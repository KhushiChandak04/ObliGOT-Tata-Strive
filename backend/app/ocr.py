"""Optional local OCR with Tesseract, used only for scanned pages Groq vision could not read.

Requires the Tesseract program itself (not just a Python package): it is detected on PATH (or TESSERACT_CMD).
When it is missing, nothing here runs and the app behaves as before. OCR output is plain text — tables lose their
structure and stamps or handwriting may garble it — so it is labelled "OCR" wherever it is used and every value
taken from it still goes through review.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pymupdf

from app.config import settings


class OcrFailed(Exception):
    pass


def ocr_available() -> bool:
    return settings.ocr_enabled and shutil.which(settings.tesseract_cmd) is not None


def ocr_page(raw: bytes, page_number: int) -> str:
    """Plain text of one physical page (1-based). Runs locally; nothing is sent anywhere."""
    command = shutil.which(settings.tesseract_cmd)
    if not settings.ocr_enabled or not command:
        raise OcrFailed("Tesseract is not installed")
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        png = doc[page_number - 1].get_pixmap(dpi=settings.ocr_dpi).tobytes("png")
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "page.png"
        image.write_bytes(png)
        try:
            result = subprocess.run([command, str(image), "stdout", "-l", settings.ocr_languages, "--psm", "3"],
                                    capture_output=True, timeout=settings.ocr_timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise OcrFailed(f"OCR of page {page_number} took longer than {settings.ocr_timeout_seconds:g} seconds") from exc
    if result.returncode != 0:
        # Tesseract's own message (e.g. a missing language pack), never document text.
        raise OcrFailed(result.stderr.decode("utf-8", "replace").strip().splitlines()[-1][:200] if result.stderr else "OCR failed")
    return result.stdout.decode("utf-8", "replace")
