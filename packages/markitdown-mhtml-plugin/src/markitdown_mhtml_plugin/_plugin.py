import io
import os
from email import message_from_string
from typing import BinaryIO, Any

from bs4 import BeautifulSoup
from markitdown import (
    MarkItDown,
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)

__plugin_interface_version__ = (
    1  # The version of the plugin interface that this plugin uses
)

ACCEPTED_MIME_TYPE_PREFIXES = [
    "message/rfc822",
    "multipart/related",
    "application/x-mimearchive",
]

ACCEPTED_FILE_EXTENSIONS = [".mhtml", ".mht"]


def register_converters(markitdown: MarkItDown, **kwargs):
    """Register the MHTML converter with MarkItDown."""
    markitdown.register_converter(MhtmlConverter())


class MhtmlConverter(DocumentConverter):
    """Converts MHTML files to Markdown by extracting HTML content."""

    def __init__(self):
        self._markitdown = MarkItDown(enable_plugins=False)

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        return (extension in ACCEPTED_FILE_EXTENSIONS or 
                any(mimetype.startswith(prefix) for prefix in ACCEPTED_MIME_TYPE_PREFIXES))

    def convert(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> DocumentConverterResult:
        encoding = stream_info.charset or 'utf-8'
        mhtml_content = file_stream.read().decode(encoding)
        
        html_content = self._extract_html_from_mhtml(mhtml_content)
        if not html_content:
            return DocumentConverterResult(
                title=None,
                markdown="HTML content not found in MHTML file."
            )

        # Extract specific div content if environment variable is set
        if os.getenv('MHTML_ARCHIVE_IS') == '1':
            content_div_html = self._extract_content_div(html_content)
            if content_div_html:
                html_content = content_div_html

        # Convert HTML to Markdown using MarkItDown's public API
        html_stream = io.BytesIO(html_content.encode('utf-8'))
        result = self._markitdown.convert_stream(html_stream, file_extension='.html', )
        return DocumentConverterResult(
            title=result.title,
            markdown=result.text_content
        )

    def _extract_html_from_mhtml(self, mhtml_content: str) -> str:
        """Extract the largest HTML content from MHTML string."""
        # hacky way to parse MHTML content and get the largest HTML part
        # This is a simplified example; a more robust implementation would be needed for production use.
        msg = message_from_string(mhtml_content)
        largest_html = None
        largest_size = 0
        
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode('utf-8')
                    if len(html) > largest_size:
                        largest_size = len(html)
                        largest_html = html
        
        return largest_html

    def _extract_content_div(self, html_content: str) -> str:
        """Extract the div with id='CONTENT' from HTML using BeautifulSoup."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            content_div = soup.find('div', id='CONTENT')
            if content_div:
                # Create a new valid HTML page with the content_div
                new_soup = BeautifulSoup('<html><head><title></title></head><body></body></html>', 'html.parser')
                new_soup.body.append(content_div)
                return str(new_soup)
            else:
                return None
                
        except Exception as e:
            return None

