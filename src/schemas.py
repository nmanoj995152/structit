"""Pydantic schemas for bill types."""

from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum
import re


class BillType(str, Enum):
    hospital = "hospital_bill"
    restaurant = "restaurant_receipt"
    invoice = "invoice"


class LineItem(BaseModel):
    description: str = "Unknown item"
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0

    @field_validator("unit_price", "total", "quantity", mode="before")
    @classmethod
    def clean_number(cls, v):
        """Strip currency symbols and commas, cast to float."""
        if isinstance(v, str):
            v = re.sub(r"[₹$,\s]", "", v)
            return float(v) if v else 0.0
        return float(v) if v is not None else 0.0


class HospitalBill(BaseModel):
    type: BillType = BillType.hospital
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    date_of_service: Optional[str] = None
    hospital_name: Optional[str] = None
    line_items: list[LineItem] = []
    subtotal: Optional[float] = None
    insurance_adjustment: Optional[float] = None
    tax: Optional[float] = None
    total_due: float = 0.0
    currency: str = "INR"

    @field_validator("total_due", "subtotal", "tax", "insurance_adjustment", mode="before")
    @classmethod
    def clean_price(cls, v):
        if isinstance(v, str):
            v = re.sub(r"[₹$,\s]", "", v)
            return float(v) if v else 0.0
        return float(v) if v is not None else 0.0


class RestaurantReceipt(BaseModel):
    type: BillType = BillType.restaurant
    vendor_name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    table_number: Optional[str] = None
    line_items: list[LineItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: float = 0.0
    payment_method: Optional[str] = None
    currency: str = "INR"

    @field_validator("total", "subtotal", "tax", "tip", mode="before")
    @classmethod
    def clean_price(cls, v):
        if isinstance(v, str):
            v = re.sub(r"[₹$,\s]", "", v)
            return float(v) if v else 0.0
        return float(v) if v is not None else 0.0


class Invoice(BaseModel):
    type: BillType = BillType.invoice
    issuer_name: Optional[str] = None
    receiver_name: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    line_items: list[LineItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float = 0.0
    currency: str = "INR"

    @field_validator("total", "subtotal", "tax", mode="before")
    @classmethod
    def clean_price(cls, v):
        if isinstance(v, str):
            v = re.sub(r"[₹$,\s]", "", v)
            return float(v) if v else 0.0
        return float(v) if v is not None else 0.0


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