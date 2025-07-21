#!/usr/bin/env python3 -m pytest
import os
from contextlib import contextmanager

from markitdown import MarkItDown, StreamInfo
from markitdown_mhtml_plugin import MhtmlConverter

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")

# Test data
MHTML_TEST_STRINGS = {
    "This is a Test MHTML File",
    "It is included to test if the MarkItDown MHTML plugin can correctly convert MHTML files.",
    "MHTML (MIME HTML) is a web archive format",
}

CONTENT_DIV_STRINGS = {
    "Main Content Title",
    "This is the main content that should be extracted when MHTML\\_ARCHIVE\\_IS=1.",
    "Only this content should appear in the markdown output.",
    "Content item 1",
    "Content item 2",
}

EXCLUDED_STRINGS = {
    "This is a header that should be ignored",
    "Header content that should not appear in the output",
    "Footer content that should be ignored",
}

NO_CONTENT_DIV_STRINGS = {
    "No Content Div Here",
    "This MHTML file has no div with id CONTENT",
    "Should fall back to full content",
}


@contextmanager
def archive_mode_enabled():
    """Context manager for setting MHTML_ARCHIVE_IS=1."""
    os.environ['MHTML_ARCHIVE_IS'] = '1'
    try:
        yield
    finally:
        if 'MHTML_ARCHIVE_IS' in os.environ:
            del os.environ['MHTML_ARCHIVE_IS']


@contextmanager
def archive_mode_disabled():
    """Context manager for ensuring MHTML_ARCHIVE_IS is not set."""
    if 'MHTML_ARCHIVE_IS' in os.environ:
        del os.environ['MHTML_ARCHIVE_IS']
    yield


def convert_mhtml_file(filename: str) -> str:
    """Helper to convert MHTML file and return text content."""
    md = MarkItDown(enable_plugins=True)
    test_file_path = os.path.join(TEST_FILES_DIR, filename)
    with open(test_file_path, "rb") as file:
        result = md.convert_stream(file, file_extension=".mhtml")
    return result.text_content


def assert_strings_present(content: str, strings: set):
    """Assert all strings are present in content."""
    for string in strings:
        assert string in content, f"Expected '{string}' in output"


def assert_strings_absent(content: str, strings: set):
    """Assert all strings are absent from content."""
    for string in strings:
        assert string not in content, f"Did not expect '{string}' in output"


def test_extract_content_div_valid_html():
    """Test that _extract_content returns the correct HTML when a valid CONTENT div is present."""
    converter = MhtmlConverter()
    html_with_content_div = '<html><body><div id="CONTENT"><p>Hello</p></div></body></html>'
    filters = [{"name": "div", "attrs": {"id": "CONTENT"}}]
    extracted_html = converter._extract_content(html_with_content_div, filters)
    assert extracted_html is not None
    assert extracted_html.strip().startswith('<html')
    assert '<body>' in extracted_html
    assert '<div id="CONTENT"><p>Hello</p></div>' in extracted_html


def test_extract_content_div_no_div():
    """Test that _extract_content returns the original HTML when no CONTENT div is found."""
    converter = MhtmlConverter()
    html_without_content_div = '<html><body><div><p>No content div</p></div></body></html>'
    filters = [{"name": "div", "attrs": {"id": "CONTENT"}}]
    extracted_html = converter._extract_content(html_without_content_div, filters)
    assert extracted_html == html_without_content_div


def test_converter() -> None:
    """Tests the MHTML converter directly."""
    test_file_path = os.path.join(TEST_FILES_DIR, "test.mhtml")
    
    with open(test_file_path, "rb") as file:
        converter = MhtmlConverter()
        result = converter.convert(
            file_stream=file,
            stream_info=StreamInfo(
                mimetype="message/rfc822", extension=".mhtml", filename="test.mhtml"
            ),
        )

    assert_strings_present(result.text_content, MHTML_TEST_STRINGS)


def test_markitdown() -> None:
    """Tests that MarkItDown correctly loads the plugin."""
    content = convert_mhtml_file("test.mhtml")
    assert_strings_present(content, MHTML_TEST_STRINGS)


def test_content_div_extraction() -> None:
    """Tests div extraction when MHTML_ARCHIVE_IS=1."""
    with archive_mode_enabled():
        content = convert_mhtml_file("test_with_content_div.mhtml")
        assert_strings_present(content, CONTENT_DIV_STRINGS)
        assert_strings_absent(content, EXCLUDED_STRINGS)


def test_content_div_extraction_disabled() -> None:
    """Tests full HTML processing when MHTML_ARCHIVE_IS is not set."""
    with archive_mode_disabled():
        content = convert_mhtml_file("test_with_content_div.mhtml")
        assert_strings_present(content, CONTENT_DIV_STRINGS)
        assert_strings_present(content, EXCLUDED_STRINGS)


def test_no_content_div_fallback() -> None:
    """Tests fallback to full HTML when no CONTENT div exists."""
    with archive_mode_enabled():
        content = convert_mhtml_file("test_no_content_div.mhtml")
        assert_strings_present(content, NO_CONTENT_DIV_STRINGS)


def test_malformed_html_handling() -> None:
    """Tests graceful handling of malformed HTML."""
    with archive_mode_enabled():
        content = convert_mhtml_file("test_malformed_html.mhtml")
        assert "Malformed Content" in content
        assert len(content.strip()) > 0


def test_empty_content_div() -> None:
    """Tests behavior with empty CONTENT div."""
    with archive_mode_enabled():
        content = convert_mhtml_file("test_empty_content_div.mhtml")
        assert_strings_absent(content, {"Header content", "Footer content"})
        assert len(content.strip()) == 0


def test_invalid_env_var_values() -> None:
    """Tests that only MHTML_ARCHIVE_IS=1 triggers div extraction."""
    test_values = ['0', 'true', 'false', 'yes', 'no', '2', '', 'invalid']
    
    for test_value in test_values:
        os.environ['MHTML_ARCHIVE_IS'] = test_value
        try:
            content = convert_mhtml_file("test_with_content_div.mhtml")
            assert_strings_present(content, EXCLUDED_STRINGS)
        finally:
            if 'MHTML_ARCHIVE_IS' in os.environ:
                del os.environ['MHTML_ARCHIVE_IS']
    
    
@contextmanager
def medium_mode_enabled():
    """Context manager for setting MHTML_MEDIUM=1."""
    os.environ['MHTML_MEDIUM'] = '1'
    try:
        yield
    finally:
        if 'MHTML_MEDIUM' in os.environ:
            del os.environ['MHTML_MEDIUM']

def test_medium_article_extraction() -> None:
    """Tests <article> extraction when MHTML_MEDIUM=1."""
    with medium_mode_enabled():
        content = convert_mhtml_file("test_blog.html")
        # Should contain main article content
        assert "Blog Post Title" in content
        assert "This is the main article content." in content
        # Should not contain unrelated sidebar/footer
        assert "Sidebar content" not in content
        assert "Footer info" not in content

def test_medium_article_extraction_disabled() -> None:
    """Tests full HTML processing when MHTML_MEDIUM is not set."""
    if 'MHTML_MEDIUM' in os.environ:
        del os.environ['MHTML_MEDIUM']
    content = convert_mhtml_file("test_blog.html")
    # Should contain both article and sidebar/footer
    assert "Blog Post Title" in content
    assert "This is the main article content." in content
    assert "Sidebar content" in content
    assert "Footer info" in content

def test_invalid_medium_env_var_values() -> None:
    """Tests that only MHTML_MEDIUM=1 triggers article extraction."""
    test_values = ['0', 'true', 'false', 'yes', 'no', '2', '', 'invalid']
    for test_value in test_values:
        os.environ['MHTML_MEDIUM'] = test_value
        try:
            content = convert_mhtml_file("test_blog.html")
            # Should contain sidebar/footer if not exactly '1'
            assert "Sidebar content" in content
            assert "Footer info" in content
        finally:
            if 'MHTML_MEDIUM' in os.environ:
                del os.environ['MHTML_MEDIUM']


def test_multiple_content_divs() -> None:
    """Tests behavior with multiple CONTENT divs (extracts first)."""
    with archive_mode_enabled():
        content = convert_mhtml_file("test_multiple_content_divs.mhtml")
        assert "First content div" in content
        assert "Other content" not in content


if __name__ == "__main__":
    """Run all tests."""
    tests = [
        # Basic functionality
        test_converter,
        test_markitdown,
        test_extract_content_div_valid_html,
        test_extract_content_div_no_div,
        # CONTENT div extraction
        test_content_div_extraction,
        test_content_div_extraction_disabled,
        # Edge cases and error handling
        test_no_content_div_fallback,
        test_malformed_html_handling,
        test_empty_content_div,
        test_invalid_env_var_values,
        test_multiple_content_divs,
        # MEDIUM article extraction
        test_medium_article_extraction,
        test_medium_article_extraction_disabled,
        test_invalid_medium_env_var_values,
    ]
    for test in tests:
        test()
    print("All tests passed.")
