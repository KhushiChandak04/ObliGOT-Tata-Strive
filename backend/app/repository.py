"""Firestore repository with an explicitly selected, process-local synthetic demo store."""
import copy
import logging
import threading
import time
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app.config import settings
from app.demo_data import ACTIONS, AGREEMENTS, FINANCE, FOLLOWUPS, MILESTONES, OPPORTUNITIES, PARTNERS, PROJECTS, REPORTS
from app.demo_dataset import build_demo_collections
from app.firebase_app import get_firebase_app

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
    "config": {},
    "alert_reviews": {},
    "activities": {},
    "documents": {},
    # Proposals extracted from documents (not operational until approved).
    "extracted_fields": {},
    "clauses": {},
    "financial_terms": {},
    "obligations": {},
    "programme_scope": {},
    "review_issues": {},
    "agreement_changes": {},
    "document_pages": {},
    "tables": {},
    "extraction_chunks": {},  # cached provider output per extraction part (resume after failures)
}
# The configured source is fixed for this process except for an explicitly enabled one-way
# transition to synthetic memory after a Firestore failure. Switching back requires a restart.
_DEMO_MODE = settings.obligot_demo_mode
_AUTO_DEMO_FALLBACK = settings.obligot_auto_demo_fallback
_DEMO_COLLECTIONS = build_demo_collections()
_TEST_MEMORY_STORE = False
_firestore_client = None
_firestore_attempted = False

class DataStoreUnavailable(RuntimeError):
    """A Firestore operation failed (network, permissions, quota, or credentials)."""

_firestore_lock = threading.Lock()


def _get_firestore():
    global _firestore_client, _firestore_attempted
    # The lock makes requests arriving together at startup wait for the client instead of failing.
    with _firestore_lock:
        if _firestore_attempted:
            if _firestore_client is None:
                raise DataStoreUnavailable("Firestore is not initialized")
            return _firestore_client
        _firestore_attempted = True
        try:
            from firebase_admin import firestore
            _firestore_client = firestore.client(app=get_firebase_app())
        except Exception as exc:
            logger.error("Firestore initialization failed: %s", type(exc).__name__)
            raise DataStoreUnavailable(f"Firestore initialization failed: {type(exc).__name__}") from exc
        return _firestore_client


def is_demo_mode() -> bool:
    return _DEMO_MODE


def _activate_demo_fallback(exc: DataStoreUnavailable) -> bool:
    global _DEMO_MODE
    if _DEMO_MODE or _TEST_MEMORY_STORE or not _AUTO_DEMO_FALLBACK:
        return False
    _DEMO_MODE = True
    logger.warning(
        "Firestore unavailable (%s); switched this backend process to isolated synthetic demo data. "
        "Restart to select a data source again.",
        type(exc.__cause__ or exc).__name__,
    )
    return True


def storage_mode() -> str:
    if _DEMO_MODE:
        return "demo-memory-fallback"
    if _TEST_MEMORY_STORE:
        return "test-memory"
    try:
        _get_firestore()
    except DataStoreUnavailable as exc:
        if not _activate_demo_fallback(exc):
            raise
        return "demo-memory-fallback"
    return "firestore"


def _memory_collection(collection: str) -> dict | None:
    if _DEMO_MODE:
        return _DEMO_COLLECTIONS[collection]
    if _TEST_MEMORY_STORE:
        return _COLLECTIONS[collection]
    return None


def firestore_enabled() -> bool:
    return storage_mode() == "firestore"


def _firestore_call(operation: str, collection: str, fn):
    try:
        return fn()
    except Exception as exc:
        raise DataStoreUnavailable(f"Firestore {operation} on '{collection}' failed: {type(exc).__name__}") from exc


def _use_firestore_or_fallback(collection: str, firestore_operation, demo_operation):
    try:
        return firestore_operation()
    except DataStoreUnavailable as exc:
        if not _activate_demo_fallback(exc):
            raise
        return demo_operation(_DEMO_COLLECTIONS[collection])


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

# Firestore read cache. Only this backend writes (client access is denied by firestore.rules), so a collection read
# once stays current through write-through updates below; the TTL picks up writes from another backend process
# (e.g. a teammate's) on the same project. Keeps the free-tier daily read quota for real use, not repeated polling.
_CACHE: dict[str, tuple[float, dict[str, dict]]] = {}


def _cached(collection: str) -> dict[str, dict] | None:
    entry = _CACHE.get(collection)
    if entry and time.monotonic() - entry[0] < settings.firestore_cache_seconds:
        return entry[1]
    return None


def _cache_set(collection: str, record_id: str, payload: dict | None) -> None:
    records = _cached(collection)
    if records is None:
        return
    if payload is None:
        records.pop(record_id, None)
    else:
        records[record_id] = payload


def list_records(collection: str) -> list[dict]:
    memory = _memory_collection(collection)
    if memory is not None:
        if _DEMO_MODE:
            logger.debug("Serving synthetic demo records from memory: %s", collection)
        return [_serialize(v) for v in memory.values()]
    cached = _cached(collection)
    if cached is not None:
        return [copy.deepcopy(v) for v in cached.values()]

    def _load() -> list[dict]:
        rows = _firestore_call(
            "list", collection,
            lambda: [{"id": doc.id, **doc.to_dict()} for doc in _get_firestore().collection(collection).stream()],
        )
        _CACHE[collection] = (time.monotonic(), {r["id"]: r for r in rows})
        return [copy.deepcopy(r) for r in rows]

    return _use_firestore_or_fallback(collection, _load, lambda records: [_serialize(v) for v in records.values()])

def get_record(collection: str, record_id: str):
    memory = _memory_collection(collection)
    if memory is not None:
        record = memory.get(record_id)
        return _serialize(record) if record is not None else None
    cached = _cached(collection)
    if cached is not None:
        return copy.deepcopy(cached[record_id]) if record_id in cached else None

    def _load():
        snapshot = _firestore_call("get", collection, lambda: _get_firestore().collection(collection).document(record_id).get())
        return {"id": snapshot.id, **snapshot.to_dict()} if snapshot.exists else None

    return _use_firestore_or_fallback(
        collection, _load, lambda records: _serialize(records[record_id]) if record_id in records else None,
    )

def put_record(collection: str, data: dict, record_id: str | None = None) -> dict:
    record_id = record_id or f"{collection[:-1] if collection.endswith('s') else collection}-{uuid4().hex[:12]}"
    payload = _serialize(data)
    payload["id"] = record_id
    memory = _memory_collection(collection)
    if memory is not None:
        memory[record_id] = payload
        return payload
    def _write() -> dict:
        _firestore_call("write", collection, lambda: _get_firestore().collection(collection).document(record_id).set(payload))
        _cache_set(collection, record_id, copy.deepcopy(payload))
        return payload

    return _use_firestore_or_fallback(collection, _write, lambda records: records.__setitem__(record_id, payload) or payload)

def patch_record(collection: str, record_id: str, changes: dict) -> dict | None:
    current = get_record(collection, record_id)
    if current is None:
        return None
    current.update(_serialize({k: v for k, v in changes.items() if v is not None}))
    return put_record(collection, current, record_id)

def delete_record(collection: str, record_id: str) -> bool:
    memory = _memory_collection(collection)
    if memory is not None:
        return memory.pop(record_id, None) is not None
    def _delete() -> bool:
        ref = _get_firestore().collection(collection).document(record_id)
        if not ref.get().exists:
            return False
        ref.delete()
        _cache_set(collection, record_id, None)
        return True
    return _use_firestore_or_fallback(
        collection,
        lambda: _firestore_call("delete", collection, _delete),
        lambda records: records.pop(record_id, None) is not None,
    )
