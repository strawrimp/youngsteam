"""YouTube transcript tool for video content analysis.

Supports youtube-transcript-api v1.x (new API).
"""

import logging
import re
from typing import Any, Dict, Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi

    YTTA_VERSION = "new"
except ImportError:
    YouTubeTranscriptApi = None
    YTTA_VERSION = None

from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class YouTubeTranscriptTool(BaseTool):
    """Extract and analyze YouTube video transcripts."""

    @property
    def name(self) -> str:
        return "youtube_transcript"

    @property
    def description(self) -> str:
        return (
            "Get YouTube video transcript for content analysis. "
            "Use this when the user mentions a YouTube video or URL. "
            "Extracts video captions/subtitles as text that can be analyzed, summarized, or discussed. "
            "Returns the full transcript with timestamps."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "The YouTube video URL (e.g., https://www.youtube.com/watch?v=...)",
                },
                "language": {
                    "type": "string",
                    "description": "Preferred transcript language code (e.g., 'ko' for Korean, 'en' for English). Defaults to auto-detect.",
                    "default": "auto",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum character length of transcript to return. Default: 10000.",
                    "default": 10000,
                },
            },
            "required": ["video_url"],
        }

    async def execute(
        self, video_url: str, language: str = "auto", max_length: int = 10000
    ) -> ToolResult:
        """Extract YouTube video transcript.

        Args:
            video_url: YouTube video URL
            language: Preferred language code
            max_length: Maximum character length

        Returns:
            ToolResult with transcript text or error message
        """
        if YouTubeTranscriptApi is None:
            return ToolResult(
                success=False,
                output="",
                error="youtube-transcript-api 패키지가 설치되지 않았습니다.",
            )

        try:
            # Extract video ID from URL
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"유효하지 않은 YouTube URL: {video_url}",
                )

            logger.info(f"Fetching transcript for video: {video_id}")

            # --- New API (v1.x) ---
            api = YouTubeTranscriptApi()

            # Build language priority list
            languages_to_try = []
            if language != "auto":
                languages_to_try.append(language)
            languages_to_try.extend(["ko", "en"])
            # Remove duplicates
            seen = set()
            languages_to_try = [
                x for x in languages_to_try if not (x in seen or seen.add(x))
            ]

            transcript_data = None
            last_error = None

            for lang in languages_to_try:
                try:
                    transcript_data = api.fetch(video_id, languages=[lang])
                    logger.info(f"Successfully fetched transcript in language: {lang}")
                    break
                except Exception as e:
                    last_error = e
                    logger.debug(f"Failed to get transcript for language {lang}: {e}")
                    continue

            if transcript_data is None:
                # Last resort: try without language
                try:
                    transcript_data = api.fetch(video_id)
                    logger.info("Fetched transcript (no specific language)")
                except Exception as e2:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"자막을 찾을 수 없습니다. 시도한 언어: {', '.join(languages_to_try)}. 오류: {str(last_error)[:200]}",
                    )

            # Format transcript - handle both dict and object segments
            formatted_text = self._format_transcript(transcript_data, max_length)
            segment_count = len(transcript_data)

            # Build output
            output = f"""## 📺 YouTube 영상 자막

**영상 ID**: {video_id}
**자막 세그먼트 수**: {segment_count}
**자막 길이**: {len(formatted_text)} 자

---

### 📝 자막 내용

{formatted_text}

---

이 자막 내용을 바탕으로 영상을 요약하거나 분석해주세요."""

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "video_id": video_id,
                    "transcript_length": len(formatted_text),
                    "segment_count": segment_count,
                },
            )

        except Exception as e:
            logger.error(f"YouTube transcript error: {e}")
            return ToolResult(
                success=False, output="", error=f"자막 추출 중 오류 발생: {str(e)}"
            )

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)",
            r"(?:youtube\.com\/watch\?.*?v=)([^&\n?#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _format_transcript(self, transcript_data, max_length: int) -> str:
        """Format transcript segments into readable text.

        Handles both dict format (old API) and object format (new API v1.x).
        """
        segments = []
        for segment in transcript_data:
            # New API returns objects with .text attribute
            if hasattr(segment, "text"):
                text = segment.text.strip()
            elif isinstance(segment, dict):
                text = segment.get("text", "").strip()
            else:
                text = str(segment).strip()

            if text:
                segments.append(text)

        full_text = " ".join(segments)

        # Clean up
        full_text = re.sub(r"\[Music\]", "", full_text)
        full_text = re.sub(r"\[Applause\]", "", full_text)
        full_text = re.sub(r"\s+", " ", full_text)

        if len(full_text) > max_length:
            full_text = full_text[:max_length] + "... (자막이 너무 길어서 잘랐습니다)"

        return full_text
