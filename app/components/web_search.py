from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from tavily import TavilyClient

from app.common.logger import get_logger
from app.config.config import (
    TAVILY_API_KEY,
    TAVILY_SEARCH_DEPTH,
    TAVILY_SEARCH_RESULTS,
)

logger = get_logger(__name__)


def search_web(query: str) -> List[Document]:
    """Fetch top web results via Tavily and return them as LangChain Documents.

    Used as a fallback when PDF retrieval doesn't contain enough information.
    """
    if not query or not query.strip():
        return []

    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is not set.")

    client = TavilyClient(api_key=TAVILY_API_KEY)

    response = client.search(
        query=query.strip(),
        search_depth=TAVILY_SEARCH_DEPTH,
        max_results=TAVILY_SEARCH_RESULTS,
        include_answer=False,
        include_raw_content=False,
    )

    results = response.get("results", []) if isinstance(response, dict) else []

    docs: List[Document] = []
    for item in results:
        if not isinstance(item, dict):
            continue

        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        content = (item.get("content") or item.get("snippet") or "").strip()

        parts = [part for part in [title, url, content] if part]
        if not parts:
            continue

        docs.append(
            Document(
                page_content="\n".join(parts),
                metadata={"source": url, "title": title, "type": "web"},
            )
        )

    logger.info("Tavily returned %s results", len(docs))
    return docs
