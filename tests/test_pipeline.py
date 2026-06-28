"""Basic integration smoke tests."""

import pytest
from src.detector import detect_bill_type
from src.schemas import HospitalBill, RestaurantReceipt, LineItem


def test_detect_hospital():
    ocr = "patient name John diagnosis fever doctor consultation"
    assert detect_bill_type(ocr, "") == "hospital_bill"


def test_detect_restaurant():
    ocr = "table 4 food beverage tip total restaurant"
    assert detect_bill_type(ocr, "") == "restaurant_receipt"


def test_detect_invoice_fallback():
    assert detect_bill_type("nothing useful here", "") == "invoice"


def test_hospital_schema_price_cleaning():
    bill = HospitalBill(total_due="₹1,250.00", tax="₹50")
    assert bill.total_due == 1250.0
    assert bill.tax == 50.0


def test_restaurant_schema_defaults():
    receipt = RestaurantReceipt(total="500")
    assert receipt.total == 500.0
    assert receipt.currency == "INR"
    assert receipt.line_items == []


def test_line_item_cleaning():
    item = LineItem(description="Paneer Tikka", unit_price="₹180", total="₹360", quantity="2")
    assert item.unit_price == 180.0
    assert item.total == 360.0