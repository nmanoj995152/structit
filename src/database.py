"""SQLite database layer for PixStruct."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_DIR = Path.home() / ".pixstruct"
DB_PATH = DB_DIR / "data.db"


def _get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # return rows as dict-like objects
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bills (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            bill_type   TEXT NOT NULL,
            status      TEXT DEFAULT 'success',
            image_path  TEXT,
            raw_ocr     TEXT,
            structured  TEXT NOT NULL,
            total       REAL,
            vendor      TEXT,
            bill_date   TEXT
        );

        CREATE TABLE IF NOT EXISTS line_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id      INTEGER REFERENCES bills(id),
            description  TEXT,
            quantity     REAL DEFAULT 1.0,
            unit_price   REAL,
            total        REAL
        );

        CREATE TABLE IF NOT EXISTS processing_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id     INTEGER REFERENCES bills(id),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            stage       TEXT,
            duration_ms INTEGER,
            status      TEXT,
            error       TEXT
        );
    """)
    conn.commit()
    conn.close()


def insert_bill(
    bill_type: str,
    structured: dict,
    raw_ocr: str = "",
    status: str = "success",
    image_path: str = "",
) -> int:
    """Insert a bill record. Returns new bill ID."""
    conn = _get_connection()

    # Pull top-level fields for quick querying
    total = structured.get("total_due") or structured.get("total")
    vendor = structured.get("hospital_name") or structured.get("vendor_name")
    bill_date = structured.get("date_of_service") or structured.get("date")

    cursor = conn.execute(
        """INSERT INTO bills
           (bill_type, status, image_path, raw_ocr, structured, total, vendor, bill_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (bill_type, status, image_path, raw_ocr,
         json.dumps(structured), total, vendor, bill_date),
    )
    bill_id = cursor.lastrowid

    # Insert line items into their own table
    for item in structured.get("line_items", []):
        conn.execute(
            """INSERT INTO line_items (bill_id, description, quantity, unit_price, total)
               VALUES (?, ?, ?, ?, ?)""",
            (bill_id, item.get("description"), item.get("quantity", 1),
             item.get("unit_price"), item.get("total")),
        )

    conn.commit()
    conn.close()
    return bill_id


def get_bill(bill_id: int) -> dict | None:
    """Fetch a full bill record with its line items."""
    conn = _get_connection()

    row = conn.execute(
        "SELECT * FROM bills WHERE id = ?", (bill_id,)
    ).fetchone()

    if row is None:
        conn.close()
        return None

    bill = dict(row)
    bill["structured"] = json.loads(bill["structured"])

    items = conn.execute(
        "SELECT * FROM line_items WHERE bill_id = ?", (bill_id,)
    ).fetchall()
    bill["line_items"] = [dict(i) for i in items]

    conn.close()
    return bill


def list_bills(limit: int = 50) -> list[dict]:
    """Return most recent bills (summary only, no line items)."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, created_at, bill_type, status, vendor, total, bill_date "
        "FROM bills ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_stage(
    bill_id: int,
    stage: str,
    duration_ms: int,
    status: str = "success",
    error: str = "",
) -> None:
    """Log a processing stage result."""
    conn = _get_connection()
    conn.execute(
        """INSERT INTO processing_log (bill_id, stage, duration_ms, status, error)
           VALUES (?, ?, ?, ?, ?)""",
        (bill_id, stage, duration_ms, status, error),
    )
    conn.commit()
    conn.close()