# GitLab Issues — PixStruct

Open GitLab → Issues → New Issue and create each one below.

---

## Issue #1
**Title:** `feat: image pre-processing pipeline`
**Assignee:** You
**Estimate:** 45 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:ocr`

**Description:**
- [ ] Accept JPG, PNG, WEBP up to 20MB
- [ ] Convert to grayscale
- [ ] Deskew using OpenCV
- [ ] Normalize contrast with CLAHE
- [ ] Output normalized PNG bytes for pipeline
- [ ] Unit test: output is valid PNG with correct dimensions

---

## Issue #2
**Title:** `feat: Tesseract OCR wrapper`
**Assignee:** You
**Estimate:** 30 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:ocr`

**Description:**
- [ ] Run Tesseract with `--oem 3 --psm 6`
- [ ] Return raw text + per-word confidence scores
- [ ] Compute overall confidence (mean word confidence)
- [ ] Flag low-confidence results (< 60%) for VLM-only fallback
- [ ] Unit test: extract known text from sample receipt fixture

---

## Issue #3
**Title:** `feat: Moondream2 VLM loader and inference`
**Assignee:** You
**Estimate:** 60 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:vlm`

**Description:**
- [ ] Load `moondream2-Q4_K_M.gguf` from `~/.pixstruct/models/`
- [ ] Run CPU inference with `n_threads = os.cpu_count() - 1`
- [ ] Hard timeout 60s — capture partial output if hit
- [ ] Return natural language bill layout description
- [ ] Log inference duration to `processing_log`
- [ ] Unit test: model loads, returns non-empty string for fixture image

---

## Issue #4
**Title:** `feat: bill type detection`
**Assignee:** You
**Estimate:** 30 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:vlm`

**Description:**
- [ ] Classify into: `hospital_bill`, `restaurant_receipt`, `invoice`
- [ ] Use keyword heuristics from OCR text + VLM description
- [ ] Default to `invoice` if ambiguous
- [ ] Unit test: correct classification on 3 fixture images

---

## Issue #5
**Title:** `feat: Phi-3 Mini SLM integration`
**Assignee:** Viplav
**Estimate:** 60 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:slm`

**Description:**
- [ ] Load `Phi-3-mini-4k-instruct-Q4_K_M.gguf` from `~/.pixstruct/models/`
- [ ] Set `n_ctx=2048`, CPU threads = `os.cpu_count() - 1`
- [ ] Return raw string output
- [ ] Log inference duration to `processing_log`
- [ ] Unit test: model loads and produces output for sample prompt

---

## Issue #6
**Title:** `feat: extraction prompt and retry logic`
**Assignee:** Viplav
**Estimate:** 45 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:slm`

**Description:**
- [ ] System prompt enforces JSON-only output (no markdown)
- [ ] Prompt includes correct schema per bill type
- [ ] On `json.JSONDecodeError`: retry up to 2x with error feedback in prompt
- [ ] After 3 failures: return `status=failed`, store raw output
- [ ] Unit test: given sample OCR text, output is valid parseable JSON

---

## Issue #7
**Title:** `feat: Pydantic validation and field normalization`
**Assignee:** Viplav
**Estimate:** 30 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:validation`

**Description:**
- [ ] `HospitalBill` and `RestaurantReceipt` Pydantic v2 models
- [ ] Strip ₹ symbols and commas from price fields, cast to `float`
- [ ] Normalize date to `YYYY-MM-DD`, fallback to today
- [ ] Default `currency = "INR"` if not detected
- [ ] Mark `status=partial` if required fields are null
- [ ] Unit test: malformed JSON handled without crash

---

## Issue #8
**Title:** `feat: SQLite schema and database layer`
**Assignee:** You
**Estimate:** 30 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:storage`

**Description:**
- [ ] Tables: `bills`, `line_items`, `processing_log`
- [ ] DB file at `~/.pixstruct/data.db` created on first run
- [ ] `insert_bill(structured: dict) -> int`
- [ ] `get_bill(bill_id: int) -> dict`
- [ ] `list_bills(limit=50) -> list`
- [ ] Unit test: insert + retrieve round-trip preserves all fields

---

## Issue #9
**Title:** `feat: FastAPI backend and /extract endpoint`
**Assignee:** Viplav
**Estimate:** 30 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:api`

**Description:**
- [ ] `POST /extract` — image upload → structured JSON + bill_id
- [ ] `GET /bills` — list all bills
- [ ] `GET /bills/{id}` — full bill record
- [ ] `GET /bills/{id}/export` — download JSON file
- [ ] Proper 422 / 500 error responses

---

## Issue #10
**Title:** `feat: HTMX frontend and PWA service worker`
**Assignee:** Viplav
**Estimate:** 45 min
**Due:** Phase 2 (lunch)
**Labels:** `phase:2`, `component:frontend`

**Description:**
- [ ] Drag-and-drop image upload
- [ ] Progress indicator with stage labels: OCR → VLM → SLM → Saved
- [ ] Card view per bill: vendor, date, total, line items
- [ ] JSON preview tab per bill
- [ ] Download JSON button
- [ ] Service worker caches static assets
- [ ] Works fully with network disabled in browser

---

## Issue #11
**Title:** `chore: CI pipeline and pre-commit hooks (10+ real checks)`
**Assignee:** You
**Estimate:** 60 min
**Due:** Phase 3 (3 PM)
**Labels:** `phase:3`, `component:ci`

**Description:**
All checks must be REAL — no stubs, no `exit 0`.

- [ ] 1. `ruff check` — linting
- [ ] 2. `ruff format --check` — formatting
- [ ] 3. `mypy` — static type checking
- [ ] 4. `pytest` — all unit tests pass
- [ ] 5. `pytest --cov` — coverage report (fail if < 60%)
- [ ] 6. `bandit -r src/` — security scan
- [ ] 7. `pip-audit` — dependency vulnerability scan
- [ ] 8. Semantic commit message check
- [ ] 9. `pyproject.toml` validity check
- [ ] 10. Offline integration test (extraction with network blocked)
- [ ] 11. JSON schema validation on sample output
- [ ] 12. `trivy fs .` — filesystem security scan

Pre-commit hooks:
- [ ] `ruff` on staged files
- [ ] `mypy` on staged files
- [ ] Trailing whitespace + end-of-file fixes
- [ ] Conventional commit message check

---

## Issue #12
**Title:** `chore: integration test and demo prep`
**Assignee:** Both (You + Viplav)
**Estimate:** 30 min
**Due:** Phase 3 (3 PM)
**Labels:** `phase:3`

**Description:**
- [ ] Run full pipeline on 3 real images: 1 hospital bill, 1 restaurant receipt, 1 invoice
- [ ] All 3 produce valid JSON records in SQLite
- [ ] App works with Wi-Fi disabled (browser network tab → offline)
- [ ] Record end-to-end processing time for each
- [ ] Write demo script: what to show, in what order