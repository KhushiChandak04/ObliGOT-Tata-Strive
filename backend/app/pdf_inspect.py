"""Page-by-page PDF inspection with PyMuPDF: page count, embedded text, and low-text (likely scanned) pages.

Every page is read; nothing is truncated. No OCR is performed — low-text pages are reported so a person (or a
later OCR/vision step) can handle them, never treated as if their content had been extracted.
"""
from dataclasses import dataclass

import pymupdf

from app.documents import DocumentPage, page_text_status

PDF_SIGNATURE = b"%PDF-"


class PdfInspectionError(Exception):
    """The file could not be read as a PDF. `code` is machine-readable; str(self) is a user-facing reason."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PdfInspection:
    page_count: int
    pages: list[DocumentPage]
    page_texts: list[str]

    @property
    def low_text_pages(self) -> list[int]:
        return [p.page_number for p in self.pages if p.text_status == "low_text"]


def looks_like_pdf(raw: bytes) -> bool:
    # The PDF header may be preceded by a few junk bytes; the spec allows it within the first 1024.
    return PDF_SIGNATURE in raw[:1024]


def inspect_pdf(raw: bytes, max_pages: int) -> PdfInspection:
    try:
        doc = pymupdf.open(stream=raw, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several exception types for damaged files
        raise PdfInspectionError("unreadable_pdf", "The file could not be opened as a PDF (it may be damaged).") from exc
    with doc:
        if doc.needs_pass:
            raise PdfInspectionError("password_protected", "The PDF is password-protected; upload an unprotected copy.")
        if doc.page_count == 0:
            raise PdfInspectionError("no_pages", "The PDF has no pages.")
        if doc.page_count > max_pages:
            raise PdfInspectionError(
                "too_many_pages", f"The PDF has {doc.page_count} pages; the limit is {max_pages}. Split it and upload the parts.")
        texts: list[str] = []
        try:
            for page in doc:
                texts.append(page.get_text("text"))
        except Exception as exc:
            raise PdfInspectionError("unreadable_pdf", f"Page {len(texts) + 1} could not be read.") from exc
    pages = [DocumentPage(page_number=i + 1, char_count=len(t.strip()), text_status=page_text_status(t))
             for i, t in enumerate(texts)]
    return PdfInspection(page_count=len(pages), pages=pages, page_texts=texts)
