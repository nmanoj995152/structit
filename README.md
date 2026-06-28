# StructIt

StructIt is an offline-first, CPU-only document intelligence app that converts
unstructured files into structured JSON and stores the results locally in
SQLite.

## Features

- Upload PDF, DOCX, TXT, JPG, PNG, and WEBP files.
- Extract text locally:
  - PDF: PyMuPDF
  - DOCX: python-docx
  - TXT: native Python decoding
  - Images: Tesseract OCR
- Normalize text before structuring.
- Generate structured JSON with local runtimes when configured:
  - llama.cpp via `llama-cpp-python`
  - Ollama with locally pulled models
  - deterministic local fallback when no model is configured
- Store raw text and structured JSON in local SQLite.
- Streamlit UI with Home, Upload, Results, History, and Settings pages.
- Export results as JSON or CSV.
- No OpenAI, Anthropic, or cloud inference.

## Output Schema

```json
{
  "title": "",
  "people": [],
  "organizations": [],
  "emails": [],
  "phones": [],
  "dates": [],
  "summary": "",
  "keywords": []
}
```

## Requirements

- Python 3.11+
- Tesseract installed locally for image OCR
- Optional local model runtime:
  - llama.cpp GGUF model in `~/.pixstruct/models/`
  - Ollama with a locally available model

The project includes `models/tessdata/eng.traineddata` so English OCR language
data is available offline from the repo.

## Install

```powershell
cd C:\Users\Admin\structit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run Streamlit

```powershell
cd C:\Users\Admin\structit
streamlit run src\streamlit_app.py
```

## Run FastAPI

```powershell
cd C:\Users\Admin\structit
python -m uvicorn src.main:app --host 127.0.0.1 --port 8001
```

If port `8001` is already in use, choose another port:

```powershell
python -m uvicorn src.main:app --host 127.0.0.1 --port 8002
```

## Local Model Settings

StructIt never calls cloud APIs. Runtime selection is local:

```text
STRUCTIT_LLM_RUNTIME=none
STRUCTIT_LLM_RUNTIME=llama.cpp
STRUCTIT_LLM_RUNTIME=ollama
STRUCTIT_OLLAMA_MODEL=llama3.2:3b
```

Use `none` for deterministic local extraction without an LLM.

## Data Storage

SQLite is stored at:

```text
~/.pixstruct/data.db
```

Tables:

- `documents`: generic document extraction records
- `bills`: legacy bill/receipt extraction records
- `line_items`: legacy bill line items
- `processing_log`: stage timing and errors

## Validation

```powershell
python -m ruff check src tests
python -m black --check src tests
python -m isort --check-only src tests
python -m mypy src
python -m pytest --cov=src --cov-report=term-missing
python -m bandit -r src
```

## Offline Rules

- Do not add OpenAI, Anthropic, or hosted model SDKs.
- Do not send document contents over the network.
- Keep inference CPU-only.
- Prefer local FOSS runtimes and quantized models.

## License

GPL-3.0-or-later.
