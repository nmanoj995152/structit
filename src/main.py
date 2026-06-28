"""FastAPI application — routes and server entry point."""

import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from src.pipeline import process_bill
from src.database import init_db, get_bill, list_bills

app = FastAPI(title="PixStruct", version="0.1.0")

# Serve static files (frontend)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Upload a bill image and extract structured data."""
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=422, detail="Only JPG, PNG, WEBP images accepted.")

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="Image too large. Max 20MB.")

    try:
        result = process_bill(image_bytes, image_path=file.filename or "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    return JSONResponse(content=result)


@app.get("/bills")
async def bills():
    """List all processed bills (summary)."""
    return list_bills(limit=50)


@app.get("/bills/{bill_id}")
async def bill_detail(bill_id: int):
    """Get full bill record with line items."""
    bill = get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")
    return bill


@app.get("/bills/{bill_id}/export")
async def export_bill(bill_id: int):
    """Download bill as JSON file."""
    bill = get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")

    export_path = Path(f"/tmp/pixstruct_bill_{bill_id}.json")
    export_path.write_text(json.dumps(bill, indent=2))
    return FileResponse(
        path=str(export_path),
        filename=f"bill_{bill_id}.json",
        media_type="application/json",
    )