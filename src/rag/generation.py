from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from prompts.system_prompt import SYSTEM_PROMPT
from src.rag.vector_store import RetrievedChunk

DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


class TutorAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tema: str = Field(description="Concepto principal de la respuesta")
    respuesta: str = Field(description="Explicación sustentada en el contexto recuperado")
    ejemplo: str = Field(description="Ejemplo breve o una cadena vacía si no aplica")
    nivel: Literal["básico", "intermedio", "avanzado"]


def format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        source = str(chunk.metadata.get("source", "Documento sin nombre"))
        page = chunk.metadata.get("page")
        location = f"{source}, página {page}" if page is not None else source
        blocks.append(f"[Fragmento {index} | {location}]\n{chunk.text}")
    return "\n\n".join(blocks)


def build_user_message(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]] | None = None,
) -> str:
    history_lines: list[str] = []
    for item in (history or [])[-4:]:
        role = "Estudiante" if item.get("role") == "user" else "Tutor"
        content = str(item.get("content", "")).strip()
        if content:
            history_lines.append(f"{role}: {content[:700]}")
    history_text = "\n".join(history_lines) or "Sin turnos anteriores."
    context_text = format_context(chunks) or "No se recuperó evidencia relevante."
    return (
        "<INSTRUCCIONES>\n"
        "Responde la pregunta actual aplicando el System Prompt. Usa el historial solo "
        "para resolver referencias a turnos anteriores.\n"
        "Si la pregunta tiene varias partes y el contexto respalda solo algunas, responde "
        "esas partes y señala con precisión qué dato falta para las demás; no rechaces toda "
        "la pregunta. No completes vacíos con conocimiento general. Incluye un ejemplo solo "
        "si el contexto lo respalda; si no, deja el campo ejemplo vacío.\n"
        "</INSTRUCCIONES>\n"
        f"<HISTORIAL>\n{history_text}\n</HISTORIAL>\n"
        f"<CONTEXTO>\n{context_text}\n</CONTEXTO>\n"
        f"<PREGUNTA>\n{question.strip()}\n</PREGUNTA>"
    )


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]] | None = None,
    *,
    client=None,
    model_name: str = DEFAULT_GROQ_MODEL,
) -> TutorAnswer:
    """Generate one schema-constrained answer; only retrieved chunks are sent."""
    if client is None:
        from groq import Groq

        client = Groq()

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": (
                    f"<SYSTEM_PROMPT>\n{SYSTEM_PROMPT}\n</SYSTEM_PROMPT>\n\n"
                    f"{build_user_message(question, chunks, history)}"
                ),
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "tutor_answer",
                "strict": True,
                "schema": TutorAnswer.model_json_schema(),
            },
        },
        temperature=0.2,
        max_completion_tokens=900,
    )
    raw_text = response.choices[0].message.content
    if not raw_text:
        raise ValueError("Groq devolvió una respuesta vacía.")
    return TutorAnswer.model_validate_json(raw_text)
