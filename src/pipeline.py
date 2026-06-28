"""
Main pipeline: image bytes → structured bill record in SQLite.
This is the single entry point that connects all components.
"""

import time
from src.preprocess import preprocess_image
from src.ocr import run_ocr
from src.vlm import describe_bill_image
from src.detector import detect_bill_type
from src.extractor import extract_structured
from src.database import init_db, insert_bill, log_stage


def process_bill(image_bytes: bytes, image_path: str = "") -> dict:
    """
    Full pipeline: raw image → structured JSON → SQLite.
    Returns a result dict with bill_id, structured data, and status.
    """
    init_db()
    timings = {}

    # Step 1 — Pre-process image
    t0 = time.time()
    clean_image = preprocess_image(image_bytes)
    timings["preprocess"] = int((time.time() - t0) * 1000)

    # Step 2 — OCR
    t0 = time.time()
    ocr_result = run_ocr(clean_image)
    timings["ocr"] = int((time.time() - t0) * 1000)

    # Step 3 — VLM (skip if OCR confidence is very high to save time)
    t0 = time.time()
    if ocr_result.confidence >= 0.85:
        vlm_description = "High-confidence OCR — skipped VLM for speed."
    else:
        vlm_description = describe_bill_image(clean_image)
    timings["vlm"] = int((time.time() - t0) * 1000)

    # Step 4 — Detect bill type
    bill_type = detect_bill_type(ocr_result.text, vlm_description)

    # Step 5 — SLM extraction
    t0 = time.time()
    structured, status = extract_structured(
        ocr_text=ocr_result.text,
        vlm_description=vlm_description,
        bill_type=bill_type,
    )
    timings["slm"] = int((time.time() - t0) * 1000)

    # Step 6 — Save to SQLite
    bill_id = insert_bill(
        bill_type=bill_type,
        structured=structured,
        raw_ocr=ocr_result.text,
        status=status,
        image_path=image_path,
    )

    # Log timing for each stage
    for stage, duration_ms in timings.items():
        log_stage(bill_id, stage, duration_ms)

    return {
        "bill_id": bill_id,
        "bill_type": bill_type,
        "status": status,
        "structured": structured,
        "timings_ms": timings,
        "ocr_confidence": round(ocr_result.confidence, 2),
    }