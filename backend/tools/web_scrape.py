"""Web page scraping tool — extracts readable text content from URLs.

Uses httpx + BeautifulSoup4 to fetch and parse static HTML pages.
Designed for the agent function-calling pipeline.
"""

import logging
import re
from typing import Any, Dict
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# HTML tags that rarely contain useful article content
NOISE_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "aside",
    "iframe",
    "noscript",
    "svg",
    "form",
    "button",
    "input",
    "select",
    "textarea",
]

# Tags that typically hold the main content (checked in order)
CONTENT_TAGS = ["article", "main", "section", "div"]

# Maximum redirect hops
MAX_REDIRECTS = 5


class WebScrapeTool(BaseTool):
    """Fetch and extract readable text content from a web page URL."""

    @property
    def name(self) -> str:
        return "web_scrape"

    @property
    def description(self) -> str:
        return (
            "웹 페이지 URL의 본문 텍스트를 추출합니다. "
            "사용자가 링크(URL)를 공유하거나 특정 웹페이지의 내용을 알고 싶어 할 때 사용하세요. "
            "뉴스 기사, 블로그 포스트, 문서 페이지 등의 본문을 읽을 수 있습니다. "
            "추출된 텍스트를 바탕으로 요약, 분석, 번역 등을 수행할 수 있습니다."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "읽을 웹 페이지의 URL (예: https://example.com/article)",
                },
                "max_length": {
                    "type": "integer",
                    "description": "추출할 본문 텍스트의 최대 길이 (문자 수). 기본값: 15000",
                    "default": 15000,
                },
            },
            "required": ["url"],
        }

    async def execute(self, url: str, max_length: int = 15000) -> ToolResult:
        """Fetch a web page and extract its text content.

        Args:
            url: The web page URL to scrape.
            max_length: Maximum character length of extracted text.

        Returns:
            ToolResult with page title and extracted body text.
        """
        # Basic URL validation
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ToolResult(
                success=False,
                output="",
                error=f"지원하지 않는 URL 스킴입니다: {parsed.scheme} (http/https만 지원)",
            )

        try:
            html, final_url = await self._fetch_html(url)
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                output="",
                error=f"요청 시간 초과: {url} (10초 내에 응답하지 않았습니다)",
            )
        except httpx.HTTPStatusError as exc:
            return ToolResult(
                success=False,
                output="",
                error=f"HTTP 오류 {exc.response.status_code}: {url}",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output="",
                error=f"페이지를 가져올 수 없습니다: {exc}",
            )

        try:
            title, content = self._extract_content(html, max_length)
        except Exception as exc:
            logger.warning(f"HTML 파싱 실패, 원시 텍스트 반환: {exc}")
            # Fallback: strip tags naively
            raw = re.sub(r"<[^>]+>", " ", html)
            content = self._clean_text(raw)[:max_length]
            title = urlparse(final_url).netloc

        if not content.strip():
            return ToolResult(
                success=True,
                output=f"## {title or final_url}\n\n페이지에서 추출할 수 있는 본문 텍스트가 없습니다. (JavaScript 렌더링 전용 페이지일 수 있습니다)",
            )

        output = f"## {title}\n\n**URL**: {final_url}\n\n---\n\n{content}"

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "url": final_url,
                "title": title,
                "content_length": len(content),
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_html(self, url: str) -> tuple[str, str]:
        """Fetch HTML content from URL.

        Returns:
            (html_text, final_url_after_redirects)
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko,en;q=0.9",
        }

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            headers=headers,
            verify=False,  # macOS Python SSL cert workaround
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Handle encoding — httpx usually detects, but fallback to utf-8
            html = response.text
            final_url = str(response.url)

            return html, final_url

    def _extract_content(self, html: str, max_length: int) -> tuple[str, str]:
        """Parse HTML and extract title + readable body text.

        Strategy:
        1. Try <article> tag first
        2. Then <main> tag
        3. Then largest <section> or <div> with most paragraph text
        4. Fallback to <body>

        Returns:
            (title, content_text)
        """
        soup = BeautifulSoup(html, "lxml")

        # Title
        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else ""

        # Also check og:title which is often better
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = og_title["content"]

        # Remove noise elements
        for tag_name in NOISE_TAGS:
            for el in soup.find_all(tag_name):
                el.decompose()

        # Try to find the main content area
        content_el = None

        for tag_name in CONTENT_TAGS:
            candidates = soup.find_all(tag_name)
            if not candidates:
                continue

            # Pick the candidate with the most text
            best = max(candidates, key=lambda el: len(el.get_text(strip=True)))
            text_len = len(best.get_text(strip=True))
            if text_len > 200:  # Minimum threshold
                content_el = best
                break

        if content_el is None:
            body = soup.find("body")
            content_el = body if body else soup

        # Extract text from paragraphs first (cleaner), then fallback to all text
        paragraphs = content_el.find_all(
            ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"]
        )
        if (
            paragraphs
            and len(" ".join(p.get_text(strip=True) for p in paragraphs)) > 100
        ):
            raw_text = "\n\n".join(
                p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
            )
        else:
            raw_text = content_el.get_text(separator="\n", strip=True)

        content = self._clean_text(raw_text)

        # Trim to max_length
        if len(content) > max_length:
            content = content[:max_length] + "\n\n... (본문이 너무 길어 잘렸습니다)"

        return title, content

    def _clean_text(self, raw: str) -> str:
        """Clean extracted text: normalize whitespace, remove boilerplate."""
        # Replace multiple newlines with double
        text = re.sub(r"\n{3,}", "\n\n", raw)
        # Replace multiple spaces with single
        text = re.sub(r"[ \t]{2,}", " ", text)
        # Remove lines that are mostly whitespace
        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if line]
        return "\n".join(lines)
