from __future__ import annotations

import unicodedata
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
    normalized_question = "".join(
        character
        for character in unicodedata.normalize("NFKD", question.casefold())
        if not unicodedata.combining(character)
    )
    intent_guidance: list[str] = []
    if any(term in normalized_question for term in ("gestion de requisitos", "requirements management")):
        intent_guidance.append(
            "Para una pregunta sobre gestión de requisitos y ciclo ADM, explica la relación "
            "que describan los fragmentos (por ejemplo, continuidad, cambios o repositorio, "
            "solo si aparecen allí). No la conviertas en una lista genérica de fases."
        )
    if "adm" in normalized_question and any(
        term in normalized_question for term in ("fases", "phases", "ciclo", "cycle")
    ):
        intent_guidance.append(
            "Si los fragmentos muestran la secuencia de fases del ADM, enumérala. Distingue "
            "las fases que solo aparecen nombradas de las que sí tienen actividades u objetivos "
            "descritos. Nunca repitas la pregunta como respuesta."
        )
    compared_domains = sum(
        term in normalized_question
        for term in ("negocio", "datos", "aplicaciones", "tecnologic", "business", "data", "application", "technology")
    )
    if compared_domains >= 2:
        intent_guidance.append(
            "Para comparar dominios, responde de forma parcial y separada: explica cada "
            "dominio que los fragmentos describan y nombra cuáles solo aparecen mencionados "
            "sin definición. No rechaces toda la comparación si hay evidencia útil para "
            "algunos dominios, y no infieras funciones a partir de un nombre solamente."
        )
    if any(term in normalized_question for term in ("entregable", "deliverable", "outputs", "productos de trabajo")):
        intent_guidance.append(
            "En preguntas sobre entregables, presenta solo las fases y productos que estén "
            "en los fragmentos y aclara que la lista es parcial si no aparecen todas las "
            "fases del ADM. No atribuyas validación de cada entregable al Architecture "
            "Board a menos que el texto lo diga expresamente."
        )

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
        "Si los fragmentos contienen evidencia pertinente, redacta una respuesta directa. "
        "Nunca devuelvas una respuesta vacía ni repitas la pregunta como respuesta. Si no "
        "hay evidencia suficiente, indícalo claramente.\n"
        "Si el contexto respalda parte de la pregunta, responde esa parte y señala con "
        "precisión qué falta; no rechaces toda la pregunta. No completes vacíos con "
        "conocimiento general. Cada dato factual debe estar respaldado por los fragmentos; "
        "no deduzcas contenido a partir del título del archivo ni del nombre de una fase. "
        "El campo ejemplo debe quedar vacío salvo que algún fragmento respalde explícitamente "
        "ese ejemplo.\n"
        + "\n".join(intent_guidance)
        + "\n"
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
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_message(question, chunks, history),
            },
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
