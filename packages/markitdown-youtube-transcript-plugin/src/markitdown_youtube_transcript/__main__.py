#!/usr/bin/env python3
"""CLI entry point for the markitdown-youtube-transcript plugin.

Usage:
    markitdown-yt <URL or video ID> [options]

Examples:
    markitdown-yt https://youtu.be/dQw4w9WgXcQ
    markitdown-yt dQw4w9WgXcQ --info
    markitdown-yt https://youtu.be/dQw4w9WgXcQ --lang de
    markitdown-yt https://youtu.be/dQw4w9WgXcQ -o output.md
"""

import argparse
import sys
from markitdown import MarkItDown


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="markitdown-yt",
        description="Convert a YouTube video to Markdown (transcript + metadata).",
    )
    parser.add_argument("url", help="YouTube video URL or 11-character video ID")
    parser.add_argument(
        "-o",
        "--output",
        help="Write output to this file instead of stdout.",
    )
    parser.add_argument(
        "--lang",
        default="auto",
        help="Transcript language code (e.g. en, de) or 'auto' (default: auto).",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Include video metadata and description alongside the transcript.",
    )

    args = parser.parse_args()

    # Accept a bare video ID as well as a full URL
    url = args.url
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"

    md = MarkItDown(enable_builtins=False, enable_plugins=True)

    convert_kwargs: dict = {
        "youtube_transcript_languages": [args.lang],
        "youtube_include_info": args.info,
    }

    try:
        result = md.convert(url, **convert_kwargs)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(result.markdown)
    else:
        print(
            result.markdown.encode(sys.stdout.encoding, errors="replace").decode(
                sys.stdout.encoding
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
