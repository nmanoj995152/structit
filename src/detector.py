"""Detect bill type from OCR text and VLM description."""

BILL_TYPES = ["hospital_bill", "restaurant_receipt", "invoice"]

# Keywords that strongly indicate each bill type
HOSPITAL_KEYWORDS = [
    "patient", "diagnosis", "doctor", "physician", "ward",
    "discharge", "admission", "hospital", "clinic", "prescription",
    "medicine", "surgery", "consultation", "lab", "pathology",
]

RESTAURANT_KEYWORDS = [
    "table", "cover charge", "waiter", "restaurant", "cafe",
    "dine", "order", "menu", "food", "beverage", "tip",
    "gst on food", "swiggy", "zomato", "hotel bill",
]


def detect_bill_type(ocr_text: str, vlm_description: str) -> str:
    """
    Classify bill into one of: hospital_bill, restaurant_receipt, invoice.
    Uses keyword scoring on combined OCR + VLM text.
    Default: invoice (most generic).
    """
    combined = (ocr_text + " " + vlm_description).lower()

    hospital_score = sum(1 for kw in HOSPITAL_KEYWORDS if kw in combined)
    restaurant_score = sum(1 for kw in RESTAURANT_KEYWORDS if kw in combined)

    if hospital_score == 0 and restaurant_score == 0:
        return "invoice"

    if hospital_score >= restaurant_score:
        return "hospital_bill"

    return "restaurant_receipt"