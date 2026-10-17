"""Firestore repository with an explicit in-memory demo fallback.

Firestore is the intended persistent store. The fallback is for local UI development
only and resets on process restart. No SQLite database is used.
"""
import logging
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app.demo_data import ACTIONS, AGREEMENTS, FINANCE, FOLLOWUPS, MILESTONES, OPPORTUNITIES, PARTNERS, PROJECTS, REPORTS
from app.firebase_app import FirebaseUnavailable, get_firebase_app

logger = logging.getLogger("obligot.repository")

_COLLECTIONS = {
    "partners": PARTNERS,
    "actions": ACTIONS,
    "followups": FOLLOWUPS,
    "agreements": AGREEMENTS,
    "projects": PROJECTS,
    "finance": FINANCE,
    "reports": REPORTS,
    "opportunities": OPPORTUNITIES,
    "milestones": MILESTONES,
}
_firestore_client = None
_firestore_attempted = False

class DataStoreUnavailable(RuntimeError):
    """A Firestore operation failed (network, permissions, quota, or credentials)."""

def _get_firestore():
    global _firestore_client, _firestore_attempted
    if _firestore_attempted:
        return _firestore_client
    _firestore_attempted = True
    try:
        from firebase_admin import firestore
        _firestore_client = firestore.client(app=get_firebase_app())
    except (FirebaseUnavailable, ImportError) as exc:
        logger.warning("Firestore not configured (%s); using non-persistent in-memory demo data.", exc)
        _firestore_client = None
    except Exception as exc:
        logger.warning("Firestore client creation failed (%s); using non-persistent in-memory demo data.", type(exc).__name__)
        _firestore_client = None
    return _firestore_client

def firestore_enabled() -> bool:
    return _get_firestore() is not None

def _firestore_call(operation: str, collection: str, fn):
    try:
        return fn()
    except Exception as exc:
        raise DataStoreUnavailable(f"Firestore {operation} on '{collection}' failed: {type(exc).__name__}") from exc

def _serialize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, dict):
        value = {k: _serialize(v) for k, v in value.items()}
    elif isinstance(value, list):
        value = [_serialize(v) for v in value]
    elif isinstance(value, (date, datetime)):
        value = value.isoformat()
    return value

def list_records(collection: str) -> list[dict]:
    db = _get_firestore()
    if db is not None:
        return _firestore_call("list", collection, lambda: [{"id": doc.id, **doc.to_dict()} for doc in db.collection(collection).stream()])
    return [_serialize(v) for v in _COLLECTIONS[collection].values()]

def get_record(collection: str, record_id: str):
    db = _get_firestore()
    if db is not None:
        doc = _firestore_call("get", collection, lambda: db.collection(collection).document(record_id).get())
        return ({"id": doc.id, **doc.to_dict()} if doc.exists else None)
    record = _COLLECTIONS[collection].get(record_id)
    return _serialize(record) if record is not None else None

def put_record(collection: str, data: dict, record_id: str | None = None) -> dict:
    record_id = record_id or f"{collection[:-1] if collection.endswith('s') else collection}-{uuid4().hex[:12]}"
    payload = _serialize(data)
    payload["id"] = record_id
    db = _get_firestore()
    if db is not None:
        _firestore_call("write", collection, lambda: db.collection(collection).document(record_id).set(payload))
    else:
        _COLLECTIONS[collection][record_id] = payload
    return payload

def patch_record(collection: str, record_id: str, changes: dict) -> dict | None:
    current = get_record(collection, record_id)
    if current is None:
        return None
    current.update(_serialize({k: v for k, v in changes.items() if v is not None}))
    return put_record(collection, current, record_id)

def delete_record(collection: str, record_id: str) -> bool:
    db = _get_firestore()
    if db is not None:
        def _delete() -> bool:
            ref = db.collection(collection).document(record_id)
            if not ref.get().exists:
                return False
            ref.delete()
            return True
        return _firestore_call("delete", collection, _delete)
    return _COLLECTIONS[collection].pop(record_id, None) is not None
