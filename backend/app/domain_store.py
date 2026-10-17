import json
import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

DB_PATH = Path(os.getenv("OBLIGOT_DB_PATH", str(Path(__file__).resolve().parents[1] / "obligot.db")))
ENTITY_TYPES = {"agreements", "projects", "finance-records", "reports"}

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS domain_records (
            id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, payload TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_domain_type ON domain_records(entity_type)")

def list_records(entity_type: str) -> list[dict[str, Any]]:
    if entity_type not in ENTITY_TYPES:
        raise ValueError("Unsupported entity type")
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM domain_records WHERE entity_type=? ORDER BY created_at DESC", (entity_type,)).fetchall()
    return [{"id": r["id"], **json.loads(r["payload"]), "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]

def get_record(entity_type: str, record_id: str):
    if entity_type not in ENTITY_TYPES:
        raise ValueError("Unsupported entity type")
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM domain_records WHERE entity_type=? AND id=?", (entity_type, record_id)).fetchone()
    return None if row is None else {"id": row["id"], **json.loads(row["payload"]), "created_at": row["created_at"], "updated_at": row["updated_at"]}

def create_record(entity_type: str, payload: dict[str, Any]):
    if entity_type not in ENTITY_TYPES:
        raise ValueError("Unsupported entity type")
    init_db()
    now = date.today().isoformat()
    record_id = f"{entity_type.rstrip('s')}-{uuid4().hex[:10]}"
    with connect() as conn:
        conn.execute("INSERT INTO domain_records VALUES (?, ?, ?, ?, ?)", (record_id, entity_type, json.dumps(payload, default=str), now, now))
    return get_record(entity_type, record_id)

def update_record(entity_type: str, record_id: str, changes: dict[str, Any]):
    old = get_record(entity_type, record_id)
    if old is None:
        return None
    merged = {k: v for k, v in old.items() if k not in {"id", "created_at", "updated_at"}}
    merged.update({k: v for k, v in changes.items() if v is not None})
    now = date.today().isoformat()
    with connect() as conn:
        conn.execute("UPDATE domain_records SET payload=?, updated_at=? WHERE entity_type=? AND id=?", (json.dumps(merged, default=str), now, entity_type, record_id))
    return get_record(entity_type, record_id)

def delete_record(entity_type: str, record_id: str) -> bool:
    if entity_type not in ENTITY_TYPES:
        raise ValueError("Unsupported entity type")
    init_db()
    with connect() as conn:
        cur = conn.execute("DELETE FROM domain_records WHERE entity_type=? AND id=?", (entity_type, record_id))
    return cur.rowcount > 0
