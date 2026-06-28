"""Pydantic schemas for bill types."""

import re
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class BillType(StrEnum):
    hospital = "hospital_bill"
    restaurant = "restaurant_receipt"
    invoice = "invoice"


def clean_number(value) -> float:
    """Convert OCR/model currency strings into floats without raising."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value)
    match = re.search(r"-?\d+(?:[,\s]\d{2,3})*(?:\.\d+)?|-?\d+(?:\.\d+)?", text)
    if not match:
        return 0.0
    return float(match.group(0).replace(",", "").replace(" ", ""))


class LineItem(BaseModel):
    description: str = "Unknown item"
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0

    @field_validator("unit_price", "total", "quantity", mode="before")
    @classmethod
    def clean_number_field(cls, value):
        return clean_number(value)


class HospitalBill(BaseModel):
    type: BillType = BillType.hospital
    patient_name: str | None = None
    patient_id: str | None = None
    date_of_service: str | None = None
    hospital_name: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = None
    insurance_adjustment: float | None = None
    tax: float | None = None
    total_due: float = 0.0
    currency: str = "INR"

    @field_validator(
        "total_due",
        "subtotal",
        "tax",
        "insurance_adjustment",
        mode="before",
    )
    @classmethod
    def clean_price(cls, value):
        return clean_number(value)


class RestaurantReceipt(BaseModel):
    type: BillType = BillType.restaurant
    vendor_name: str | None = None
    date: str | None = None
    time: str | None = None
    table_number: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = None
    tax: float | None = None
    tip: float | None = None
    total: float = 0.0
    payment_method: str | None = None
    currency: str = "INR"

    @field_validator("total", "subtotal", "tax", "tip", mode="before")
    @classmethod
    def clean_price(cls, value):
        return clean_number(value)


class Invoice(BaseModel):
    type: BillType = BillType.invoice
    issuer_name: str | None = None
    receiver_name: str | None = None
    invoice_number: str | None = None
    date: str | None = None
    due_date: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = None
    tax: float | None = None
    total: float = 0.0
    currency: str = "INR"

    @field_validator("total", "subtotal", "tax", mode="before")
    @classmethod
    def clean_price(cls, value):
        return clean_number(value)


SCHEMA_MAP = {
    "hospital_bill": HospitalBill,
    "restaurant_receipt": RestaurantReceipt,
    "invoice": Invoice,
}

SCHEMA_JSON_MAP = {
    "hospital_bill": HospitalBill.model_json_schema(),
    "restaurant_receipt": RestaurantReceipt.model_json_schema(),
    "invoice": Invoice.model_json_schema(),
}
