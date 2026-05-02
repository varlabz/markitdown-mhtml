#!/usr/bin/env -S uvx --with yt-dlp python 
"""Extract YouTube transcripts."""

import argparse
import os
import re
import sys
import tempfile
import time
from typing import Tuple
from yt_dlp import YoutubeDL 


def clean_vtt(text: str) -> str:
    """Strip VTT markup and metadata, removing duplicate consecutive lines."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("WEBVTT"):
            continue
        if stripped.startswith("NOTE"):
            continue
        if "-->" in stripped:
            continue
        # Skip header lines like "Kind: captions", "Language: en"
        if re.match(r"^(Kind|Language|Voice|CSS):", stripped):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return "\n".join(lines)


def _parse_input(value: str) -> Tuple[str, str]:
    """Extract video ID and canonical URL from a YouTube URL or ID."""
    patterns = [
        r"v=([a-zA-Z0-9_-]{6,})",
        r"youtu\.be/([a-zA-Z0-9_-]{6,})",
    ]
    for pat in patterns:
        match = re.search(pat, value)
        if match:
            video_id = match.group(1)
            return video_id, f"https://www.youtube.com/watch?v={video_id}"
    if re.fullmatch(r"[a-zA-Z0-9_-]{6,}", value):
        return value, f"https://www.youtube.com/watch?v={value}"
    raise RuntimeError("Could not parse video id from input")


def _format_info(info: dict) -> str:
    """Format video info dict into a string."""
    lines = []
    for key in ("title", "description", "channel", "upload_date", "duration", "view_count", "like_count", "channel_id", "channel_url", "tags", "categories", "license", "creator", "release_year", "average_rating", "comment_count", "age_limit", "webpage_url"):
        value = info.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{key.upper()}: {value}")
    lines.append("\n")
    return "\n".join(lines)


def _resolve_lang(info: dict, lang: str) -> str:
    """Resolve 'auto' to the video's detected source language.

    yt-dlp detects the source language and stores it in info['language'].
    Auto-generated captions exist in info['automatic_captions'] under
    the key 'ab' (a sentinel, not a real language code). Using 'ab'
    as subtitleslangs causes YouTube to return HTTP 429 because it
    tries to translate to Abkhazian which has no captions.
    """
    if lang != "auto":
        return lang
    # Use yt-dlp's detected source language (e.g. 'en')
    detected = info.get("language")
    if detected:
        return detected
    raise RuntimeError("No subtitles available for this video")


def _download_subtitles(url: str, tmpdir: str, selected: str) -> list:
    """Download subtitles and return list of VTT filenames."""
    sub_opts = {
        "skip_download": True,
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": [selected],
        "subtitlesformat": "vtt",
        "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [],
    }
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    old_out_fd = os.dup(1)
    old_err_fd = os.dup(2)
    os.dup2(devnull_fd, 1)
    os.dup2(devnull_fd, 2)
    os.close(devnull_fd)

    try:
        with YoutubeDL(sub_opts) as inner_ydl:
            inner_ydl.download([url])
    finally:
        os.dup2(old_out_fd, 1)
        os.dup2(old_err_fd, 2)
        os.close(old_out_fd)
        os.close(old_err_fd)

    return [p for p in os.listdir(tmpdir) if p.endswith(".vtt")]


def _try_auto_subtitles(info: dict, url: str, tmpdir: str, fallback_lang: str = None) -> list:
    """Try to download auto-generated subtitles as a fallback.

    If fallback_lang is specified (e.g. 'en'), try that first, then other
    available auto-generated languages. Otherwise try all available langs.

    Returns list of VTT filenames, or empty list if none found.
    """
    auto_subs = info.get("automatic_captions")
    if not auto_subs:
        return []

    # Collect all available auto-generated language codes
    # Structure: {"ab": [{"ext": "vtt", "url": "..."}, ...], "en": [...]}
    langs = set()
    for lang_code, formats in auto_subs.items():
        if isinstance(formats, list) and formats:
            langs.add(lang_code)

    if not langs:
        return []

    # Build ordered list: fallback_lang first (if specified and available), then rest
    ordered_langs = []
    if fallback_lang and fallback_lang in langs:
        ordered_langs.append(fallback_lang)
        langs.discard(fallback_lang)
    ordered_langs.extend(sorted(langs))

    # Try each language with retries to avoid HTTP 429 rate limiting
    for lang_code in ordered_langs:
        for attempt in range(3):
            try:
                vtt_files = _download_subtitles(url, tmpdir, lang_code)
                if vtt_files:
                    return vtt_files
                break  # No files for this language, move to next
            except Exception:
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))  # Exponential backoff: 3s, 6s
                else:
                    sys.stderr.write(f"  Failed for language '{lang_code}' after 3 attempts\n")
    return []


def extract_transcript(url: str, lang: str, raw: bool = False) -> Tuple[dict, str]:
    """Extract transcript from a YouTube video using the yt-dlp Python module.

    Performs a single extract_info call to get both video metadata and
    subtitle availability, then downloads the requested subtitles.
    If the primary transcript fails, falls back to auto-generated subtitles.

    Args:
        url: YouTube video URL.
        lang: Language code (e.g. 'en', 'de') or 'auto'.
        raw: If True, return raw VTT instead of cleaned text.

    Returns:
        Tuple of (info dict, cleaned transcript text or raw VTT).

    Raises:
        RuntimeError: If yt-dlp is not installed or no transcript is found.
    """

    # Single extract_info call to get metadata + subtitle info
    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Resolve 'auto' to the actual source language
    selected = _resolve_lang(info, lang)

    with tempfile.TemporaryDirectory() as tmpdir:
        # --- Primary attempt: requested language subtitles ---
        vtt_files = _download_subtitles(url, tmpdir, selected)

        # --- Fallback: auto-generated subtitles ---
        if not vtt_files:
            fallback_lang = "en" if lang == "auto" else None
            vtt_files = _try_auto_subtitles(info, url, tmpdir, fallback_lang=fallback_lang)

        if not vtt_files:
            return info, "ERROR: did not produce a transcript"

        vtt_path = os.path.join(tmpdir, vtt_files[0])
        with open(vtt_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            text = raw_text if raw else clean_vtt(raw_text)
            return info, text


def main() -> int:
    """CLI entry point for transcript extraction."""
    parser = argparse.ArgumentParser(
        description="Extract YouTube transcript using yt-dlp Python module."
    )
    parser.add_argument("input", help="YouTube URL or video ID")
    parser.add_argument(
        "--lang",
        default="auto",
        help="Transcript language code (e.g. en, de) or 'auto'",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw VTT transcript without cleaning",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print video info (title, description, etc.)",
    )
    args = parser.parse_args()

    try:
        video_id, url = _parse_input(args.input)
    except Exception as exc:
        sys.stderr.write(f"Failed to parse input '{args.input}': {exc}\n")
        return 1

    try:
        info, text = extract_transcript(url, args.lang, raw=args.raw)
        if args.info:
            print(_format_info(info))
            print("TRANSCRIPT:")
        print(text)
        return 0
    except Exception as exc:
        sys.stderr.write(f"Failed to extract transcript for '{args.input}': {exc}\n")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
