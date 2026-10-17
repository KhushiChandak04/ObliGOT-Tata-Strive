---
name: data-import
description: Build or extend ObliGOT's safe spreadsheet (CSV/XLSX) importer — inspect the real workbook first, then mapping, validation, duplicate/conflict detection, preview, confirmed save, and an honest import summary. Never silently merge or overwrite records.
argument-hint: <workbook path or import task>
---

# Data import: $ARGUMENTS

## 1. Inspect the actual workbook first
- Open the provided file with a read-only script (`python -I`, openpyxl `read_only=True, data_only=True`). List every sheet, its header row, row count, sample rows, and data types.
- Classify each sheet: underlying records (pipeline, MOUs, finance, invoices, UCs, funds received) vs aggregate/pivot/summary sheets. **Never import aggregate sheets as records** — use them only for cross-checks.
- Treat the workbook as demonstration data, not as the authoritative business specification. Do not design around accidental blanks or inconsistencies.
- Report findings and the proposed sheet→collection mapping before implementing.

## 2. Pipeline
1. Parse supported sheets (reuse `POST /api/import/preview` in `backend/app/routes.py`; extend it compatibly).
2. Map columns to model fields; show the mapping for review and allow overrides.
3. Normalize only known-safe variations: whitespace, date formats, known status synonyms, numeric strings. Record every normalization applied.
4. Validate required fields, dates (and start ≤ end), amounts (numeric, ≥ 0, currency known), enum values, and references (partner/project must resolve).
5. Detect: in-file duplicates, matches with existing records (by stable ID or exact reference number), conflicts (same key, different values), missing fields, and ambiguous matches.
6. **Never merge records because names look similar** — similar names are flagged as ambiguous for human decision.
7. Preview writes nothing (`committed: false`).
8. Commit only rows the user confirmed, through existing backend models/validation and role checks (admin/manager). No silent overwrites: existing records change only with explicit per-row confirmation.
9. Handle partial failures transparently; label imported records with their source (file name, sheet, row) and `source_label` (`demo` for synthetic data).

## 3. Summary
Return and display counts and row lists for: imported, skipped, invalid, duplicate, conflicting, ambiguous — with reasons.

## 4. Verify
- Pytest with small CSV/XLSX fixtures: multiple sheets, aggregate sheet ignored, bad dates, negative/non-numeric amounts, duplicates, ambiguous names, unresolved partners, preview non-destructive, confirmed commit.
- Run `cd backend && python -m pytest -q` (and frontend build if UI changed). Report real results.

## 5. Report and stop
Update `IMPLEMENTATION_PLAN.md`. **Stop for approval.** If time is short, recommend a reliable preloaded demo dataset over a fragile importer.
