"""Web search tool using DuckDuckGo (no API key required)."""

import httpx
import json
import logging
from typing import Any, Dict, List
from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo Instant Answer API."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the internet for current information, news, facts, or any topic. "
            "Use this when you need up-to-date information or facts you don't know. "
            "Returns top search results with titles, URLs, and descriptions."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the internet",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
                }
            },
            "required": ["query"],
        }

    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """Execute a web search using DuckDuckGo."""
        try:
            results = await self._search_duckduckgo(query, max_results)
            if not results:
                return ToolResult(
                    success=True,
                    output=f"검색 결과 없음: '{query}'에 대한 결과를 찾을 수 없습니다.",
                )

            # Format results
            formatted = f"## '{query}' 검색 결과\n\n"
            for i, result in enumerate(results, 1):
                formatted += f"**{i}. {result['title']}**\n"
                formatted += f"URL: {result['url']}\n"
                formatted += f"{result['description']}\n\n"

            return ToolResult(success=True, output=formatted, metadata={"results": results})

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return ToolResult(success=False, output="", error=f"검색 실패: {str(e)}")

    async def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict]:
        """Fetch search results from DuckDuckGo."""
        results = []

        # Try DuckDuckGo Instant Answer API first
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_redirect": "1",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                    headers={"User-Agent": "AI-Agent/1.0"},
                )
                data = response.json()

                # Parse Abstract (main result)
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "description": data["AbstractText"][:500],
                    })

                # Parse Related Topics
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:80],
                            "url": topic.get("FirstURL", ""),
                            "description": topic.get("Text", "")[:300],
                        })

                # Parse Results
                for result in data.get("Results", [])[:max_results]:
                    results.append({
                        "title": result.get("Text", "")[:80],
                        "url": result.get("FirstURL", ""),
                        "description": result.get("Text", "")[:300],
                    })

        except Exception as e:
            logger.warning(f"DuckDuckGo API failed: {e}")

        # Fallback: Try DuckDuckGo HTML lite search
        if not results:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(
                        "https://lite.duckduckgo.com/lite/",
                        params={"q": query},
                        headers={
                            "User-Agent": "Mozilla/5.0 (compatible; AI-Agent/1.0)",
                            "Accept": "text/html",
                        },
                    )
                    # Parse HTML results (basic extraction)
                    html = response.text
                    # Extract links and snippets (simple approach)
                    import re
                    links = re.findall(r'href="(https?://[^"]+)"', html)
                    snippets = re.findall(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', html, re.DOTALL)

                    for i, (link, snippet) in enumerate(zip(links[:max_results], snippets[:max_results])):
                        clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                        if clean_snippet and link:
                            results.append({
                                "title": link.split("/")[-1].replace("-", " ")[:60] or link,
                                "url": link,
                                "description": clean_snippet[:300],
                            })
            except Exception as e:
                logger.warning(f"DuckDuckGo HTML fallback failed: {e}")

        return results[:max_results]
