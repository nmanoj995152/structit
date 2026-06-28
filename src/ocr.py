"""Tesseract OCR wrapper for bill text extraction."""

import io
import os
from dataclasses import dataclass
from pathlib import Path

import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

PROJECT_TESSDATA = Path(__file__).resolve().parents[1] / "models" / "tessdata"
WINDOWS_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


@dataclass
class OCRResult:
    text: str
    confidence: float
    error: str = ""


def _configure_tesseract() -> None:
    """Use an explicit local Tesseract binary when one is configured/found."""
    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd:
        pytesseract.pytesseract.tesseract_cmd = env_cmd
    elif WINDOWS_TESSERACT.exists():
        pytesseract.pytesseract.tesseract_cmd = str(WINDOWS_TESSERACT)

    tessdata = _best_tessdata_dir()
    if tessdata:
        os.environ["TESSDATA_PREFIX"] = str(tessdata)


def _best_tessdata_dir() -> Path | None:
    """Prefer project-local OCR data so runtime stays offline and portable."""
    candidates = [
        PROJECT_TESSDATA,
        Path(os.getenv("TESSDATA_PREFIX", "")),
        WINDOWS_TESSERACT.parent / "tessdata",
    ]
    for candidate in candidates:
        if candidate and (candidate / "eng.traineddata").exists():
            return candidate
    return None


def _parse_confidence(value: str) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def run_ocr(image_bytes: bytes) -> OCRResult:
    """
    Run Tesseract on preprocessed image bytes.

    Returns extracted text and mean confidence score. Missing OCR engines and
    unreadable images are reported as structured OCRResult failures so callers
    can persist a graceful error instead of crashing the request.
    """
    _configure_tesseract()

    try:
        image = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config="--oem 3 --psm 6",
            output_type=pytesseract.Output.DICT,
        )
    except TesseractNotFoundError:
        return OCRResult(
            text="",
            confidence=0.0,
            error=(
                "Tesseract OCR executable not found. Install Tesseract locally "
                "or set TESSERACT_CMD to its executable path."
            ),
        )
    except Exception as exc:
        if "eng.traineddata" in str(exc) or "Failed loading language" in str(exc):
            return OCRResult(
                text="",
                confidence=0.0,
                error=(
                    "OCR language data is missing. Add eng.traineddata under "
                    f"{PROJECT_TESSDATA} and restart the app."
                ),
            )
        return OCRResult(text="", confidence=0.0, error=f"OCR failed: {exc}")

    confidences: list[float] = []
    words: list[str] = []
    for index, raw_confidence in enumerate(data.get("conf", [])):
        confidence = _parse_confidence(raw_confidence)
        text = data.get("text", [""])[index].strip()
        if confidence is not None:
            confidences.append(confidence)
            if text:
                words.append(text)

    raw_text = " ".join(words)
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return OCRResult(text=raw_text, confidence=mean_confidence / 100.0)
