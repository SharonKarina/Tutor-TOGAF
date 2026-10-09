from __future__ import annotations

import unicodedata

from src.rag.embeddings import LocalEmbedder
from src.rag.generation import DEFAULT_GROQ_MODEL, TutorAnswer, generate_answer
from src.rag.vector_store import ChromaVectorStore, RetrievedChunk

ABSTENTION_TEXT = (
    "No encontré información suficiente en los documentos cargados para responder "
    "esta pregunta con respaldo."
)

QUERY_EXPANSIONS = {
    "fases del adm": (
        "ADM phases Preliminary Phase Phase A Architecture Vision Phase B Business Architecture "
        "Phase C Information Systems Architecture Phase D Technology Architecture "
        "Phase E Opportunities and Solutions Phase F Migration Planning "
        "Phase G Implementation Governance Phase H Architecture Change Management"
    ),
    "vision de arquitectura": (
        "Phase A Architecture Vision scope stakeholders business goals objectives "
        "high-level aspirational view approval"
    ),
    "arquitectura de negocio": "Business Architecture Phase B baseline target business capability process organization",
    "arquitectura de datos": "Data Architecture Phase C data entities logical data components",
    "arquitectura de aplicaciones": "Application Architecture Phase C application systems services",
    "arquitectura tecnologica": "Technology Architecture Phase D technology infrastructure platform",
    "bloques de construccion": "Architecture Building Blocks ABB Solution Building Blocks SBB",
}

FOLLOW_UP_MARKERS = (
    "y eso", "y esa", "y ese", "lo anterior", "amplia eso", "profundiza", "continua",
    "dame mas detalle", "explica eso", "que significa eso", "como se relaciona",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def build_retrieval_query(question: str, history: list[dict[str, str]] | None) -> str:
    """Keep standalone searches focused; add prior questions only for clear follow-ups."""
    current = question.strip()
    normalized = _normalize(current)
    parts = [current]

    if any(marker in normalized for marker in FOLLOW_UP_MARKERS):
        previous_questions = [
            str(item.get("content", "")).strip()
            for item in (history or [])
            if item.get("role") == "user" and str(item.get("content", "")).strip()
        ][-2:]
        parts = [*previous_questions, current]

    expansions = [
        expansion
        for phrase, expansion in QUERY_EXPANSIONS.items()
        if phrase in normalized
    ]
    parts.extend(expansions)
    return "\n".join(parts)


def abstention_answer() -> TutorAnswer:
    return TutorAnswer(
        tema="Información no encontrada en el corpus",
        respuesta=ABSTENTION_TEXT,
        ejemplo="",
        nivel="básico",
    )


class RAGPipeline:
    def __init__(
        self,
        store: ChromaVectorStore,
        embedder: LocalEmbedder,
        *,
        min_similarity: float = 0.55,
        model_name: str = DEFAULT_GROQ_MODEL,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.min_similarity = min_similarity
        self.model_name = model_name

    def retrieve(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        top_k: int = 8,
    ) -> list[RetrievedChunk]:
        query = build_retrieval_query(question, history)
        candidates = self.store.search(query, self.embedder, top_k=top_k)
        return [chunk for chunk in candidates if chunk.similarity >= self.min_similarity]

    def answer(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        *,
        top_k: int = 8,
        client=None,
    ) -> tuple[TutorAnswer, list[RetrievedChunk]]:
        retrieved = self.retrieve(question, history, top_k=top_k)
        if not retrieved:
            return abstention_answer(), []
        response = generate_answer(
            question,
            retrieved,
            history,
            client=client,
            model_name=self.model_name,
        )
        return response, retrieved
