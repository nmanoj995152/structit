"""Basic integration smoke tests."""

from src.detector import detect_bill_type
from src.extractor import extract_structured
from src.schemas import HospitalBill, LineItem, RestaurantReceipt


def test_detect_hospital():
    ocr = "patient name John diagnosis fever doctor consultation"
    assert detect_bill_type(ocr, "") == "hospital_bill"


def test_detect_restaurant():
    ocr = "table 4 food beverage tip total restaurant"
    assert detect_bill_type(ocr, "") == "restaurant_receipt"


def test_detect_invoice_fallback():
    assert detect_bill_type("nothing useful here", "") == "invoice"


def test_detector_does_not_match_keyword_inside_words():
    assert detect_bill_type("", "VLM unavailable; using OCR only.") == "invoice"


def test_rule_based_extraction_without_local_model():
    ocr = "\n".join(
        [
            "Cafe Local",
            "Date: 28/06/2026",
            "Paneer Tikka 2 x 180 360",
            "GST 18",
            "Total INR 378",
        ]
    )
    structured, status = extract_structured(ocr, "", "restaurant_receipt")
    assert status == "success"
    assert structured["vendor_name"] == "Cafe Local"
    assert structured["date"] == "2026-06-28"
    assert structured["total"] == 378.0


def test_hospital_schema_price_cleaning():
    bill = HospitalBill(total_due="\u20b91,250.00", tax="\u20b950")
    assert bill.total_due == 1250.0
    assert bill.tax == 50.0


def test_restaurant_schema_defaults():
    receipt = RestaurantReceipt(total="500")
    assert receipt.total == 500.0
    assert receipt.currency == "INR"
    assert receipt.line_items == []


def test_line_item_cleaning():
    item = LineItem(
        description="Paneer Tikka",
        unit_price="\u20b9180",
        total="\u20b9360",
        quantity="2",
    )
    assert item.unit_price == 180.0
    assert item.total == 360.0
