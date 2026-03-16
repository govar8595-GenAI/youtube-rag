"""
api/routes.py
=============
FastAPI application exposing the YouTube RAG system as a REST API.

Endpoints
---------
POST /ingest          — Ingest a YouTube video (fetch transcript + build index)
POST /chat            — Ask a question about an ingested video
GET  /videos          — List all indexed video IDs
GET  /health          — Health check
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from ingest_youtube import ingest_youtube
from retriever import build_vector_store, is_video_indexed
from rag_pipeline import run_rag_pipeline

logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube Video Chat — Adaptive RAG",
    description="Ask anything about a YouTube video using adaptive multi-source RAG.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory registry of ingested videos (video_id → title)
_video_registry: dict[str, str] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    url: str
    title: Optional[str] = None


class IngestResponse(BaseModel):
    video_id: str
    num_chunks: int
    message: str


class ChatRequest(BaseModel):
    video_id: str
    question: str


class SourceItem(BaseModel):
    type: str
    timestamp: Optional[str] = None
    video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None


class EvaluationInfo(BaseModel):
    groundedness_score: Optional[float]
    completeness_score: Optional[float]
    hallucination_risk: Optional[str]
    reasoning: Optional[str]


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    confidence: str
    intent: str
    retrieval_log: List[str]
    evaluation: EvaluationInfo


class VideoInfo(BaseModel):
    video_id: str
    title: Optional[str]
    indexed: bool


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest_video(request: IngestRequest):
    """
    Accepts a YouTube URL, fetches its transcript, splits it into chunks,
    generates embeddings, and stores them in the vector database.
    """
    try:
        video_id, documents = ingest_youtube(request.url)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during ingestion")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    try:
        build_vector_store(documents, video_id)
    except Exception as exc:
        logger.exception("Vector store build failed")
        raise HTTPException(status_code=500, detail=f"Vector store build failed: {exc}")

    title = request.title or video_id
    _video_registry[video_id] = title

    return IngestResponse(
        video_id=video_id,
        num_chunks=len(documents),
        message=f"Video '{title}' ingested successfully with {len(documents)} chunks.",
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Answers a question about a previously ingested YouTube video using
    the Adaptive Multi-Source RAG pipeline.
    """
    if not is_video_indexed(request.video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{request.video_id}' is not indexed. Please call /ingest first.",
        )

    video_title = _video_registry.get(request.video_id)

    try:
        result = run_rag_pipeline(
            question=request.question,
            video_id=request.video_id,
            video_title=video_title,
        )
    except Exception as exc:
        logger.exception("RAG pipeline error")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceItem(**s) for s in result["sources"]],
        confidence=result["confidence"],
        intent=result["intent"],
        retrieval_log=result["retrieval_log"],
        evaluation=EvaluationInfo(**result["evaluation"]),
    )


@app.get("/videos", response_model=List[VideoInfo])
def list_videos():
    """Returns all video IDs that have been ingested."""
    return [
        VideoInfo(
            video_id=vid,
            title=title,
            indexed=is_video_indexed(vid),
        )
        for vid, title in _video_registry.items()
    ]
