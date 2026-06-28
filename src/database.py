"""SQLite database layer for PixStruct."""

import json
import sqlite3
from pathlib import Path

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
            input_hash  TEXT,
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

        CREATE TABLE IF NOT EXISTS documents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            filename        TEXT NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            input_hash      TEXT,
            source_type     TEXT,
            status          TEXT DEFAULT 'success',
            raw_text        TEXT,
            structured_json TEXT NOT NULL,
            logs            TEXT
        );
    """)
    _ensure_column(conn, "bills", "input_hash", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bills_input_hash ON bills(input_hash)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_input_hash ON documents(input_hash)"
    )
    conn.commit()
    conn.close()


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {table_name} " f"ADD COLUMN {column_name} {column_definition}"
        )


def insert_bill(
    bill_type: str,
    structured: dict,
    raw_ocr: str = "",
    status: str = "success",
    image_path: str = "",
    input_hash: str = "",
) -> int:
    """Insert a bill record. Returns new bill ID."""
    conn = _get_connection()

    # Pull top-level fields for quick querying
    total = structured.get("total_due") or structured.get("total")
    vendor = structured.get("hospital_name") or structured.get("vendor_name")
    bill_date = structured.get("date_of_service") or structured.get("date")

    cursor = conn.execute(
        """INSERT INTO bills
           (bill_type, status, image_path, input_hash, raw_ocr,
            structured, total, vendor, bill_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            bill_type,
            status,
            image_path,
            input_hash,
            raw_ocr,
            json.dumps(structured),
            total,
            vendor,
            bill_date,
        ),
    )
    bill_id = cursor.lastrowid
    if bill_id is None:
        conn.close()
        raise RuntimeError("SQLite did not return a bill id.")

    # Insert line items into their own table
    for item in structured.get("line_items", []):
        conn.execute(
            """INSERT INTO line_items
               (bill_id, description, quantity, unit_price, total)
               VALUES (?, ?, ?, ?, ?)""",
            (
                bill_id,
                item.get("description"),
                item.get("quantity", 1),
                item.get("unit_price"),
                item.get("total"),
            ),
        )

    conn.commit()
    conn.close()
    return bill_id


def get_bill_by_hash(input_hash: str) -> dict | None:
    """Fetch the newest bill record for the same input hash."""
    if not input_hash:
        return None

    conn = _get_connection()
    row = conn.execute(
        "SELECT id FROM bills WHERE input_hash = ? ORDER BY created_at DESC LIMIT 1",
        (input_hash,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return get_bill(int(row["id"]))


def get_bill(bill_id: int) -> dict | None:
    """Fetch a full bill record with its line items."""
    conn = _get_connection()

    row = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()

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


def insert_document(
    filename: str,
    raw_text: str,
    structured_json: dict,
    input_hash: str = "",
    source_type: str = "",
    status: str = "success",
    logs: list[str] | None = None,
) -> int:
    """Insert a generic document extraction record."""
    conn = _get_connection()
    cursor = conn.execute(
        """INSERT INTO documents
           (filename, input_hash, source_type, status, raw_text, structured_json, logs)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            filename,
            input_hash,
            source_type,
            status,
            raw_text,
            json.dumps(structured_json),
            json.dumps(logs or []),
        ),
    )
    document_id = cursor.lastrowid
    if document_id is None:
        conn.close()
        raise RuntimeError("SQLite did not return a document id.")
    conn.commit()
    conn.close()
    return int(document_id)


def get_document(document_id: int) -> dict | None:
    """Fetch one generic document record."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None

    document = dict(row)
    document["structured_json"] = json.loads(document["structured_json"])
    document["logs"] = json.loads(document["logs"] or "[]")
    return document


def get_document_by_hash(input_hash: str) -> dict | None:
    """Fetch the newest successful generic document record by input hash."""
    if not input_hash:
        return None
    conn = _get_connection()
    row = conn.execute(
        """SELECT id FROM documents
           WHERE input_hash = ? AND status = 'success'
           ORDER BY created_at DESC LIMIT 1""",
        (input_hash,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return get_document(int(row["id"]))


def list_documents(limit: int = 100) -> list[dict]:
    """Return recent generic document records."""
    conn = _get_connection()
    rows = conn.execute(
        """SELECT id, filename, created_at, source_type, status
           FROM documents ORDER BY created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


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
