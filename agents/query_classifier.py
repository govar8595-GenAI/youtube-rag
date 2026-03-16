"""
agents/query_classifier.py
==========================
LLM-powered agent that analyses a user query and returns a structured
intent classification used by the Adaptive Retrieval Router.
"""
from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from config import OPENAI_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    VIDEO_SPECIFIC   = "video_specific_question"   # asks about what the speaker/video says
    TIMESTAMP_LOOKUP = "timestamp_lookup"           # asks for time/moment in the video
    CONCEPTUAL       = "conceptual_question"        # asks to explain a concept mentioned
    GENERAL_INFO     = "general_information"        # broad factual question
    SUMMARIZATION    = "summarization"              # summarise the video or a part of it
    UNKNOWN          = "unknown"


CLASSIFIER_SYSTEM_PROMPT = """You are a query intent classifier for a YouTube Video Q&A system.

Classify the user's question into exactly ONE of these intents:

| Intent                   | When to use |
|--------------------------|-------------|
| video_specific_question  | The user asks about what the presenter says, does, or shows specifically in the video. |
| timestamp_lookup         | The user wants to know WHEN (at what time) something happens in the video. |
| conceptual_question      | The user asks to explain a concept, term, or idea that was mentioned. |
| general_information      | The user asks a broad factual question not tied to the video's content. |
| summarization            | The user asks for a summary of all or part of the video. |
| unknown                  | Cannot be classified. |

Respond with ONLY a valid JSON object — no markdown, no extra text:

{
  "intent": "<one of the five values above>",
  "reasoning": "<one sentence explaining why>",
  "keywords": ["<key", "terms", "from", "query>"],
  "needs_web_search": true | false
}

`needs_web_search` should be true only for `general_information` or when the question
is clearly beyond the scope of a single video's transcript.
"""


def classify_query(query: str) -> dict:
    """
    Classifies the user query.

    Returns
    -------
    {
        "intent": QueryIntent value (str),
        "reasoning": str,
        "keywords": List[str],
        "needs_web_search": bool,
    }
    """
    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        temperature=0,
    )

    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=f"User query: {query}"),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        # Validate intent value
        try:
            result["intent"] = QueryIntent(result["intent"]).value
        except ValueError:
            result["intent"] = QueryIntent.UNKNOWN.value
        return result
    except Exception as exc:
        logger.warning("Query classification failed: %s — defaulting to unknown", exc)
        return {
            "intent": QueryIntent.UNKNOWN.value,
            "reasoning": "Classification failed.",
            "keywords": [],
            "needs_web_search": False,
        }
