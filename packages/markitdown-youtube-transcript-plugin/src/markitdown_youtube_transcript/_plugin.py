import re
from typing import Any, BinaryIO, List, Optional

from markitdown import (
    MarkItDown,
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)


__plugin_interface_version__ = 1  # The version of the plugin interface that this plugin uses

# Matches all common YouTube video URL patterns and extracts the 11-char video ID.
# Supported formats:
#   https://www.youtube.com/watch?v=VIDEO_ID
#   https://youtu.be/VIDEO_ID
#   https://www.youtube.com/embed/VIDEO_ID
#   https://www.youtube.com/shorts/VIDEO_ID
#   https://www.youtube.com/v/VIDEO_ID
_YOUTUBE_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|v/)|youtu\.be/)"
    r"([a-zA-Z0-9_-]{11})",
    re.IGNORECASE,
)

# Optional transcript support via yt-dlp
try:
    from .extract import extract_transcript

    _IS_TRANSCRIPT_CAPABLE = True
except ImportError:
    _IS_TRANSCRIPT_CAPABLE = False


def register_converters(markitdown: MarkItDown, **kwargs: Any) -> None:
    """
    Called during construction of MarkItDown instances to register converters
    provided by this plugin.
    """
    markitdown.register_converter(YouTubeTranscriptConverter())


def _extract_video_id(url: str) -> Optional[str]:
    """Return the 11-character YouTube video ID embedded in *url*, or None."""
    match = _YOUTUBE_VIDEO_ID_RE.search(url)
    return match.group(1) if match else None


class YouTubeTranscriptConverter(DocumentConverter):
    """
    Converts YouTube videos to Markdown.

    Accepts any URL whose ``stream_info.url`` contains a recognisable YouTube
    video reference (watch, youtu.be short link, embed, shorts, or v/ path).

    The converter uses ``yt-dlp`` (via ``extract_transcript``) to:
    1. Extract the video ID from the URL.
    2. Fetch rich video metadata (title, channel, description, views, …).
    3. Download the video transcript (auto-generated captions as fallback).
    4. Return a Markdown document with the metadata and transcript.

    Keyword arguments forwarded from ``MarkItDown.convert()``:

    ``youtube_transcript_languages`` : list[str]
        Ordered list of BCP-47 language codes to try when fetching the
        transcript (e.g. ``["en", "de"]``).  The first entry is passed to
        ``extract_transcript`` as the ``lang`` parameter.  Use ``["auto"]``
        (the default) to let yt-dlp detect the source language automatically.
    """

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        url = stream_info.url or ""
        return _extract_video_id(url) is not None

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        url = stream_info.url or ""
        video_id = _extract_video_id(url)

        if not video_id:
            raise ValueError(
                f"Could not extract a YouTube video ID from URL: {url!r}"
            )

        canonical_url = f"https://www.youtube.com/watch?v={video_id}"

        # Determine transcript language: take the first entry from the list,
        # defaulting to "auto" so yt-dlp detects the source language.
        preferred_languages: Optional[List[str]] = kwargs.get(
            "youtube_transcript_languages"
        )
        lang = preferred_languages[0] if preferred_languages else "auto"

        include_info: bool = kwargs.get("youtube_include_info", False)

        lines: List[str] = []

        if _IS_TRANSCRIPT_CAPABLE:
            info, transcript_text = extract_transcript(canonical_url, lang=lang)

            title: Optional[str] = info.get("title") or None

            if include_info:
                lines.append(f"# {title or 'YouTube Video'}\n")

                # --- Video metadata ---
                lines.append("## Video Info\n")
                if info.get("channel"):
                    lines.append(f"- **Channel:** {info['channel']}")
                lines.append(f"- **Video ID:** `{video_id}`")
                lines.append(f"- **URL:** {canonical_url}")
                if info.get("upload_date"):
                    lines.append(f"- **Upload Date:** {info['upload_date']}")
                if info.get("duration") is not None:
                    lines.append(f"- **Duration:** {info['duration']}s")
                if info.get("view_count") is not None:
                    lines.append(f"- **Views:** {info['view_count']:,}")
                if info.get("like_count") is not None:
                    lines.append(f"- **Likes:** {info['like_count']:,}")
                if info.get("tags"):
                    tags = info["tags"]
                    if isinstance(tags, list):
                        tags = ", ".join(str(t) for t in tags)
                    lines.append(f"- **Tags:** {tags}")
                lines.append("")

                # --- Description ---
                description = info.get("description")
                if description:
                    lines.append("## Description\n")
                    lines.append(description)
                    lines.append("")

            # --- Transcript ---
            if transcript_text and not transcript_text.startswith("ERROR:"):
                if include_info:
                    lines.append("## Transcript\n")
                lines.append(transcript_text)
                lines.append("")

        else:
            # yt-dlp not available
            title = None
            lines.append(f"<!-- Could not fetch transcript for {canonical_url} -->")

        return DocumentConverterResult(
            markdown="\n".join(lines),
            title=title if _IS_TRANSCRIPT_CAPABLE else None,
        )
