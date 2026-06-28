"""Tesseract OCR wrapper for bill text extraction."""

import pytesseract
from PIL import Image
import io
from dataclasses import dataclass


@dataclass
class OCRResult:
    text: str
    confidence: float  # 0.0 to 1.0


def run_ocr(image_bytes: bytes) -> OCRResult:
    """
    Run Tesseract on preprocessed image bytes.
    Returns extracted text and mean confidence score.
    """
    image = Image.open(io.BytesIO(image_bytes))

    # Get detailed OCR data including confidence per word
    data = pytesseract.image_to_data(
        image,
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT,
    )

    # Collect words with valid confidence (Tesseract returns -1 for non-text)
    confidences = [
        int(c) for c in data["conf"] if int(c) != -1
    ]
    words = [
        data["text"][i]
        for i, c in enumerate(data["conf"])
        if int(c) != -1 and data["text"][i].strip()
    ]

    raw_text = " ".join(words)
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return OCRResult(
        text=raw_text,
        confidence=mean_confidence / 100.0,  # normalize to 0.0–1.0
    )