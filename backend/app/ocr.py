"""Local OCR for scanned pages: PyMuPDF renders the page, then RapidOCR (pip package, no system install) or
Tesseract (if installed) reads it.

Runs on this machine; nothing is sent anywhere. OCR output is plain text — tables lose their structure and stamps
or handwriting may garble it — so it is labelled "OCR" wherever it is used and every value taken from it still goes
through review.
"""
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import pymupdf

from app.config import settings


class OcrFailed(Exception):
    pass


@lru_cache(maxsize=1)
def _rapidocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    return RapidOCR()


def _engine() -> str | None:
    if not settings.ocr_enabled:
        return None
    if settings.ocr_engine in ("auto", "rapidocr") and _rapidocr() is not None:
        return "rapidocr"
    if settings.ocr_engine in ("auto", "tesseract") and shutil.which(settings.tesseract_cmd):
        return "tesseract"
    return None


def ocr_available() -> bool:
    return _engine() is not None


def engine_name() -> str:
    return _engine() or "none"


def _render(raw: bytes, page_number: int) -> bytes:
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        return doc[page_number - 1].get_pixmap(dpi=settings.ocr_dpi).tobytes("png")


def _lines(boxes: list) -> str:
    """RapidOCR returns text boxes; group boxes on the same visual line, left to right."""
    items = []
    for box, text, _score in boxes:
        ys = [p[1] for p in box]
        items.append((sum(ys) / len(ys), max(ys) - min(ys), min(p[0] for p in box), text))
    items.sort()
    lines: list[list[tuple]] = []
    for item in items:
        if lines and abs(item[0] - lines[-1][0][0]) < max(item[1], lines[-1][0][1]) * 0.6:
            lines[-1].append(item)
        else:
            lines.append([item])
    return "\n".join(" ".join(t for *_, t in sorted(line, key=lambda i: i[2])) for line in lines)


def ocr_page(raw: bytes, page_number: int) -> str:
    """Plain text of one physical page (1-based)."""
    engine = _engine()
    if engine is None:
        raise OcrFailed("No OCR engine is installed (pip install rapidocr-onnxruntime)")
    png = _render(raw, page_number)
    if engine == "rapidocr":
        try:
            boxes, _ = _rapidocr()(png, use_cls=False)  # scans are upright; the angle check costs ~40% of the time
        except Exception as exc:  # the engine's own failure, never document text
            raise OcrFailed(f"OCR of page {page_number} failed ({type(exc).__name__})") from exc
        return _lines(boxes or [])
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "page.png"
        image.write_bytes(png)
        try:
            result = subprocess.run([shutil.which(settings.tesseract_cmd), str(image), "stdout", "-l", settings.ocr_languages,
                                     "--psm", "3"], capture_output=True, timeout=settings.ocr_timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise OcrFailed(f"OCR of page {page_number} took longer than {settings.ocr_timeout_seconds:g} seconds") from exc
    if result.returncode != 0:
        # Tesseract's own message (e.g. a missing language pack), never document text.
        raise OcrFailed(result.stderr.decode("utf-8", "replace").strip().splitlines()[-1][:200] if result.stderr else "OCR failed")
    return result.stdout.decode("utf-8", "replace")
