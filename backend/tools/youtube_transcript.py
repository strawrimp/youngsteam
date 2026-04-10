"""YouTube transcript tool for video content analysis."""

import logging
import re
from typing import Any, Dict, Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

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
            "Returns the full transcript with timestamps and speaker information if available."
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
                    "description": "Maximum character length of transcript to return (to avoid overwhelming context). Default: 10000.",
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
                error="youtube-transcript-api 패키지가 설치되지 않았습니다. 'pip install youtube-transcript-api'를 실행하세요.",
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

            # Get transcript with fallback languages
            logger.info(f"Fetching transcript for video: {video_id}")

            # Try multiple languages in priority order
            languages_to_try = []
            if language != "auto":
                languages_to_try.append(language)
            # Add fallback languages
            languages_to_try.extend(["ko", "ko-KR", "en", "en-US", "en-GB"])
            # Remove duplicates while preserving order
            seen = set()
            languages_to_try = [
                x for x in languages_to_try if not (x in seen or seen.add(x))
            ]

            transcript = None
            last_error = None

            for lang in languages_to_try:
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=[lang]
                    )
                    logger.info(f"Successfully fetched transcript in language: {lang}")
                    break
                except Exception as e:
                    last_error = e
                    logger.debug(f"Failed to get transcript for language {lang}: {e}")
                    continue

            if transcript is None:
                # Try manual captions as last resort
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=None
                    )
                    logger.info(
                        "Successfully fetched transcript (no specific language)"
                    )
                except Exception as e2:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"자막을 찾을 수 없습니다. 시도한 언어: {', '.join(languages_to_try)}. 마지막 오류: {str(last_error)[:200]}",
                    )

            # Format transcript
            formatted_text = self._format_transcript(transcript, max_length)

            # Get video metadata
            metadata = self._get_video_info(video_url)

            # Build output
            output = f"""## 📺 YouTube 영상 분석

**영상 ID**: {video_id}
**제목**: {metadata.get("title", "알 수 없음")}
**자막 길이**: {len(formatted_text)} 자
**대략적 분량**: {len(formatted_text) // 200} 분

---

### 📝 자막 (주요 내용)

{formatted_text}

---

### 💡 분석 제안
- 위 자막을 바탕으로 영상의 주요 내용을 요약할 수 있습니다
- 중요 키워드나 인용구를 추출할 수 있습니다
- 영상이 다루는 주제를 분류할 수 있습니다
"""

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "video_id": video_id,
                    "title": metadata.get("title", ""),
                    "transcript_length": len(formatted_text),
                    "original_segments": len(transcript),
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

    def _format_transcript(self, transcript: list, max_length: int) -> str:
        """Format transcript segments into readable text.

        Args:
            transcript: List of transcript segments
            max_length: Maximum character length

        Returns:
            Formatted transcript text
        """
        # Combine segments, removing duplicate timestamps
        segments = []
        for segment in transcript:
            text = segment.get("text", "").strip()
            if text:
                segments.append(text)

        # Join and truncate
        full_text = " ".join(segments)

        # Clean up common issues
        full_text = re.sub(r"\[Music\]", "", full_text)
        full_text = re.sub(r"\[Applause\]", "", full_text)
        full_text = re.sub(r"\s+", " ", full_text)

        # Truncate if too long
        if len(full_text) > max_length:
            full_text = full_text[:max_length] + "... (자막이 너무 길어서 잘랐습니다)"

        return full_text

    def _get_video_info(self, url: str) -> Dict[str, str]:
        """Try to get basic video information.

        Note: Full metadata requires additional API calls, so we provide basic info.
        """
        info = {
            "title": "",
            "channel": "",
            "duration": "",
        }

        # Extract video ID
        video_id = self._extract_video_id(url)
        if video_id:
            info["video_id"] = video_id

        return info
