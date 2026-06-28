# Work Division Plan — PixStruct

**Team:** You + Viplav
**Phase 1 deadline:** 10:00 AM
**Phase 2 deadline:** Lunch break
**Phase 3 deadline:** 3:00 PM

---

## Ownership

| Component | You | Viplav |
|-----------|-----|--------|
| Image pre-processing (OpenCV) | ✅ | — |
| Tesseract OCR integration | ✅ | — |
| Moondream2 VLM (llama.cpp) | ✅ | — |
| Bill type detection | ✅ | — |
| SQLite schema + DB layer | ✅ | — |
| GitLab CI + pre-commit hooks | ✅ | — |
| Phi-3 Mini SLM integration | — | ✅ |
| Extraction prompt engineering | — | ✅ |
| Pydantic validation + schemas | — | ✅ |
| FastAPI routes + API layer | — | ✅ |
| HTMX frontend + PWA | — | ✅ |
| JSON export | — | ✅ |
| Integration + demo dry-run | ✅ Both | ✅ Both |

---

## Phase 1 — Before 10 AM

| Task | Owner | Time |
|------|-------|------|
| Create GitLab repo, push all Phase 1 files | You | 20 min |
| Create all 12 issues in GitLab UI | Viplav | 20 min |
| Set up project folder structure + pyproject.toml | You | 15 min |
| Align on integration contracts (see below) | Both | 10 min |

---

## Phase 2 — Before Lunch

| Task | Owner | Est. | Issue |
|------|-------|------|-------|
| Image pre-processing module | You | 45 min | #1 |
| Tesseract OCR wrapper | You | 30 min | #2 |
| Moondream2 loader + inference | You | 60 min | #3 |
| Bill type detection | You | 30 min | #4 |
| SQLite init + CRUD | You | 30 min | #8 |
| Phi-3 Mini loader + inference | Viplav | 60 min | #5 |
| Extraction prompt + retry logic | Viplav | 45 min | #6 |
| Pydantic models + validation | Viplav | 30 min | #7 |
| FastAPI app + endpoints | Viplav | 30 min | #9 |
| HTMX UI + PWA service worker | Viplav | 45 min | #10 |
| Wire everything end-to-end | Both | 30 min | #12 |

---

## Phase 3 — Before 3 PM

| Task | Owner | Est. | Issue |
|------|-------|------|-------|
| pre-commit config (ruff, mypy etc.) | You | 20 min | #11 |
| .gitlab-ci.yml (10+ real checks) | You | 40 min | #11 |
| CONTRIBUTING.md | Viplav | 10 min | — |
| CHANGELOG.md | Viplav | 10 min | — |
| Demo dry-run with Wi-Fi OFF | Both | 20 min | — |

---

## Integration Contracts

Agree on these before writing code — this is where your work connects.

### Contract 1 — You → Viplav (after OCR + VLM)
```python
def process_image(image_path: str) -> dict:
    return {
        "ocr_text": str,           # raw Tesseract output
        "vlm_description": str,    # Moondream2 layout description
        "ocr_confidence": float,   # 0.0 – 1.0
        "detected_type": str,      # "hospital_bill" | "restaurant_receipt" | "invoice"
    }
```

### Contract 2 — Viplav → You (after SLM + validation)
```python
def extract_structured(pipeline_result: dict) -> dict:
    return {
        "structured": dict,   # validated Pydantic model as dict
        "status": str,        # "success" | "partial" | "failed"
        "raw_json": str,      # raw SLM string before validation
    }
```

---

## Sync Rule
Check in with each other every **45 minutes**.
If blocked for more than **15 minutes** — swap tasks, don't wait.