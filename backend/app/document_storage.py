"""Private storage for uploaded PDFs. File bytes never go into Firestore.

Current backend: a local folder (DOCUMENT_STORAGE_DIR, git-ignored). Files are named by server-generated document
ID only, so user-supplied filenames never reach the filesystem. There is no public download route.
Firebase Storage is the intended backend once a bucket is configured; on Cloud Run a local folder is not durable.
"""
import re
from pathlib import Path

from app.config import settings

_SAFE_ID = re.compile(r"^doc-[0-9a-f]{12}$")


def _root() -> Path:
    root = Path(settings.document_storage_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parent.parent / root
    return root


def save_pdf(document_id: str, raw: bytes) -> str:
    """Store the file and return its private storage reference (`local:<id>.pdf`)."""
    if not _SAFE_ID.match(document_id):
        raise ValueError("invalid document id")
    root = _root()
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{document_id}.pdf").write_bytes(raw)
    return f"local:{document_id}.pdf"


def load_pdf(storage_ref: str) -> bytes:
    name = storage_ref.removeprefix("local:")
    if not storage_ref.startswith("local:") or not _SAFE_ID.match(name.removesuffix(".pdf")) or not name.endswith(".pdf"):
        raise ValueError("invalid storage reference")
    return (_root() / name).read_bytes()


def delete_pdf(storage_ref: str) -> None:
    name = storage_ref.removeprefix("local:")
    if not storage_ref.startswith("local:") or not _SAFE_ID.match(name.removesuffix(".pdf")) or not name.endswith(".pdf"):
        raise ValueError("invalid storage reference")
    (_root() / name).unlink(missing_ok=True)


def safe_display_name(filename: str | None) -> str:
    """Original filename kept for display only: path parts and control characters removed, length limited."""
    name = re.split(r"[\\/]", filename or "")[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return (name or "document.pdf")[:255]
