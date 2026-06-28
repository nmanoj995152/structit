"""Structured extraction with local SLM and deterministic fallback."""

from __future__ import annotations

import json
import re
from datetime import datetime

from src.schemas import SCHEMA_JSON_MAP, SCHEMA_MAP, clean_number
from src.slm import run_slm

SYSTEM_PROMPT = """You are a data extraction assistant for bills and receipts.
Your job is to extract structured information and return it as valid JSON.
RULES:
- Respond ONLY with a JSON object. No explanation. No markdown. No backticks.
- If a field is missing from the bill, use null.
- All prices must be plain numbers with no currency symbols or commas.
- Dates must be in YYYY-MM-DD format.
- line_items must always be an array, even if empty.
- Do not invent data that is not present in the bill."""

DATE_PATTERNS = [
    r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
    r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
    r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b",
]
CURRENCY_PATTERN = r"(?:rs\.?|inr|\u20b9|\$)?"
AMOUNT_PATTERN = r"([0-9][0-9,\s]*(?:\.\d+)?)"
TOTAL_PATTERNS = [
    (
        r"(?:grand\s+total|amount\s+due|balance\s+due|net\s+amount|"
        rf"total\s+due|total)\s*[:\-]?\s*{CURRENCY_PATTERN}\s*"
        rf"{AMOUNT_PATTERN}"
    ),
    rf"(?:rs\.?|inr|\u20b9|\$)\s*{AMOUNT_PATTERN}",
]
SUBTOTAL_PATTERN = (
    rf"(?:subtotal|sub\s+total|taxable\s+amount)\s*[:\-]?\s*"
    rf"{CURRENCY_PATTERN}\s*{AMOUNT_PATTERN}"
)
TAX_PATTERN = (
    rf"(?:tax|gst|cgst|sgst|vat)\s*[:\-]?\s*" rf"{CURRENCY_PATTERN}\s*{AMOUNT_PATTERN}"
)
TIP_PATTERN = rf"\btip\s*[:\-]?\s*{CURRENCY_PATTERN}\s*{AMOUNT_PATTERN}"
TABLE_PATTERN = r"\btable\s*(?:no\.?|#)?\s*([A-Za-z0-9-]+)"
LINE_SKIP_PATTERN = r"\b(total|subtotal|tax|gst|date|invoice|bill no|amount due)\b"
LINE_AMOUNT_PATTERN = rf"{CURRENCY_PATTERN}\s*([0-9][0-9,\s]*(?:\.\d{{1,2}})?)\s*$"


def extract_structured(
    ocr_text: str,
    vlm_description: str,
    bill_type: str,
) -> tuple[dict, str]:
    """
    Extract structured data from OCR + optional VLM output.

    A local SLM is attempted first. If it is unavailable, slow, or returns
    invalid JSON, the deterministic fallback still produces schema-aligned JSON
    from OCR text so the app remains useful offline and on low-power CPUs.
    """
    if not ocr_text.strip() and not vlm_description.strip():
        return _empty_structured(bill_type, "No readable text found."), "failed"

    slm_result = _extract_with_slm(ocr_text, vlm_description, bill_type)
    if slm_result is not None:
        return slm_result

    return _extract_with_rules(ocr_text, vlm_description, bill_type)


def _extract_with_slm(
    ocr_text: str,
    vlm_description: str,
    bill_type: str,
) -> tuple[dict, str] | None:
    schema = SCHEMA_JSON_MAP.get(bill_type, SCHEMA_JSON_MAP["invoice"])
    model_class = SCHEMA_MAP.get(bill_type, SCHEMA_MAP["invoice"])

    user_prompt = f"""Bill type: {bill_type}

OCR Text:
{ocr_text[:1800]}

Visual Description:
{vlm_description[:500]}

Extract all fields from this bill according to this JSON schema:
{json.dumps(schema, indent=2)}"""

    last_error = ""
    for attempt in range(3):
        retry_note = ""
        if attempt > 0:
            retry_note = (
                f"\n\nPrevious attempt failed with: {last_error}\n" "Return fixed JSON."
            )

        try:
            raw_output = run_slm(user_prompt + retry_note, SYSTEM_PROMPT)
            parsed = json.loads(_clean_json_output(raw_output))
            validated = model_class(**parsed)
            structured = validated.model_dump(mode="json")
            return structured, _status_for(structured)
        except FileNotFoundError:
            return None
        except RuntimeError as exc:
            if "llama-cpp-python not available" in str(exc):
                return None
            last_error = str(exc)
        except json.JSONDecodeError as exc:
            last_error = f"JSON parse error: {exc}"
        except Exception as exc:
            last_error = f"Validation error: {exc}"

    return None


def _extract_with_rules(
    ocr_text: str,
    vlm_description: str,
    bill_type: str,
) -> tuple[dict, str]:
    text = _normalize_text(f"{ocr_text}\n{vlm_description}")
    line_items = _extract_line_items(text)
    subtotal = _first_amount(SUBTOTAL_PATTERN, text)
    common = {
        "line_items": line_items,
        "subtotal": subtotal,
        "tax": _first_amount(TAX_PATTERN, text),
        "currency": _detect_currency(text),
    }
    total = _extract_total(text) or subtotal or _sum_items(line_items)
    date = _extract_date(text)
    vendor = _extract_vendor(text)

    if bill_type == "hospital_bill":
        payload = {
            "hospital_name": vendor,
            "date_of_service": date,
            "total_due": total,
            **common,
        }
    elif bill_type == "restaurant_receipt":
        payload = {
            "vendor_name": vendor,
            "date": date,
            "table_number": _extract_label(text, TABLE_PATTERN),
            "tip": _first_amount(TIP_PATTERN, text),
            "total": total,
            **common,
        }
    else:
        payload = {
            "issuer_name": vendor,
            "invoice_number": _extract_label(
                text,
                r"\b(?:invoice|inv|bill)\s*(?:no\.?|number|#)?\s*[:\-]?"
                r"\s*([A-Za-z0-9-/]+)",
            ),
            "date": date,
            "due_date": _extract_label(
                text,
                r"\bdue\s+date\s*[:\-]?\s*([A-Za-z0-9,\-/ ]{6,20})",
            ),
            "total": total,
            **common,
        }

    model_class = SCHEMA_MAP.get(bill_type, SCHEMA_MAP["invoice"])
    structured = model_class(**payload).model_dump(mode="json")
    status = _status_for(structured)
    if not ocr_text.strip():
        status = "failed"
        structured["error"] = "No readable OCR text found."
    elif status == "failed":
        status = "partial"
        structured["warning"] = (
            "I could read some text, but not enough to fill every field. "
            "Open JSON to review what was found, or try a clearer image."
        )
        structured["raw_ocr_excerpt"] = ocr_text[:500]
    elif status == "partial":
        structured["warning"] = (
            "Processed locally. Some fields may need review because the bill "
            "text was not clear enough."
        )
    return structured, status


def _clean_json_output(raw_output: str) -> str:
    clean = raw_output.strip()
    clean = (
        clean.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    )
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end >= start:
        return clean[start : end + 1]
    return clean


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r", "\n"))


def _extract_total(text: str) -> float:
    amounts: list[float] = []
    lower = text.lower()
    for pattern in TOTAL_PATTERNS:
        for match in re.finditer(pattern, lower, flags=re.IGNORECASE):
            amounts.append(clean_number(match.group(1)))
    return max(amounts) if amounts else 0.0


def _first_amount(pattern: str, text: str) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return clean_number(match.group(1)) if match else 0.0


def _sum_items(items: list[dict]) -> float:
    return round(sum(clean_number(item.get("total")) for item in items), 2)


def _extract_line_items(text: str) -> list[dict]:
    items: list[dict] = []
    for line in text.splitlines():
        clean_line = line.strip(" -:\t")
        if len(clean_line) < 4:
            continue
        if re.search(LINE_SKIP_PATTERN, clean_line, re.I):
            continue

        amount_matches = list(re.finditer(LINE_AMOUNT_PATTERN, clean_line, re.I))
        if not amount_matches:
            continue

        amount_match = amount_matches[-1]
        amount = clean_number(amount_match.group(1))
        description = clean_line[: amount_match.start()].strip(" -:\t")
        if not description or len(description) > 80:
            continue

        quantity = 1.0
        quantity_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(?:x|qty|pcs?)\b",
            description,
            re.I,
        )
        if quantity_match:
            quantity = clean_number(quantity_match.group(1))

        items.append(
            {
                "description": description,
                "quantity": quantity,
                "unit_price": round(amount / quantity, 2) if quantity else amount,
                "total": amount,
            }
        )

    return items[:40]


def _extract_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).strip()
        for fmt in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d-%m-%y",
            "%d/%m/%y",
            "%d %b %Y",
            "%d %B %Y",
            "%d %b %y",
            "%d %B %y",
        ):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                pass
    return None


def _extract_vendor(text: str) -> str | None:
    joined = " ".join(line.strip() for line in text.splitlines()[:4] if line.strip())
    before_label = re.match(
        r"^(.{3,80}?)\s+\b(?:date|invoice|receipt|bill|total)\b",
        joined,
        flags=re.I,
    )
    if before_label:
        candidate = _clean_vendor(before_label.group(1))
        if candidate:
            return candidate

    skip = re.compile(
        r"\b(invoice|receipt|bill|tax|gst|date|phone|mobile|email)\b",
        re.I,
    )
    for line in text.splitlines()[:8]:
        candidate = _clean_vendor(line)
        if 2 < len(candidate) <= 80 and not skip.search(candidate):
            return candidate
    return None


def _clean_vendor(value: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9 &.,'-]", " ", value).strip(" -,.")
    return re.sub(r"\s+", " ", candidate)


def _extract_label(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip(" -,:") if match else None


def _detect_currency(text: str) -> str:
    lower = text.lower()
    if "\u20b9" in text or "inr" in lower or "rs" in lower:
        return "INR"
    if "$" in text or "usd" in lower:
        return "USD"
    return "INR"


def _status_for(structured: dict) -> str:
    total = structured.get("total_due") or structured.get("total")
    vendor = (
        structured.get("hospital_name")
        or structured.get("vendor_name")
        or structured.get("issuer_name")
    )
    date = structured.get("date_of_service") or structured.get("date")
    if total and vendor:
        return "success"
    if total or vendor or date or structured.get("line_items"):
        return "partial"
    return "failed"


def _empty_structured(bill_type: str, error: str) -> dict:
    model_class = SCHEMA_MAP.get(bill_type, SCHEMA_MAP["invoice"])
    structured = model_class().model_dump(mode="json")
    structured["error"] = error
    return structured
