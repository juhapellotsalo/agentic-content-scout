"""Tavily web search tool for content discovery."""

import logging
import os
from urllib.parse import urlparse

from langchain_core.tools import tool
from tavily import TavilyClient

logger = logging.getLogger(__name__)


@tool
def tavily_search(queries: list[str]) -> str:
    """Search the web for content related to a topic.

    Use this to discover articles, blog posts, papers, and other content.
    Provide multiple diverse queries to cast a wide net.

    Args:
        queries: List of search queries (e.g., ["LangGraph agents tutorial", "multi-agent patterns"])

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY environment variable is not set"

    tavily = TavilyClient(api_key=api_key)
    results = []
    seen_urls = set()

    for query in queries:
        try:
            resp = tavily.search(query, search_depth="advanced", max_results=5)
            for r in resp.get("results", []):
                url = r.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    domain = urlparse(url).netloc
                    title = r.get("title", "No title")
                    snippet = r.get("content", "")[:300]
                    results.append(f"**{title}**\nSource: {domain}\nURL: {url}\n{snippet}...")
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            results.append(f"Search failed for '{query}': {e}")

    if not results:
        return "No results found."

    return f"Found {len(results)} results:\n\n" + "\n\n".join(results)
