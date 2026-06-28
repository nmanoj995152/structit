"""Prompt engineering and JSON extraction with retry logic."""

import json
from src.slm import run_slm
from src.schemas import SCHEMA_MAP, SCHEMA_JSON_MAP

SYSTEM_PROMPT = """You are a data extraction assistant for bills and receipts.
Your job is to extract structured information and return it as valid JSON.
RULES:
- Respond ONLY with a JSON object. No explanation. No markdown. No backticks.
- If a field is missing from the bill, use null.
- All prices must be plain numbers — no ₹ or $ or commas.
- Dates must be in YYYY-MM-DD format.
- line_items must always be an array, even if empty.
- Do not invent data that is not present in the bill."""


def extract_structured(
    ocr_text: str,
    vlm_description: str,
    bill_type: str,
) -> tuple[dict, str]:
    """
    Extract structured data from OCR + VLM output using Phi-3 Mini.
    Returns (validated_dict, status) where status is 'success', 'partial', or 'failed'.
    Retries up to 2 times on JSON parse failure.
    """
    schema = SCHEMA_JSON_MAP.get(bill_type, SCHEMA_JSON_MAP["invoice"])
    model_class = SCHEMA_MAP.get(bill_type, SCHEMA_MAP["invoice"])

    user_prompt = f"""Bill type: {bill_type}

OCR Text:
{ocr_text[:1200]}

Visual Description:
{vlm_description[:400]}

Extract all fields from this bill according to this JSON schema:
{json.dumps(schema, indent=2)}"""

    last_error = ""
    for attempt in range(3):  # 1 initial + 2 retries
        # On retry, feed the error back into the prompt
        retry_note = ""
        if attempt > 0:
            retry_note = f"\n\nPrevious attempt failed with: {last_error}\nFix the JSON and try again."

        raw_output = run_slm(user_prompt + retry_note, SYSTEM_PROMPT)

        try:
            # Strip any accidental markdown fences just in case
            clean = raw_output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(clean)

            # Validate through Pydantic
            validated = model_class(**parsed)
            status = "success"

            # Mark as partial if key total field is zero/null
            total = validated.model_dump().get("total_due") or validated.model_dump().get("total")
            if not total:
                status = "partial"

            return validated.model_dump(), status

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
        except Exception as e:
            last_error = f"Validation error: {e}"

    # All retries exhausted
    return {"raw_output": raw_output, "error": last_error}, "failed"