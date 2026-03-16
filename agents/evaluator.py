"""
agents/evaluator.py
===================
Self-Evaluation Agent: scores the generated answer for groundedness and
completeness, then recommends whether to trigger additional retrieval.
"""
from __future__ import annotations

import json
import logging
from typing import List

from langchain_openai import ChatOpenAI
from langchain.schema import Document, HumanMessage, SystemMessage

from config import OPENAI_API_KEY, LLM_MODEL, CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)


EVALUATOR_SYSTEM_PROMPT = """You are a strict factual evaluator for a RAG (Retrieval-Augmented Generation) system.

Given:
- A user question
- Retrieved context documents
- A generated answer

Your job is to evaluate:
1. GROUNDEDNESS: Is the answer supported by the retrieved context?
2. COMPLETENESS: Does the answer fully address the question?
3. HALLUCINATION RISK: Does the answer include claims not present in the context?

Respond with ONLY a JSON object:

{
  "groundedness_score": 0.0 to 1.0,
  "completeness_score": 0.0 to 1.0,
  "hallucination_risk": "low" | "medium" | "high",
  "confidence": "high" | "medium" | "low",
  "needs_more_retrieval": true | false,
  "suggested_followup_query": "<optional alternative search query or null>",
  "reasoning": "<brief explanation>"
}

Rules:
- groundedness_score < 0.6  → set needs_more_retrieval = true
- completeness_score < 0.5  → set needs_more_retrieval = true
- hallucination_risk = high  → set confidence = "low"
- If context is empty or trivial → groundedness_score = 0.0
"""


def _format_context_for_eval(docs: List[Document]) -> str:
    if not docs:
        return "(no context retrieved)"
    parts = []
    for i, doc in enumerate(docs, 1):
        src = doc.metadata.get("source", "unknown")
        ts = doc.metadata.get("timestamp", "")
        parts.append(f"[Doc {i} | source={src} ts={ts}]\n{doc.page_content[:600]}")
    return "\n\n".join(parts)


def evaluate_answer(
    question: str,
    context_docs: List[Document],
    answer: str,
) -> dict:
    """
    Evaluates an answer against its supporting documents.

    Returns
    -------
    {
        "groundedness_score": float,
        "completeness_score": float,
        "hallucination_risk": str,
        "confidence": str,
        "needs_more_retrieval": bool,
        "suggested_followup_query": str | None,
        "reasoning": str,
    }
    """
    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        temperature=0,
    )

    context_str = _format_context_for_eval(context_docs)

    prompt = f"""User Question:
{question}

Retrieved Context:
{context_str}

Generated Answer:
{answer}

Evaluate the answer."""

    messages = [
        SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return result
    except Exception as exc:
        logger.warning("Evaluation failed: %s — returning conservative defaults", exc)
        return {
            "groundedness_score": 0.5,
            "completeness_score": 0.5,
            "hallucination_risk": "medium",
            "confidence": "medium",
            "needs_more_retrieval": False,
            "suggested_followup_query": None,
            "reasoning": "Evaluation failed, defaults applied.",
        }
