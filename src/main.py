"""FastAPI application: routes and server entry point."""

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.database import get_bill, init_db, list_bills
from src.pipeline import process_bill

app = FastAPI(title="PixStruct", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Upload a bill file and extract structured data."""
    allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=422,
            detail="Only JPG, PNG, WEBP, and PDF files are accepted.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="File too large. Max 20MB.")

    try:
        result = process_bill(
            file_bytes,
            image_path=file.filename or "",
            content_type=file.content_type or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {exc}",
        ) from exc

    return JSONResponse(content=result)


@app.get("/health")
async def health():
    """Deployment health check."""
    return {"status": "ok", "offline_first": True}


@app.get("/bills")
async def bills():
    """List all processed bills."""
    return list_bills(limit=50)


@app.get("/bills/{bill_id}")
async def bill_detail(bill_id: int):
    """Get a full bill record with line items."""
    bill = get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")
    return bill


@app.get("/bills/{bill_id}/export")
async def export_bill(bill_id: int):
    """Download bill as a JSON file."""
    bill = get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")

    export_path = Path(tempfile.gettempdir()) / f"pixstruct_bill_{bill_id}.json"
    export_path.write_text(json.dumps(bill, indent=2), encoding="utf-8")
    return FileResponse(
        path=str(export_path),
        filename=f"bill_{bill_id}.json",
        media_type="application/json",
    )


def serve() -> None:
    """Run the local web app."""
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000)
