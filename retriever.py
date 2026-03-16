"""
retriever.py
============
Manages the vector store (FAISS or Chroma) and exposes a semantic
similarity retriever with metadata-aware search.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List, Optional

from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS, Chroma

from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    VECTOR_STORE_BACKEND,
    VECTOR_STORE_DIR,
    TOP_K,
)

logger = logging.getLogger(__name__)

# Global in-memory store handles (per video_id)
_faiss_stores: dict[str, FAISS] = {}
_chroma_store: Optional[Chroma] = None


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Store construction
# ─────────────────────────────────────────────────────────────────────────────

def build_vector_store(documents: List[Document], video_id: str) -> None:
    """
    Embeds documents and persists them to the configured vector store.
    Existing data for the same video_id is replaced.
    """
    embeddings = _get_embeddings()
    store_path = Path(VECTOR_STORE_DIR)
    store_path.mkdir(parents=True, exist_ok=True)

    if VECTOR_STORE_BACKEND == "faiss":
        vs = FAISS.from_documents(documents, embeddings)
        vs.save_local(str(store_path / video_id))
        _faiss_stores[video_id] = vs
        logger.info("FAISS store built and saved for video %s (%d docs)", video_id, len(documents))

    elif VECTOR_STORE_BACKEND == "chroma":
        global _chroma_store
        persist_dir = str(store_path / "chroma")
        vs = Chroma.from_documents(
            documents,
            embeddings,
            collection_name=video_id,
            persist_directory=persist_dir,
        )
        vs.persist()
        _chroma_store = vs
        logger.info("Chroma store built for video %s", video_id)

    else:
        raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {VECTOR_STORE_BACKEND!r}")


def load_vector_store(video_id: str):
    """Loads a persisted vector store from disk for the given video_id."""
    embeddings = _get_embeddings()
    store_path = Path(VECTOR_STORE_DIR)

    if VECTOR_STORE_BACKEND == "faiss":
        vs_path = store_path / video_id
        if not vs_path.exists():
            raise FileNotFoundError(f"No FAISS store found for video {video_id!r}")
        vs = FAISS.load_local(str(vs_path), embeddings, allow_dangerous_deserialization=True)
        _faiss_stores[video_id] = vs
        return vs

    elif VECTOR_STORE_BACKEND == "chroma":
        persist_dir = str(store_path / "chroma")
        vs = Chroma(
            collection_name=video_id,
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )
        return vs

    raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {VECTOR_STORE_BACKEND!r}")


def _get_store(video_id: str):
    """Returns a loaded store, pulling from cache or disk as needed."""
    if VECTOR_STORE_BACKEND == "faiss":
        if video_id not in _faiss_stores:
            return load_vector_store(video_id)
        return _faiss_stores[video_id]

    if VECTOR_STORE_BACKEND == "chroma":
        if _chroma_store is None:
            return load_vector_store(video_id)
        return _chroma_store

    raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {VECTOR_STORE_BACKEND!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_from_transcript(
    query: str,
    video_id: str,
    top_k: int = TOP_K,
    filter_metadata: Optional[dict] = None,
) -> List[Document]:
    """
    Performs semantic similarity search against the transcript vector store.

    Parameters
    ----------
    query         : Natural-language query string.
    video_id      : Target video whose store to search.
    top_k         : Number of chunks to return.
    filter_metadata : Optional metadata filter (Chroma only).

    Returns
    -------
    List of Documents ordered by relevance (most relevant first).
    """
    vs = _get_store(video_id)

    try:
        if filter_metadata and VECTOR_STORE_BACKEND == "chroma":
            docs = vs.similarity_search(query, k=top_k, filter=filter_metadata)
        else:
            docs = vs.similarity_search(query, k=top_k)
    except Exception as exc:
        logger.error("Vector search failed: %s", exc)
        docs = []

    logger.debug("Transcript retrieval: %d docs for query %r", len(docs), query[:60])
    return docs


def retrieve_with_scores(
    query: str,
    video_id: str,
    top_k: int = TOP_K,
) -> List[tuple[Document, float]]:
    """
    Like retrieve_from_transcript but also returns similarity scores.
    Scores are cosine distances (lower = more similar for FAISS L2).
    """
    vs = _get_store(video_id)
    try:
        results = vs.similarity_search_with_score(query, k=top_k)
    except Exception as exc:
        logger.error("Scored vector search failed: %s", exc)
        results = []
    return results


def is_video_indexed(video_id: str) -> bool:
    """Returns True if a persisted index exists for this video_id."""
    store_path = Path(VECTOR_STORE_DIR)
    if VECTOR_STORE_BACKEND == "faiss":
        return (store_path / video_id).exists()
    if VECTOR_STORE_BACKEND == "chroma":
        return (store_path / "chroma").exists()
    return False
