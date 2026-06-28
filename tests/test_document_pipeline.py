"""Tests for the generic offline document pipeline."""

from src.document_loaders import extract_text_from_file
from src.document_pipeline import process_document
from src.structurer import structure_text
from src.text_normalizer import normalize_text


def test_txt_extraction():
    result = extract_text_from_file(
        b"Project Alpha\nContact: ada@example.com",
        filename="note.txt",
        content_type="text/plain",
    )
    assert result.source_type == "txt"
    assert "ada@example.com" in result.text


def test_text_normalization():
    assert normalize_text(" Hello\t\tWorld\r\n\r\n\r\nNext ") == "Hello World\n\nNext"


def test_rule_structurer_extracts_schema_fields():
    structured, status, logs = structure_text(
        "Project Alpha\nAda Lovelace from Example Ltd met on 28/06/2026. "
        "Email ada@example.com or call +91 98765 43210.",
        runtime="none",
    )
    assert status == "success"
    assert structured["title"] == "Project Alpha"
    assert "ada@example.com" in structured["emails"]
    assert "28/06/2026" in structured["dates"]
    assert "project" in structured["keywords"]
    assert logs


def test_process_document_txt_round_trip():
    result = process_document(
        b"Project Beta\nReach bob@example.com on 2026-06-28.",
        filename="beta.txt",
        content_type="text/plain",
        model_runtime="none",
        use_cache=False,
    )
    assert result["status"] == "success"
    assert result["source_type"] == "txt"
    assert result["structured_json"]["title"] == "Project Beta"
    assert "bob@example.com" in result["structured_json"]["emails"]
