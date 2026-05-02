#!/usr/bin/env python3 -m pytest
"""Tests for the markitdown-youtube-transcript plugin.

Most tests use mocking to avoid live network calls.  A single optional
integration test (skipped by default) exercises the real YouTube APIs.
"""

import io
from unittest.mock import patch

import pytest

from markitdown import MarkItDown, StreamInfo
from markitdown_youtube_transcript import YouTubeTranscriptConverter
from markitdown_youtube_transcript._plugin import _extract_video_id


# ---------------------------------------------------------------------------
# _extract_video_id
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Non-YouTube URLs should return None
        ("https://example.com/watch?v=dQw4w9WgXcQ", None),
        ("https://vimeo.com/123456789", None),
        ("", None),
    ],
)
def test_extract_video_id(url: str, expected) -> None:
    assert _extract_video_id(url) == expected


# ---------------------------------------------------------------------------
# accepts()
# ---------------------------------------------------------------------------

class TestAccepts:
    def _converter(self) -> YouTubeTranscriptConverter:
        return YouTubeTranscriptConverter()

    def _stream_info(self, url: str) -> StreamInfo:
        return StreamInfo(url=url)

    def test_accepts_watch_url(self) -> None:
        converter = self._converter()
        assert converter.accepts(
            io.BytesIO(b""), self._stream_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

    def test_accepts_short_url(self) -> None:
        converter = self._converter()
        assert converter.accepts(
            io.BytesIO(b""), self._stream_info("https://youtu.be/dQw4w9WgXcQ")
        )

    def test_accepts_shorts_url(self) -> None:
        converter = self._converter()
        assert converter.accepts(
            io.BytesIO(b""), self._stream_info("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        )

    def test_rejects_non_youtube_url(self) -> None:
        converter = self._converter()
        assert not converter.accepts(
            io.BytesIO(b""), self._stream_info("https://vimeo.com/123")
        )

    def test_rejects_empty_url(self) -> None:
        converter = self._converter()
        assert not converter.accepts(io.BytesIO(b""), StreamInfo())


# ---------------------------------------------------------------------------
# Fake data shared across convert() tests
# ---------------------------------------------------------------------------

_FAKE_INFO = {
    "title": "Test Video Title",
    "channel": "Test Channel",
    "upload_date": "20240101",
    "duration": 213,
    "view_count": 1_234_567,
    "like_count": 42_000,
    "tags": ["test", "demo"],
    "description": "A great test video.",
}

_FAKE_TRANSCRIPT_TEXT = "Hello world This is a test"


# ---------------------------------------------------------------------------
# convert() — with mocked extract_transcript
# ---------------------------------------------------------------------------

class TestConvert:
    VIDEO_ID = "dQw4w9WgXcQ"
    WATCH_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"

    def _stream_info(self, url: str = WATCH_URL) -> StreamInfo:
        return StreamInfo(url=url)

    @patch("markitdown_youtube_transcript._plugin.extract_transcript")
    def test_basic_output(self, mock_extract) -> None:
        """Transcript and metadata appear in the markdown output."""
        mock_extract.return_value = (_FAKE_INFO, _FAKE_TRANSCRIPT_TEXT)

        converter = YouTubeTranscriptConverter()
        result = converter.convert(io.BytesIO(b""), self._stream_info())

        assert result.title == "Test Video Title"
        assert "# Test Video Title" in result.markdown
        assert "Test Channel" in result.markdown
        assert self.VIDEO_ID in result.markdown
        assert "Hello world" in result.markdown
        assert "This is a test" in result.markdown
        # Rich metadata fields
        assert "1,234,567" in result.markdown
        assert "42,000" in result.markdown
        assert "A great test video." in result.markdown

    @patch("markitdown_youtube_transcript._plugin.extract_transcript")
    def test_lang_kwarg_passed_through(self, mock_extract) -> None:
        """youtube_transcript_languages first entry is forwarded as lang."""
        mock_extract.return_value = (_FAKE_INFO, _FAKE_TRANSCRIPT_TEXT)

        converter = YouTubeTranscriptConverter()
        converter.convert(
            io.BytesIO(b""),
            self._stream_info(),
            youtube_transcript_languages=["de", "en"],
        )

        _, call_kwargs = mock_extract.call_args
        assert call_kwargs["lang"] == "de"

    @patch("markitdown_youtube_transcript._plugin.extract_transcript")
    def test_default_lang_is_auto(self, mock_extract) -> None:
        """When no language list is given, lang defaults to 'auto'."""
        mock_extract.return_value = (_FAKE_INFO, _FAKE_TRANSCRIPT_TEXT)

        converter = YouTubeTranscriptConverter()
        converter.convert(io.BytesIO(b""), self._stream_info())

        _, call_kwargs = mock_extract.call_args
        assert call_kwargs["lang"] == "auto"

    @patch("markitdown_youtube_transcript._plugin.extract_transcript")
    def test_error_transcript_omitted(self, mock_extract) -> None:
        """An ERROR: prefix in the transcript text suppresses the section."""
        mock_extract.return_value = (_FAKE_INFO, "ERROR: did not produce a transcript")

        converter = YouTubeTranscriptConverter()
        result = converter.convert(io.BytesIO(b""), self._stream_info())

        assert "## Transcript" not in result.markdown
        # Metadata should still appear
        assert "Test Video Title" in result.markdown

    @patch("markitdown_youtube_transcript._plugin.extract_transcript")
    def test_youtu_be_url(self, mock_extract) -> None:
        """youtu.be short URLs are resolved to the canonical watch URL."""
        mock_extract.return_value = (_FAKE_INFO, _FAKE_TRANSCRIPT_TEXT)

        converter = YouTubeTranscriptConverter()
        result = converter.convert(
            io.BytesIO(b""),
            StreamInfo(url=f"https://youtu.be/{self.VIDEO_ID}"),
        )

        assert self.VIDEO_ID in result.markdown
        # Canonical URL should be passed to extract_transcript
        call_args, _ = mock_extract.call_args
        assert call_args[0] == self.WATCH_URL

    @patch("markitdown_youtube_transcript._plugin.extract_transcript")
    def test_plugin_registration(self, mock_extract) -> None:
        """The plugin registers the converter when enable_plugins=True."""
        mock_extract.return_value = (_FAKE_INFO, _FAKE_TRANSCRIPT_TEXT)

        md = MarkItDown(enable_plugins=True)
        converter_types = [type(reg.converter).__name__ for reg in md._converters]
        assert "YouTubeTranscriptConverter" in converter_types


# ---------------------------------------------------------------------------
# Optional live integration test (skipped by default)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Live network test — run manually with -k test_live")
def test_live_transcript() -> None:
    """Fetches a real transcript from YouTube. Requires network access."""
    md = MarkItDown(enable_plugins=True)
    # Short public-domain clip (Big Buck Bunny trailer)
    result = md.convert("https://www.youtube.com/watch?v=aqz-KE-bpKQ")
    assert result.markdown
    assert len(result.markdown) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
