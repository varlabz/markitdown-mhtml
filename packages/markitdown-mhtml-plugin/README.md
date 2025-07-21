# MarkItDown MHTML Plugin

[![PyPI](https://img.shields.io/pypi/v/markitdown-mhtml-plugin.svg)](https://pypi.org/project/markitdown-mhtml-plugin/)
![PyPI - Downloads](https://img.shields.io/pypi/dd/markitdown-mhtml-plugin)
[![Built by AutoGen Team](https://img.shields.io/badge/Built%20by-AutoGen%20Team-blue)](https://github.com/microsoft/autogen)


This project provides an MHTML converter plugin for MarkItDown. MHTML (MIME HTML) files are web archive formats that contain a complete web page and its resources in a single file.

## Features

- Converts MHTML (.mhtml, .mht) files to Markdown
- Extracts HTML content from MHTML archives
- Basic HTML to Markdown conversion
- Handles multipart MHTML structure

## Installation

```bash
pip install markitdown-mhtml-plugin
```

## Usage


```python
from markitdown import MarkItDown

# The plugin will be automatically registered when imported
md = MarkItDown()
result = md.convert("example.mhtml")
print(result.markdown)
```

### Environment Variable: MHTML_ARCHIVE_IS

If the environment variable `MHTML_ARCHIVE_IS` is set to `1`, the converter will extract and convert only the `<div id="CONTENT">` section from the HTML within the MHTML file (if present). This is useful for MHTML files that contain a main content div and you want to ignore other HTML parts.

Example usage:

```bash
export MHTML_ARCHIVE_IS=1
python your_script.py
```

Or in Python:

```python
import os
os.environ["MHTML_ARCHIVE_IS"] = "1"
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert("example.mhtml")
print(result.markdown)
```

## Implementation Details

The MhtmlConverter class implements the DocumentConverter interface:

```python
from typing import BinaryIO, Any
import email
from markitdown import MarkItDown, DocumentConverter, DocumentConverterResult, StreamInfo

class MhtmlConverter(DocumentConverter):

    def __init__(
        self, priority: float = DocumentConverter.PRIORITY_SPECIFIC_FILE_FORMAT
    ):
        super().__init__(priority=priority)

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        # Check if the file is an MHTML file by extension or MIME type
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()
        
        if extension in [".mhtml", ".mht"]:
            return True
            
        for prefix in ["message/rfc822", "multipart/related", "application/x-mimearchive"]:
            if mimetype.startswith(prefix):
                return True
                
        return False

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        # Parse MHTML file as email message and extract HTML content
        stream_data = file_stream.read()
        msg = email.message_from_bytes(stream_data, policy=email.policy.default)
        
        html_content = self._extract_html_from_mhtml(msg)
        markdown_content = self._basic_html_to_markdown(html_content) if html_content else "No HTML content found."
        
        return DocumentConverterResult(
            title=self._extract_title_from_html(html_content) if html_content else None,
            markdown=markdown_content,
        )
```

## Plugin Registration

The package implements and exports the following:

```python
# The version of the plugin interface that this plugin uses. 
# The only supported version is 1 for now.
__plugin_interface_version__ = 1 

# The main entrypoint for the plugin. This is called each time MarkItDown instances are created.
def register_converters(markitdown: MarkItDown, **kwargs):
    """
    Called during construction of MarkItDown instances to register converters provided by plugins.
    """

    # Simply create and attach an MhtmlConverter instance
    markitdown.register_converter(MhtmlConverter())
```

## Entry Point Configuration

The plugin is registered in the `pyproject.toml` file:

```toml
[project.entry-points."markitdown.plugin"]
mhtml_plugin = "markitdown_mhtml_plugin"
```

## Development Installation

To install the plugin for development from the current directory use:

```bash
pip install -e .
```

Once the plugin package is installed, verify that it is available to MarkItDown by running:

```bash
markitdown --list-plugins
```

To use the plugin for a conversion use the `--use-plugins` flag. For example, to convert an MHTML file:

```bash
markitdown --use-plugins path-to-file.mhtml
```

In Python, plugins can be enabled as follows:

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True) 
result = md.convert("path-to-file.mhtml")
print(result.text_content)
```

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
