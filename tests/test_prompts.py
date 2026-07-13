"""Unit tests for user-content assembly (no API calls)."""

import pytest

from app.prompts import build_file_content, build_user_content


def test_text_content_is_single_text_block():
    content = build_user_content("USCIS I-797C ...")
    assert len(content) == 1
    assert content[0]["type"] == "text"
    assert "USCIS I-797C" in content[0]["text"]


def test_pdf_document_block_first():
    content = build_file_content("Zm9v", "application/pdf")
    assert content[0]["type"] == "document"
    assert content[0]["source"] == {
        "type": "base64",
        "media_type": "application/pdf",
        "data": "Zm9v",
    }
    assert content[-1]["type"] == "text"  # instruction follows the document


def test_image_uses_image_block():
    content = build_file_content("Zm9v", "image/png")
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"


def test_unsupported_media_type_raises():
    with pytest.raises(ValueError):
        build_file_content("Zm9v", "text/plain")
