from __future__ import annotations

import hashlib
import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from src.rag.documents import chunk_documents, extract_documents
from src.rag.embeddings import DEFAULT_EMBEDDING_MODEL, get_local_embedder
from src.rag.generation import DEFAULT_GEMINI_MODEL
from src.rag.pipeline import RAGPipeline
from src.rag.vector_store import ChromaVectorStore

load_dotenv()
st.set_page_config(page_title="Tutor TOGAF", page_icon="📚", layout="centered")


@st.cache_resource(show_spinner="Cargando el modelo local de embeddings…")
def cached_embedder(model_name: str):
    return get_local_embedder(model_name)


@st.cache_resource(show_spinner=False)
def cached_gemini_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        return ""


def render_answer(entry: dict) -> None:
    answer = entry.get("answer", {})
    st.markdown(f"**{answer.get('tema', 'Respuesta')}**")
    st.write(answer.get("respuesta", entry.get("content", "")))
    example = answer.get("ejemplo", "")
    if example:
        st.markdown(f"**Ejemplo:** {example}")
    if answer.get("nivel"):
        st.caption(f"Nivel: {answer['nivel']}")

    sources = entry.get("sources", [])
    if sources:
        with st.expander(f"Fuentes consultadas ({len(sources)})"):
            for index, source in enumerate(sources, start=1):
                location = source.get("source", "Documento")
                page = source.get("page")
                if page is not None:
                    location += f" · página {page}"
                st.markdown(f"**{index}. {location}**")
                st.caption(f"Similitud: {source.get('similarity', 0):.3f}")
                st.write(source.get("text", ""))


st.title("Tutor TOGAF")
st.caption("Asistente académico con recuperación de fragmentos y fuentes visibles.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "rag_store" not in st.session_state:
    st.session_state.rag_store = None
if "corpus_fingerprint" not in st.session_state:
    st.session_state.corpus_fingerprint = None

with st.sidebar:
    st.header("Base de conocimiento")
    uploads = st.file_uploader(
        "Carga los documentos que tienes autorización para procesar",
        type=["pdf", "docx", "txt", "html", "htm"],
        accept_multiple_files=True,
        help="Los documentos se procesan en la sesión y no se guardan en el índice local del servidor.",
    )
    if st.button("Crear índice de esta sesión", type="primary", disabled=not uploads):
        try:
            source_documents = []
            file_hashes = []
            for upload in uploads or []:
                data = upload.getvalue()
                file_hashes.append(hashlib.sha256(data).hexdigest())
                source_documents.extend(extract_documents(data, upload.name))
            chunks = chunk_documents(source_documents)
            store = ChromaVectorStore(
                path=None,
                collection_name=f"session_{uuid.uuid4().hex[:16]}",
            )
            model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
            embedder = cached_embedder(model_name)
            with st.spinner("Extrayendo texto y creando el índice local…"):
                store.replace_index(chunks, embedder)
            st.session_state.rag_store = store
            st.session_state.corpus_fingerprint = hashlib.sha256(
                "".join(sorted(file_hashes)).encode("ascii")
            ).hexdigest()
            st.session_state.messages = []
            st.success(f"Índice listo: {len(source_documents)} páginas/documentos y {len(chunks)} fragmentos.")
        except Exception as exc:
            st.error(f"No se pudo crear el índice: {exc}")

    if st.session_state.rag_store is not None:
        st.success(f"Índice de esta sesión: {st.session_state.rag_store.count()} fragmentos")
    else:
        st.info("Carga tus PDF de TOGAF y crea el índice para empezar.")

    st.divider()
    top_k = st.slider("Fragmentos máximos por pregunta (top_k)", min_value=1, max_value=8, value=5)
    if st.button("Limpiar conversación"):
        st.session_state.messages = []
        st.rerun()

    st.caption(
        "La aplicación recibe los archivos cargados para procesarlos en la sesión. "
        "Solo los fragmentos recuperados, la pregunta y el historial reciente se envían a Gemini. "
        "Configura una clave de un proyecto con facturación activa para evitar que Google use "
        "entradas y respuestas para mejorar productos."
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_answer(message)
        else:
            st.write(message["content"])

question = st.chat_input("Pregunta sobre los documentos TOGAF cargados…")
if question:
    if st.session_state.rag_store is None:
        st.warning("Primero carga los PDF y crea el índice de esta sesión.")
        st.stop()

    api_key = gemini_api_key()
    if not api_key:
        st.error("Falta configurar GEMINI_API_KEY en el entorno o en los secretos de Streamlit.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    embedder = cached_embedder(os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    pipeline = RAGPipeline(
        st.session_state.rag_store,
        embedder,
        min_similarity=float(os.getenv("MIN_RETRIEVAL_SIMILARITY", "0.55")),
        model_name=model_name,
    )
    history = st.session_state.messages[:-1]
    client = cached_gemini_client(api_key)
    try:
        with st.chat_message("assistant"):
            with st.spinner("Buscando evidencia en los documentos…"):
                answer, retrieved = pipeline.answer(
                    question,
                    history,
                    top_k=top_k,
                    client=client,
                )
            source_entries = [
                {
                    "source": str(item.metadata.get("source", "Documento")),
                    "page": item.metadata.get("page"),
                    "similarity": item.similarity,
                    "text": item.text,
                }
                for item in retrieved
            ]
            entry = {
                "role": "assistant",
                "content": answer.respuesta,
                "answer": answer.model_dump(),
                "sources": source_entries,
            }
            render_answer(entry)
        st.session_state.messages.append(entry)
    except Exception as exc:
        st.error(f"No se pudo responder esta pregunta: {exc}")
