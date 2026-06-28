"""
Main pipeline: upload bytes to structured bill record in SQLite.

The runtime path is offline-first: all work is local, and a deterministic
extractor keeps the app usable on CPU-only machines without a GGUF model.
"""

from __future__ import annotations

import hashlib
import time

from src.database import get_bill_by_hash, init_db, insert_bill, log_stage
from src.detector import detect_bill_type
from src.extractor import extract_structured
from src.ocr import run_ocr
from src.preprocess import preprocess_input
from src.schemas import SCHEMA_MAP
from src.vlm import describe_bill_image


def process_bill(
    file_bytes: bytes,
    image_path: str = "",
    content_type: str = "",
    use_cache: bool = True,
) -> dict:
    """
    Full pipeline: raw upload to structured JSON to SQLite.

    Returns a result dict with bill_id, structured data, status, timings, and
    OCR confidence. If the same bytes were processed before, the cached DB
    record is returned without recomputing OCR/SLM work.
    """
    init_db()
    input_hash = hashlib.sha256(file_bytes).hexdigest()
    if use_cache:
        cached = get_bill_by_hash(input_hash)
        if cached and cached["status"] == "success":
            return {
                "bill_id": cached["id"],
                "bill_type": cached["bill_type"],
                "status": cached["status"],
                "structured": cached["structured"],
                "timings_ms": {"cache": 0},
                "ocr_confidence": None,
                "cached": True,
            }

    timings: dict[str, int] = {}
    stage_errors: dict[str, str] = {}

    t0 = time.time()
    try:
        clean_image = preprocess_input(file_bytes, content_type=content_type)
    except Exception as exc:
        timings["preprocess"] = _elapsed_ms(t0)
        structured = _failure_payload("invoice", f"Preprocess failed: {exc}")
        bill_id = _persist_failure(
            "invoice",
            structured,
            image_path,
            input_hash,
            timings,
            stage_errors={"preprocess": str(exc)},
        )
        return _result(
            bill_id,
            "invoice",
            "failed",
            structured,
            timings,
            0.0,
            stage_errors,
        )
    timings["preprocess"] = _elapsed_ms(t0)

    t0 = time.time()
    ocr_result = run_ocr(clean_image)
    timings["ocr"] = _elapsed_ms(t0)
    if ocr_result.error:
        stage_errors["ocr"] = ocr_result.error

    t0 = time.time()
    vlm_description = ""
    if ocr_result.confidence < 0.60 and not ocr_result.error:
        try:
            vlm_description = describe_bill_image(clean_image)
        except Exception as exc:
            stage_errors["vlm"] = str(exc)
    timings["vlm"] = _elapsed_ms(t0)

    if ocr_result.error or not ocr_result.text.strip():
        bill_type = "invoice"
    else:
        bill_type = detect_bill_type(ocr_result.text, vlm_description)

    t0 = time.time()
    structured, status = extract_structured(
        ocr_text=ocr_result.text,
        vlm_description=vlm_description,
        bill_type=bill_type,
    )
    timings["slm"] = _elapsed_ms(t0)

    if ocr_result.error:
        status = "failed"
        structured["error"] = ocr_result.error
    elif not ocr_result.text.strip():
        status = "failed"
        structured["error"] = "No readable OCR text found."
    elif ocr_result.confidence < 0.60 and status == "success":
        status = "partial"
        structured["warning"] = "Low OCR confidence; verify extracted values."

    bill_id = insert_bill(
        bill_type=bill_type,
        structured=structured,
        raw_ocr=ocr_result.text,
        status=status,
        image_path=image_path,
        input_hash=input_hash,
    )

    for stage, duration_ms in timings.items():
        log_stage(
            bill_id,
            stage,
            duration_ms,
            status="failed" if stage in stage_errors else "success",
            error=stage_errors.get(stage, ""),
        )

    return _result(
        bill_id,
        bill_type,
        status,
        structured,
        timings,
        round(ocr_result.confidence, 2),
        stage_errors,
    )


def _failure_payload(bill_type: str, error: str) -> dict:
    model_class = SCHEMA_MAP.get(bill_type, SCHEMA_MAP["invoice"])
    structured = model_class().model_dump(mode="json")
    structured["error"] = error
    return structured


def _persist_failure(
    bill_type: str,
    structured: dict,
    image_path: str,
    input_hash: str,
    timings: dict[str, int],
    stage_errors: dict[str, str],
) -> int:
    bill_id = insert_bill(
        bill_type=bill_type,
        structured=structured,
        raw_ocr="",
        status="failed",
        image_path=image_path,
        input_hash=input_hash,
    )
    for stage, duration_ms in timings.items():
        log_stage(
            bill_id,
            stage,
            duration_ms,
            status="failed" if stage in stage_errors else "success",
            error=stage_errors.get(stage, ""),
        )
    return bill_id


def _result(
    bill_id: int,
    bill_type: str,
    status: str,
    structured: dict,
    timings: dict[str, int],
    ocr_confidence: float | None,
    stage_errors: dict[str, str],
) -> dict:
    return {
        "bill_id": bill_id,
        "bill_type": bill_type,
        "status": status,
        "structured": structured,
        "timings_ms": timings,
        "ocr_confidence": ocr_confidence,
        "stage_errors": stage_errors,
        "cached": False,
    }


def _elapsed_ms(start_time: float) -> int:
    return int((time.time() - start_time) * 1000)
