from __future__ import annotations

from src.rag.embeddings import LocalEmbedder
from src.rag.generation import DEFAULT_GROQ_MODEL, TutorAnswer, generate_answer
from src.rag.vector_store import ChromaVectorStore, RetrievedChunk

ABSTENTION_TEXT = (
    "No encontré información suficiente en los documentos cargados para responder "
    "esta pregunta con respaldo."
)


def build_retrieval_query(question: str, history: list[dict[str, str]] | None) -> str:
    """Include recent turns so short follow-up questions retrieve useful material."""
    turns = []
    for item in (history or [])[-4:]:
        content = str(item.get("content", "")).strip()
        if content:
            role = "pregunta" if item.get("role") == "user" else "respuesta"
            turns.append(f"{role}: {content[:350]}")
    if not turns:
        return question.strip()
    return "\n".join([*turns, f"pregunta actual: {question.strip()}"])


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
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        query = build_retrieval_query(question, history)
        candidates = self.store.search(query, self.embedder, top_k=top_k)
        return [chunk for chunk in candidates if chunk.similarity >= self.min_similarity]

    def answer(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        *,
        top_k: int = 5,
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
