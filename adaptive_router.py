from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from langchain.schema import Document

from agents.query_classifier import QueryIntent
from retriever import retrieve_from_transcript, retrieve_with_scores
from web_search import web_search, enrich_query_for_web
from config import TOP_K, CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

# Minimum number of transcript chars needed before we skip web search
_MIN_TRANSCRIPT_CHARS = 300
# Score threshold above which a FAISS document is considered "low similarity"
# (FAISS uses L2 distance — higher = less similar)
_FAISS_DISTANCE_CUTOFF = 1.2


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _transcript_coverage(docs: List[Document]) -> float:
    """Rough measure of how much content was retrieved from the transcript."""
    total_chars = sum(len(d.page_content) for d in docs)
    return total_chars


def _is_transcript_sufficient(
    docs: List[Document],
    scored: Optional[List[Tuple[Document, float]]] = None,
) -> bool:
    """
    Heuristic: transcript retrieval is 'sufficient' if:
      - At least 2 documents were returned, AND
      - Total retrieved text > threshold, AND
      - (When using scored search) at least one doc has acceptable similarity.
    """
    if len(docs) < 2:
        return False
    if _transcript_coverage(docs) < _MIN_TRANSCRIPT_CHARS:
        return False
    if scored:
        best_score = min(score for _, score in scored)  # lower = better for L2
        if best_score > _FAISS_DISTANCE_CUTOFF:
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Routing strategies
# ─────────────────────────────────────────────────────────────────────────────

def route_and_retrieve(
    query: str,
    video_id: str,
    intent: str,
    classification: dict,
    video_title: Optional[str] = None,
) -> Tuple[List[Document], List[str]]:
    """
    Core routing function.

    Parameters
    ----------
    query          : Original user query.
    video_id       : ID of the ingested YouTube video.
    intent         : One of the QueryIntent values.
    classification : Full dict from classify_query().
    video_title    : Optional video title to enrich web queries.

    Returns
    -------
    (documents, retrieval_log)
        documents       : Combined, deduplicated list of retrieved Documents.
        retrieval_log   : Human-readable list of steps taken.
    """
    retrieval_log: List[str] = []
    all_docs: List[Document] = []

    # ── Intent-driven routing table ─────────────────────────────────────────

    if intent == QueryIntent.TIMESTAMP_LOOKUP.value:
        # Transcript-only — timestamps are meaningless in web results
        retrieval_log.append("Intent: timestamp_lookup → transcript only")
        docs = retrieve_from_transcript(query, video_id, top_k=TOP_K)
        all_docs.extend(docs)
        retrieval_log.append(f"Transcript: {len(docs)} docs retrieved")

    elif intent == QueryIntent.SUMMARIZATION.value:
        # Broad retrieval from transcript (increase top_k for summaries)
        retrieval_log.append("Intent: summarization → extended transcript retrieval")
        docs = retrieve_from_transcript(query, video_id, top_k=TOP_K * 2)
        all_docs.extend(docs)
        retrieval_log.append(f"Transcript (extended): {len(docs)} docs retrieved")

    elif intent == QueryIntent.GENERAL_INFO.value or classification.get("needs_web_search"):
        # Hybrid: transcript first, then web
        retrieval_log.append("Intent: general_information → hybrid retrieval")

        scored = retrieve_with_scores(query, video_id, top_k=TOP_K)
        t_docs = [doc for doc, _ in scored]
        all_docs.extend(t_docs)
        retrieval_log.append(f"Transcript: {len(t_docs)} docs retrieved")

        retrieval_log.append("Triggering supplementary web search")
        web_query = enrich_query_for_web(query, video_title)
        w_docs = web_search(web_query, k=3)
        all_docs.extend(w_docs)
        retrieval_log.append(f"Web: {len(w_docs)} docs retrieved")

    else:
        # Default: transcript-first, fallback to web if thin
        retrieval_log.append(f"Intent: {intent} → transcript-first strategy")

        scored = retrieve_with_scores(query, video_id, top_k=TOP_K)
        t_docs = [doc for doc, _ in scored]
        all_docs.extend(t_docs)
        retrieval_log.append(f"Transcript: {len(t_docs)} docs retrieved")

        if not _is_transcript_sufficient(t_docs, scored):
            retrieval_log.append(
                "Transcript coverage insufficient — falling back to web search"
            )
            web_query = enrich_query_for_web(query, video_title)
            w_docs = web_search(web_query, k=3)
            all_docs.extend(w_docs)
            retrieval_log.append(f"Web fallback: {len(w_docs)} docs retrieved")
        else:
            retrieval_log.append("Transcript coverage sufficient — skipping web search")

    # ── Deduplication (by content hash) ─────────────────────────────────────
    seen: set[int] = set()
    unique_docs: List[Document] = []
    for doc in all_docs:
        h = hash(doc.page_content[:200])
        if h not in seen:
            seen.add(h)
            unique_docs.append(doc)

    retrieval_log.append(f"Total unique docs after dedup: {len(unique_docs)}")
    return unique_docs, retrieval_log
