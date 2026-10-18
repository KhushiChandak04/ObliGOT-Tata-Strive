"""Build the standard multi-sheet operational workbook (contract: app/workbook.py).

This workbook includes operational records and legacy document values that were approved before the document
workflow changed. New extraction output is available only in its document-scoped workbook. Values are written
as stored: nothing is inferred, missing cells stay empty, and amounts are never summed. No private file metadata.
"""
import io
from datetime import date, datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.amendments import current_terms
from app.repository import is_demo_mode, list_records
from app.rules import business_today
from app.workbook import SHEETS, Column

HEADER_FILL = PatternFill("solid", fgColor="1F4D3F")
HEADER_FONT = Font(bold=True, color="FFFFFF")
FORMATS = {"date": "yyyy-mm-dd", "datetime": "yyyy-mm-dd hh:mm", "number": "#,##0.00", "integer": "0"}


def _approved(collection: str) -> list[dict]:
    return [r for r in list_records(collection) if r.get("review_state") == "approved"]


def _ev(record: dict) -> dict:
    evidence = record.get("evidence") or {}
    return {"source_document_id": evidence.get("document_id") or record.get("document_id"),
            "source_page": evidence.get("page"), "source_quote": evidence.get("quote")}


def collect_rows(today: date | None = None) -> dict[str, list[dict[str, Any]]]:
    """Rows per sheet, keyed by contract column names. Pure read of the repository."""
    partners, agreements, projects = list_records("partners"), list_records("agreements"), list_records("projects")
    fields = _approved("extracted_fields")
    by_document: dict[str, dict[str, Any]] = {}
    for f in fields:
        by_document.setdefault(f["document_id"], {})[f["field"]] = f.get("approved_value")
    legal_names = {}
    for document in list_records("documents"):
        name = by_document.get(document["id"], {}).get("legal_entity_name")
        if document.get("status") == "approved" and document.get("partner_id") and name:
            legal_names[document["partner_id"]] = name
    agreement_by_project = {a["project_id"]: a["id"] for a in agreements if a.get("project_id")}

    rows: dict[str, list[dict[str, Any]]] = {sheet: [] for sheet in SHEETS}
    for p in partners:
        rows["Partners"].append({**p, "partner_id": p["id"], "legal_entity_name": legal_names.get(p["id"])})
    changes = list_records("agreement_changes")
    for a in agreements:
        source = by_document.get(a.get("source_document_id") or "", {})
        own = [c for c in changes if c["agreement_id"] == a["id"]]
        rows["Agreements"].append({
            **a, "agreement_id": a["id"], "execution_date": source.get("execution_date"),
            "effective_date": source.get("effective_date"), "renewal_terms": current_terms(a).get("renewal_terms"),
            "amended": any(c.get("applied_at") for c in own),
            "unresolved_changes": sum(1 for c in own if c["status"] == "unresolved"),
            "source_document_id": a.get("source_document_id"), "review_state": "approved"})
    for c in changes:
        rows["Addenda_Change_History"].append({
            **c, "change_id": c["id"], "source_page": (c.get("evidence") or {}).get("page"),
            "source_quote": (c.get("evidence") or {}).get("quote")})
    for p in projects:
        rows["Programmes_Projects"].append({**p, "project_id": p["id"], "agreement_id": agreement_by_project.get(p["id"])})
    for s in _approved("programme_scope"):
        rows["Programme_Scope"].append({**s, **_ev(s), "scope_id": s["id"]})
    for t in _approved("financial_terms"):
        rows["Financial_Terms"].append({**t, **_ev(t), "term_id": t["id"], "amended": False})

    # Obligations: approved document obligations (with the status of the record they created), then
    # operational milestones, reports, and UCs that did not come from a document.
    referenced: set[str] = set()
    current = {c: {r["id"]: r for r in list_records(c)} for c in ("milestones", "reports", "finance")}
    for o in _approved("obligations"):
        ref = o.get("operational_ref") or {}
        record = current.get(ref.get("collection", ""), {}).get(ref.get("id", ""), {})
        if ref:
            referenced.add(ref["id"])
        rows["Obligations_Milestones"].append({
            **o, **_ev(o), "obligation_id": o["id"], "status": record.get("status"),
            "due_date": record.get("due_date", o.get("due_date")), "owner": record.get("owner") or o.get("owner"),
            "amended": False})
    for m in current["milestones"].values():
        if m["id"] not in referenced:
            rows["Obligations_Milestones"].append({
                "obligation_id": m["id"], "agreement_id": agreement_by_project.get(m.get("project_id")), "partner_id": m.get("partner_id"),
                "project_id": m.get("project_id"), "obligation_type": "milestone", "title": m["title"], "frequency": "once",
                "due_date": m.get("due_date"), "status": m.get("status"), "owner": m.get("owner"), "amended": False,
                "review_state": "approved"})
    for r in current["reports"].values():
        if r["id"] not in referenced:
            rows["Obligations_Milestones"].append({
                "obligation_id": r["id"], "agreement_id": agreement_by_project.get(r.get("project_id")), "partner_id": r.get("partner_id"),
                "project_id": r.get("project_id"), "obligation_type": "impact_report" if r.get("report_type") == "impact" else "progress_report",
                "title": r["title"], "frequency": r.get("report_type") if r.get("report_type") in ("monthly", "quarterly") else "unspecified",
                "due_date": r.get("due_date"), "status": r.get("status"), "owner": r.get("owner"), "amended": False,
                "review_state": "approved"})
    for f in current["finance"].values():
        if f.get("record_type") == "utilization_certificate" and f["id"] not in referenced:
            rows["Obligations_Milestones"].append({
                "obligation_id": f["id"], "agreement_id": agreement_by_project.get(f.get("project_id")), "partner_id": f.get("partner_id"),
                "project_id": f.get("project_id"), "obligation_type": "utilization_certificate", "title": f["title"],
                "frequency": "unspecified", "due_date": f.get("due_date"), "status": f.get("status"), "owner": None,
                "amended": False, "review_state": "approved"})
    for c in _approved("clauses"):
        rows["Clauses"].append({**c, "clause_id": c["id"], "verbatim_text": c.get("verbatim"),
                                "source_page": (c.get("evidence") or {}).get("page")})
    for i in list_records("review_issues"):
        rows["Validation_Review_Issues"].append({**i, "issue_id": i["id"]})
    for sheet in rows:
        rows[sheet].sort(key=lambda r: str(r.get(SHEETS[sheet][0].name)))
    return rows


def _cell(column: Column, value: Any) -> Any:
    if value is None or value == "":
        return None
    if column.type == "date":
        return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    if column.type == "datetime":
        return (value if isinstance(value, datetime) else datetime.fromisoformat(str(value))).replace(tzinfo=None)
    if column.type == "number":
        return float(value)
    if column.type == "integer":
        return int(value)
    if column.type == "bool":
        return bool(value)
    return str(value)


def build_workbook(today: date | None = None) -> bytes:
    today = today or business_today()
    rows = collect_rows(today)
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, columns in SHEETS.items():
        ws = wb.create_sheet(sheet_name)
        ws.append([c.name for c in columns])
        for cell in ws[1]:
            cell.font, cell.fill, cell.alignment = HEADER_FONT, HEADER_FILL, Alignment(vertical="center")
        for record in rows[sheet_name]:
            ws.append([_cell(c, record.get(c.name)) for c in columns])
        for index, column in enumerate(columns, start=1):
            letter = get_column_letter(index)
            if column.type in FORMATS:
                for cell in ws[letter][1:]:
                    cell.number_format = FORMATS[column.type]
            longest = max([len(column.name)] + [len(str(c.value)) for c in ws[letter][1:] if c.value is not None])
            ws.column_dimensions[letter].width = min(max(longest + 2, 10), 60)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{max(ws.max_row, 1)}"
    about = wb.create_sheet("About")
    about.append(["ObliGOT partnership workbook"])
    about["A1"].font = Font(bold=True, size=13)
    for line in (
        f"Business date (IST): {today.isoformat()}",
        "DATA SOURCE: SYNTHETIC DEMO — NOT CONNECTED TO LIVE FIRESTORE RECORDS." if is_demo_mode()
        else "Data source: live Firestore records.",
        "Contains operational records and legacy document values previously approved. New document extraction output is exported separately.",
        "Empty cells mean the value is not recorded; nothing was inferred. Amounts are per record in their own currency and never summed.",
        "Rows with source_label = demo are fictional demonstration data.",
        "Column definitions: docs/WORKBOOK_SCHEMA.md.",
    ):
        about.append([line])
    about.column_dimensions["A"].width = 120
    from app.document_workbook import append_consolidated_sheet
    append_consolidated_sheet(wb)
    wb.active = 0  # Partners first, so the sheet re-imports through the existing import preview
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
