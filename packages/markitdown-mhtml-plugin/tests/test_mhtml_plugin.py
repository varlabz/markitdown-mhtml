#!/usr/bin/env python3 -m pytest
import os
import io

from markitdown import MarkItDown, StreamInfo
from markitdown_mhtml_plugin import MhtmlConverter

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")

MHTML_TEST_STRINGS = {
    "This is a Test MHTML File",
    "It is included to test if the MarkItDown MHTML plugin can correctly convert MHTML files.",
    "MHTML (MIME HTML) is a web archive format",
}


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

    for test_string in MHTML_TEST_STRINGS:
        assert test_string in result.text_content


def test_markitdown() -> None:
    """Tests that MarkItDown correctly loads the plugin."""
    md = MarkItDown(enable_plugins=True)
    
    test_file_path = os.path.join(TEST_FILES_DIR, "test.mhtml")
    with open(test_file_path, "rb") as file:
        result = md.convert_stream(file, file_extension=".mhtml")

    for test_string in MHTML_TEST_STRINGS:
        assert test_string in result.text_content


if __name__ == "__main__":
    """Runs this file's tests from the command line."""
    # test_converter()
    test_markitdown()
    print("All tests passed.")
