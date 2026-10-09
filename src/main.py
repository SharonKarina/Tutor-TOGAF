from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.rag.documents import chunk_documents, load_directory
from src.rag.embeddings import DEFAULT_EMBEDDING_MODEL, get_local_embedder
from src.rag.generation import DEFAULT_GEMINI_MODEL
from src.rag.pipeline import RAGPipeline
from src.rag.vector_store import ChromaVectorStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "source_documents"
INDEX_DIR = ROOT / "data" / "chroma"


def _client_from_environment():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Falta GEMINI_API_KEY. Configura una clave de Gemini con facturación "
            "activa para evitar el uso de entradas y respuestas en la mejora de productos."
        )
    from google import genai

    return genai.Client(api_key=api_key)


def _ensure_index() -> ChromaVectorStore:
    store = ChromaVectorStore(path=INDEX_DIR)
    if store.count() > 0:
        return store

    documents = load_directory(SOURCE_DIR)
    chunks = chunk_documents(documents)
    embedder = get_local_embedder(os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    store.replace_index(chunks, embedder)
    print(f"Índice creado con {len(chunks)} fragmentos de {len(documents)} páginas/documentos.")
    return store


def main() -> None:
    load_dotenv(ROOT / ".env")
    print("=================================")
    print("      TUTOR TOGAF - RAG")
    print("=================================")
    try:
        client = _client_from_environment()
        store = _ensure_index()
        embedder = get_local_embedder(os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Configuración pendiente: {exc}")
        print("Revisa el README para agregar los documentos y configurar la API.")
        return

    pipeline = RAGPipeline(
        store,
        embedder,
        min_similarity=float(os.getenv("MIN_RETRIEVAL_SIMILARITY", "0.55")),
        model_name=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
    )
    history: list[dict[str, str]] = []
    print("Escribe 'salir' para terminar.\n")
    while True:
        question = input("Tú: ").strip()
        if question.lower() in {"salir", "exit", "quit"}:
            break
        if not question:
            continue
        try:
            answer, sources = pipeline.answer(question, history, client=client)
        except Exception as exc:
            print(f"No se pudo generar la respuesta: {exc}\n")
            continue

        print("Tutor TOGAF:")
        print(json.dumps(answer.model_dump(), ensure_ascii=False, indent=2))
        if sources:
            print("Fuentes recuperadas:")
            for item in sources:
                location = str(item.metadata.get("source", "Documento"))
                if item.metadata.get("page") is not None:
                    location += f", página {item.metadata['page']}"
                print(f"- {location} (similitud {item.similarity:.3f})")
        print()
        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer.respuesta},
            ]
        )


if __name__ == "__main__":
    main()
