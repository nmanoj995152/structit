"""Image and document pre-processing before OCR."""

import io

import cv2
import numpy as np


def preprocess_input(file_bytes: bytes, content_type: str = "") -> bytes:
    """Normalize supported upload bytes to a cleaned PNG."""
    if content_type == "application/pdf" or file_bytes[:4] == b"%PDF":
        return preprocess_image(_render_pdf_first_page(file_bytes))
    return preprocess_image(file_bytes)


def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Take raw image bytes, return a cleaned normalized PNG as bytes.
    Steps: decode, grayscale, deskew, denoise, CLAHE contrast, encode PNG.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode file. Use JPG, PNG, WEBP, or PDF.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = _deskew(gray)
    gray = cv2.fastNlMeansDenoising(gray, h=7)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    success, buffer = cv2.imencode(".png", enhanced)
    if not success:
        raise RuntimeError("Failed to encode processed image as PNG.")

    return buffer.tobytes()


def _render_pdf_first_page(pdf_bytes: bytes) -> bytes:
    """Render the first PDF page locally when pypdfium2 is installed."""
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ValueError(
            "PDF input requires local dependency pypdfium2. "
            "Install project dependencies or upload an image."
        ) from exc

    pdf = pdfium.PdfDocument(pdf_bytes)
    if len(pdf) == 0:
        raise ValueError("PDF has no pages.")

    page = pdf[0]
    bitmap = page.render(scale=2.0)
    image = bitmap.to_pil()
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Detect and correct skew angle in a grayscale image."""
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle

    if abs(angle) < 0.5:
        return gray

    h, w = gray.shape
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        gray,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
