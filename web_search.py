from __future__ import annotations
import logging
import re
from typing import List, Optional
from langchain.schema import Document

logger = logging.getLogger(__name__)

try:
    from config import TAVILY_API_KEY
except ImportError:
    TAVILY_API_KEY = ""


def _search_tavily(query: str, k: int = 5) -> List[Document]:
    from langchain_community.tools.tavily_search import TavilySearchResults
    tool = TavilySearchResults(max_results=k, tavily_api_key=TAVILY_API_KEY)
    raw = tool.invoke(query)
    docs = []
    for item in raw:
        content = item.get("content", "")
        url = item.get("url", "")
        title = item.get("title", url)
        docs.append(Document(
            page_content=content,
            metadata={"source": "web", "url": url, "title": title, "engine": "tavily"},
        ))
    return docs


def _search_duckduckgo(query: str, k: int = 5) -> List[Document]:
    from langchain_community.tools import DuckDuckGoSearchResults
    tool = DuckDuckGoSearchResults(num_results=k)
    raw = tool.run(query)
    blocks = re.findall(r"\[snippet:\s*(.*?)\]\s*\[title:\s*(.*?)\]\s*\[link:\s*(.*?)\]", raw)
    if not blocks:
        return [Document(
            page_content=raw,
            metadata={"source": "web", "url": "", "title": query, "engine": "duckduckgo"},
        )]
    return [
        Document(
            page_content=snippet,
            metadata={"source": "web", "url": link, "title": title, "engine": "duckduckgo"},
        )
        for snippet, title, link in blocks
    ][:k]


def web_search(query: str, k: int = 5) -> List[Document]:
    if TAVILY_API_KEY:
        logger.info("Web search via Tavily: %r", query)
        try:
            return _search_tavily(query, k)
        except Exception as exc:
            logger.warning("Tavily failed (%s), falling back to DuckDuckGo", exc)
    logger.info("Web search via DuckDuckGo: %r", query)
    try:
        return _search_duckduckgo(query, k)
    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
        return []


def enrich_query_for_web(query: str, video_title: Optional[str] = None) -> str:
    if video_title:
        return f"{video_title} — {query}"
    return query