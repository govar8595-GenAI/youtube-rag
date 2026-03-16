from __future__ import annotations

import logging
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain.schema import Document, HumanMessage, SystemMessage

from agents.query_classifier import classify_query
from agents.evaluator import evaluate_answer
from adaptive_router import route_and_retrieve
from config import OPENAI_API_KEY, LLM_MODEL
from web_search import web_search

logger = logging.getLogger(__name__)

MAX_EVAL_RETRIES = 1   # How many times to retry retrieval if answer is insufficient


# ─────────────────────────────────────────────────────────────────────────────
# Context formatting
# ─────────────────────────────────────────────────────────────────────────────

def _format_context(docs: List[Document]) -> str:
    """
    Formats retrieved documents into a clean, source-labelled context block
    for injection into the LLM prompt.
    """
    parts: List[str] = []
    for doc in docs:
        meta = doc.metadata
        src = meta.get("source", "unknown")

        if src == "youtube":
            ts = meta.get("timestamp", "")
            vid = meta.get("video_id", "")
            header = f"[Source: YouTube Transcript | Video: {vid} | Timestamp: {ts}]"
        else:
            title = meta.get("title", "Web Article")
            url = meta.get("url", "")
            header = f"[Source: Web | Title: {title} | URL: {url}]"

        parts.append(f"{header}\n{doc.page_content}")

    return "\n\n---\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are an expert AI assistant that answers questions about YouTube videos.

You have access to two types of sources:
1. **YouTube Transcript** — direct quotes from the video with timestamps.
2. **Web Search Results** — supplementary information from the internet.

Guidelines:
- Prefer YouTube transcript information when answering video-specific questions.
- Always cite timestamps when referencing transcript content (e.g., "At 03:12, the speaker explains...").
- If using web results, note the source.
- Be concise but complete. Do not pad with unnecessary disclaimers.
- If the context does not contain enough information, say so clearly.
"""

RAG_USER_TEMPLATE = """Context:
{context}

---

User Question:
{question}

Provide a clear, accurate, and well-cited answer based on the context above."""


# ─────────────────────────────────────────────────────────────────────────────
# Answer generation
# ─────────────────────────────────────────────────────────────────────────────

def _generate_answer(question: str, docs: List[Document]) -> str:
    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        temperature=0.3,
    )
    context = _format_context(docs)
    prompt = RAG_USER_TEMPLATE.format(context=context, question=question)
    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    response = llm.invoke(messages)
    return response.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Source extraction (for structured response)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_sources(docs: List[Document]) -> List[dict]:
    sources = []
    seen_urls: set[str] = set()
    seen_ts: set[str] = set()

    for doc in docs:
        meta = doc.metadata
        src = meta.get("source", "unknown")

        if src == "youtube":
            ts = meta.get("timestamp", "")
            if ts not in seen_ts:
                seen_ts.add(ts)
                sources.append({
                    "type": "youtube",
                    "timestamp": ts,
                    "video_id": meta.get("video_id", ""),
                    "youtube_url": meta.get("youtube_url", ""),
                })
        else:
            url = meta.get("url", "")
            title = meta.get("title", "")
            if url not in seen_urls:
                seen_urls.add(url)
                sources.append({
                    "type": "web",
                    "url": url,
                    "title": title,
                })

    return sources


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_rag_pipeline(
    question: str,
    video_id: str,
    video_title: Optional[str] = None,
) -> dict:
    """
    Full end-to-end RAG pipeline.

    Parameters
    ----------
    question    : User's natural-language question.
    video_id    : ID of the ingested YouTube video.
    video_title : Optional human-readable video title (used to enrich web queries).

    Returns
    -------
    {
        "answer": str,
        "sources": List[dict],
        "confidence": str,
        "intent": str,
        "retrieval_log": List[str],
        "evaluation": dict,
    }
    """
    pipeline_log: List[str] = []

    # ── Step 1: Classify query ───────────────────────────────────────────────
    classification = classify_query(question)
    intent = classification["intent"]
    pipeline_log.append(f"Classified intent: {intent}")
    pipeline_log.append(f"Classification reasoning: {classification.get('reasoning', '')}")

    # ── Step 2: Adaptive retrieval ───────────────────────────────────────────
    docs, retrieval_log = route_and_retrieve(
        query=question,
        video_id=video_id,
        intent=intent,
        classification=classification,
        video_title=video_title,
    )
    pipeline_log.extend(retrieval_log)

    # ── Step 3: Generate answer ──────────────────────────────────────────────
    answer = _generate_answer(question, docs)
    pipeline_log.append("Answer generated")

    # ── Step 4: Self-evaluation ──────────────────────────────────────────────
    evaluation = evaluate_answer(question, docs, answer)
    confidence = evaluation.get("confidence", "medium")
    pipeline_log.append(f"Evaluation: confidence={confidence}, needs_more={evaluation.get('needs_more_retrieval')}")

    # ── Step 5: Optional expanded retrieval loop ─────────────────────────────
    for attempt in range(MAX_EVAL_RETRIES):
        if not evaluation.get("needs_more_retrieval"):
            break

        followup_query = evaluation.get("suggested_followup_query") or question
        pipeline_log.append(f"Retry {attempt+1}: expanded web search for {followup_query!r}")

        extra_docs = web_search(followup_query, k=3)
        if extra_docs:
            docs = docs + extra_docs
            answer = _generate_answer(question, docs)
            evaluation = evaluate_answer(question, docs, answer)
            confidence = evaluation.get("confidence", "medium")
            pipeline_log.append(f"Re-evaluation: confidence={confidence}")

    # ── Step 6: Assemble response ────────────────────────────────────────────
    sources = _extract_sources(docs)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "intent": intent,
        "retrieval_log": pipeline_log,
        "evaluation": {
            "groundedness_score": evaluation.get("groundedness_score"),
            "completeness_score": evaluation.get("completeness_score"),
            "hallucination_risk": evaluation.get("hallucination_risk"),
            "reasoning": evaluation.get("reasoning"),
        },
    }
