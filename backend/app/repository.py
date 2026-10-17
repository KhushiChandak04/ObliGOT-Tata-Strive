"""Firestore repository with an explicit in-memory demo fallback.

Firestore is the intended persistent store. The fallback is for local UI development
only and resets on process restart. No SQLite database is used.
"""
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app.config import settings
from app.demo_data import PARTNERS, ACTIONS, FOLLOWUPS

_COLLECTIONS = {
    "partners": PARTNERS,
    "actions": ACTIONS,
    "followups": FOLLOWUPS,
    "agreements": {},
    "projects": {},
    "finance": {},
    "reports": {},
}
_firestore_client = None
_firestore_attempted = False

def _get_firestore():
    global _firestore_client, _firestore_attempted
    if _firestore_attempted:
        return _firestore_client
    _firestore_attempted = True
    try:
        import firebase_admin
        from firebase_admin import firestore
        if not firebase_admin._apps:
            options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
            firebase_admin.initialize_app(options=options)
        _firestore_client = firestore.client()
    except Exception:
        _firestore_client = None
    return _firestore_client

def firestore_enabled() -> bool:
    return _get_firestore() is not None

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
        docs = db.collection(collection).stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    return [_serialize(v) for v in _COLLECTIONS[collection].values()]

def get_record(collection: str, record_id: str):
    db = _get_firestore()
    if db is not None:
        doc = db.collection(collection).document(record_id).get()
        return ({"id": doc.id, **doc.to_dict()} if doc.exists else None)
    record = _COLLECTIONS[collection].get(record_id)
    return _serialize(record) if record is not None else None

def put_record(collection: str, data: dict, record_id: str | None = None) -> dict:
    record_id = record_id or f"{collection[:-1] if collection.endswith('s') else collection}-{uuid4().hex[:12]}"
    payload = _serialize(data)
    payload["id"] = record_id
    db = _get_firestore()
    if db is not None:
        db.collection(collection).document(record_id).set(payload)
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
        ref = db.collection(collection).document(record_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True
    return _COLLECTIONS[collection].pop(record_id, None) is not None
