# markitdown-youtube-transcript-plugin

A [MarkItDown](https://github.com/microsoft/markitdown) plugin that converts YouTube videos to Markdown by fetching their transcripts and metadata.

## Supported URL formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`

## Installation

```bash
pip install markitdown-youtube-transcript-plugin
```

## Usage

### With the `markitdown` CLI

```bash
markitdown --use-plugins https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### As a Python library

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert("https://youtu.be/dQw4w9WgXcQ")
print(result.markdown)
```

### With timestamps

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    include_timestamps=True,
)
print(result.markdown)
```

### Specifying transcript languages

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    youtube_transcript_languages=["en", "de"],
)
print(result.markdown)
```

## Output format

The plugin produces Markdown like the following:

```markdown
# Never Gonna Give You Up

## Video Info

- **Channel:** Rick Astley
- **Video ID:** `dQw4w9WgXcQ`
- **URL:** https://www.youtube.com/watch?v=dQw4w9WgXcQ

## Transcript

We're no strangers to love You know the rules and so do I ...
```

## Options

| kwarg | Type | Default | Description |
|---|---|---|---|
| `youtube_transcript_languages` | `list[str]` | `["en", <first available>]` | Ordered BCP-47 language codes to try |
| `include_timestamps` | `bool` | `False` | Prefix each segment with `[MM:SS]` |

## Dependencies

- [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/) — transcript fetching
- Video metadata is retrieved from YouTube's public oEmbed endpoint (no API key needed)
