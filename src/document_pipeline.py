"""Generic offline document-to-JSON pipeline."""

from __future__ import annotations

import hashlib
import time

from src.database import (
    get_document_by_hash,
    init_db,
    insert_document,
)
from src.document_loaders import extract_text_from_file
from src.structurer import structure_text
from src.text_normalizer import normalize_text

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def process_document(
    file_bytes: bytes,
    filename: str,
    content_type: str = "",
    model_runtime: str | None = None,
    use_cache: bool = True,
) -> dict:
    """Run the generic offline StructIt document pipeline."""
    init_db()
    logs: list[str] = []
    timings_ms: dict[str, int] = {}

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("File is too large. Maximum size is 50MB.")

    input_hash = hashlib.sha256(file_bytes).hexdigest()
    if use_cache:
        cached = get_document_by_hash(input_hash)
        if cached:
            cached["cached"] = True
            return cached

    start = time.time()
    extraction = extract_text_from_file(file_bytes, filename, content_type)
    timings_ms["extract"] = _elapsed_ms(start)
    logs.append(f"Extracted text locally from {extraction.source_type}.")
    logs.extend(extraction.warnings)

    start = time.time()
    normalized_text = normalize_text(extraction.text)
    timings_ms["normalize"] = _elapsed_ms(start)
    logs.append("Normalized whitespace and control characters.")

    if not normalized_text:
        structured_json = _empty_structured()
        status = "failed"
        logs.append("No readable text was found.")
    else:
        start = time.time()
        structured_json, status, structure_logs = structure_text(
            normalized_text,
            runtime=model_runtime,
        )
        timings_ms["structure"] = _elapsed_ms(start)
        logs.extend(structure_logs)

    document_id = insert_document(
        filename=filename,
        raw_text=normalized_text,
        structured_json=structured_json,
        input_hash=input_hash,
        source_type=extraction.source_type,
        status=status,
        logs=logs,
    )

    return {
        "id": document_id,
        "filename": filename,
        "source_type": extraction.source_type,
        "status": status,
        "raw_text": normalized_text,
        "structured_json": structured_json,
        "logs": logs,
        "timings_ms": timings_ms,
        "cached": False,
    }


def _empty_structured() -> dict:
    return {
        "title": "",
        "people": [],
        "organizations": [],
        "emails": [],
        "phones": [],
        "dates": [],
        "summary": "",
        "keywords": [],
    }


def _elapsed_ms(start_time: float) -> int:
    return int((time.time() - start_time) * 1000)
