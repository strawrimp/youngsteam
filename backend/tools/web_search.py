"""Web search tool using DuckDuckGo (no API key required)."""

import httpx
import json
import logging
import re
from typing import Any, Dict, List
from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo."""

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
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """Execute a web search using DuckDuckGo."""
        try:
            results = await self._search(query, max_results)
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

            return ToolResult(
                success=True, output=formatted, metadata={"results": results}
            )

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return ToolResult(success=False, output="", error=f"검색 실패: {str(e)}")

    async def _search(self, query: str, max_results: int) -> List[Dict]:
        """Search DuckDuckGo — POST to lite endpoint for real results."""
        results = []

        # Primary: DDG Lite HTML (POST) — 실제 검색 결과
        try:
            results = await self._search_ddg_lite(query, max_results)
        except Exception as e:
            logger.warning(f"DDG Lite search failed: {e}")

        # Fallback: DDG Instant Answer API (지식 그래프)
        if not results:
            try:
                results = await self._search_ddg_instant(query, max_results)
            except Exception as e:
                logger.warning(f"DDG Instant Answer failed: {e}")

        return results[:max_results]

    async def _search_ddg_lite(self, query: str, max_results: int) -> List[Dict]:
        """DDG Lite에 POST 요청하여 실제 검색 결과를 파싱."""
        results = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": query, "kl": "kr-kr"},
                headers=headers,
            )
            html = response.text

            # 1) result-link + result-snippet 쌍으로 파싱
            #    DDG Lite 구조 (속성 순서 무관):
            #    <a rel="nofollow" href='URL' class='result-link'>TITLE</a>
            #    ...
            #    <td class='result-snippet'>DESCRIPTION</td>
            #    → <a ... > 태그 안에 class='result-link'가 포함된 경우 매칭
            #    주의: href는 큰따옴표, class는 작은따옴표 혼용
            link_pattern = re.compile(
                r"<a\s[^>]*?href=[\"'](https?://[^\"']+)[\"'][^>]*?class=['\"]result-link['\"][^>]*>(.*?)</a>",
                re.DOTALL,
            )
            snippet_pattern = re.compile(
                r"class='result-snippet'[^>]*>(.*?)</(?:td|a)>",
                re.DOTALL,
            )

            link_matches = list(link_pattern.finditer(html))
            snippet_matches = list(snippet_pattern.finditer(html))

            for i in range(min(len(link_matches), max_results)):
                url = link_matches[i].group(1)
                title = re.sub(r"<[^>]+>", "", link_matches[i].group(2)).strip()
                description = ""
                if i < len(snippet_matches):
                    description = re.sub(
                        r"<[^>]+>", "", snippet_matches[i].group(1)
                    ).strip()

                if url and "duckduckgo" not in url:
                    results.append(
                        {
                            "title": title or url,
                            "url": url,
                            "description": description[:300],
                        }
                    )

            # 2) result-link가 없으면 일반 외부 링크로 폴백
            if not results:
                all_links = re.findall(r"href=['\"](https?://[^'\"]+)['\"]", html)
                seen = set()
                for link in all_links:
                    if "duckduckgo" in link:
                        continue
                    if link in seen:
                        continue
                    seen.add(link)
                    results.append(
                        {
                            "title": link.split("/")[-1].replace("-", " ")[:60] or link,
                            "url": link,
                            "description": "",
                        }
                    )
                    if len(results) >= max_results:
                        break

        return results

    async def _search_ddg_instant(self, query: str, max_results: int) -> List[Dict]:
        """DDG Instant Answer API (지식 그래프 — 위키피디아 등)."""
        results = []

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

            if data.get("AbstractText"):
                results.append(
                    {
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "description": data["AbstractText"][:500],
                    }
                )

            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(
                        {
                            "title": topic.get("Text", "")[:80],
                            "url": topic.get("FirstURL", ""),
                            "description": topic.get("Text", "")[:300],
                        }
                    )

            for result in data.get("Results", [])[:max_results]:
                results.append(
                    {
                        "title": result.get("Text", "")[:80],
                        "url": result.get("FirstURL", ""),
                        "description": result.get("Text", "")[:300],
                    }
                )

        return results
