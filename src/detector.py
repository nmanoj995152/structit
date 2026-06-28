"""Detect bill type from OCR text and optional visual description."""

import re

BILL_TYPES = ["hospital_bill", "restaurant_receipt", "invoice"]

HOSPITAL_KEYWORDS = [
    "patient",
    "diagnosis",
    "doctor",
    "physician",
    "ward",
    "discharge",
    "admission",
    "hospital",
    "clinic",
    "prescription",
    "medicine",
    "surgery",
    "consultation",
    "lab",
    "pathology",
]

RESTAURANT_KEYWORDS = [
    "table",
    "cover charge",
    "waiter",
    "restaurant",
    "cafe",
    "dine",
    "order",
    "menu",
    "food",
    "beverage",
    "tip",
    "gst on food",
    "swiggy",
    "zomato",
    "hotel bill",
]


def detect_bill_type(ocr_text: str, vlm_description: str) -> str:
    """
    Classify bill into one of: hospital_bill, restaurant_receipt, invoice.

    Uses word/phrase keyword scoring on combined OCR + VLM text. Default is
    invoice because it is the broadest schema.
    """
    combined = f"{ocr_text} {vlm_description}".lower()

    hospital_score = _score_keywords(combined, HOSPITAL_KEYWORDS)
    restaurant_score = _score_keywords(combined, RESTAURANT_KEYWORDS)

    if hospital_score == 0 and restaurant_score == 0:
        return "invoice"
    if hospital_score >= restaurant_score:
        return "hospital_bill"
    return "restaurant_receipt"


def _score_keywords(text: str, keywords: list[str]) -> int:
    score = 0
    for keyword in keywords:
        pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            score += 1
    return score
