"""Image pre-processing before OCR and VLM."""

import cv2
import numpy as np
from PIL import Image
import io


def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Take raw image bytes, return a cleaned normalized PNG as bytes.
    Steps: decode → grayscale → deskew → CLAHE contrast → encode PNG
    """
    # Decode image bytes into numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image. Check format (JPG, PNG, WEBP).")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Deskew — detect rotation angle and correct it
    gray = _deskew(gray)

    # Enhance contrast using CLAHE (good for faded receipts)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Encode back to PNG bytes
    success, buffer = cv2.imencode(".png", enhanced)
    if not success:
        raise RuntimeError("Failed to encode processed image as PNG.")

    return buffer.tobytes()


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Detect and correct skew angle in a grayscale image."""
    # Threshold to binary
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Find all non-zero points (text pixels)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return gray  # nothing to deskew

    # Get the minimum area bounding box angle
    angle = cv2.minAreaRect(coords)[-1]

    # Normalize angle to range (-45, 45)
    if angle < -45:
        angle = 90 + angle

    # Only correct if skew is significant (> 0.5 degrees)
    if abs(angle) < 0.5:
        return gray

    # Rotate the image to correct skew
    (h, w) = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated