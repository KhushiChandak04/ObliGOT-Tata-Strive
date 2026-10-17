# Implementation Plan

Each step ends with a checkpoint report and requires explicit team approval before the next step begins. Approved steps are committed and pushed to `origin/main` at the end of the step (fetch first; stop and ask if teammates have pushed).

## Step log

| Step | Name                                          | Status                                    |
| ---- | --------------------------------------------- | ----------------------------------------- |
| 1    | Repository and API audit                      | Done — approved                           |
| 2    | Architecture proposal                         | Done — approved                           |
| 3    | Project instructions and custom skills        | Done — approved                           |
| 4    | Existing API route repairs (groups 4a–4f)     | Done — approved                           |
| 5    | Application foundation (5a, 5b, 5c)           | 5a done (API-connected UI, now unrouted); 5b/5c pending auth implementation and backend credentials |
| 6    | Core partnership workflows (6a–6d)            | Done — approved (backend APIs in use; original pages now unrouted) |
| 7    | Deadline engine and action center (7a–7c)     | 7a, 7b approved; 7c done (UI now unrouted) |
| 8    | Funding and compliance + new-UI integration (8a finance backend, 8b core UI wiring, 8c partner/pipeline/agreements/projects) | 8a–8c done. 8d (Finance/Reports UI) moved into P6. 8e–8f (external partner submissions) **cancelled** — never implemented |

Steps 9–13 were replaced on 17 Oct 2026 by the document-to-Excel phases below (product pivot after stakeholder discovery).

| Phase | Name | Status |
| ----- | ---- | ------ |
| P0 | Scope and repository audit | Done — approved |
| P1 | Canonical schema and workbook contract (P1a models + contract) | P1a done — approved |
| P2 | PDF extraction foundation (upload, private storage, PyMuPDF page text, low-text detection, document status) | P2a (backend) done — approved |
| P3 | Evidence-linked extraction (Gemini structured output), review/approve, multi-sheet XLSX export | Done — approved |
| F1 | Firebase connection: Firestore, demo seed, sign-in required (replaces 5b; roles 5c still open) | Done — approved |
| P4 | Addendum reconciliation (link to agreement, old vs proposed, approval, history) | P4a (backend) done — approved. Validated on synthetic addenda only; no real addendum sample yet |
| S1 | Scan-aware page reading (Gemini vision for scanned pages, document map, page images) | Done — approved |
| S2 | Tables, relative deadlines, section-aware extraction (sample-driven) | Done — approved (synthetic fixtures; real samples not sent to Gemini) |
| A1 | Align the teammate's document screens (merged 9da70ea) with the backend API | Done — approved |
| A2 | Finance and Reports & UCs on live data (old 8d); faster Gemini (fallback model, saved page readings) | Done — awaiting review |
| S3 | Arithmetic consistency checks and workbook sheets for budgets/tranches/targets | Not started |
| P5 | Rules engine on approved records only (+ amendment-conflict and contractual fund-release rules) | Mostly existing; additions not started |
| P6 | Frontend integration (documents, review workspace, addendum review, export; Finance/Reports live) | Not started |
| P7 | Grounded AI summaries and alert explanations | Scaffolded (no key; free-text output) |
| P8 | Integration testing and demo readiness | Not started |

> **Note on the two sets of Step 5–6 notes.** The "React application foundation" and "Core workflow screens" notes directly
> below were written by a teammate for the new reference-based frontend (`reference/obligot.html` → `frontend/src/app/App.tsx`),
> pushed on 17 Oct 2026. The later "Step 5a"–"Step 7c" notes describe the API-connected backend and pages built and approved
> in this plan. Team decision (17 Oct 2026): keep the new frontend's design and wire it to the backend API screen by screen.

## Step 5 notes — React application foundation (teammate, new reference UI)

- Rebuilt the frontend shell from `reference/obligot.html`: landing page, animated agent trace, auth tabs, responsive app sidebar, dashboard, Action Center, Partner 360, alert drawer, and placeholder routes.
- Preserved the FastAPI API contracts; this step uses the fictional reference alert set for the approved UI foundation and does not persist demo decisions.
- Added `frontend/src/vite-env.d.ts`, raised the TypeScript library target to ES2021 for existing `replaceAll` usage, and typed an existing `titleCase` callback.
- Verification: `cd frontend && npm install` completed successfully (npm reported 9 existing audit vulnerabilities); `cd frontend && npm run build` completed successfully with Vite production output.
- Review note: Firebase sign-in remains the existing integration boundary; the reference auth form navigates to the dashboard until the auth workflow is wired to the backend in a later approved step.

## Step 6 notes — Core workflow screens (teammate, new reference UI)

- Replaced the placeholder route surfaces with typed synthetic repository-backed Pipeline, Agreements, Projects, Finance, Reports & UCs, and SheetJS Import screens.
- Added deterministic counts, renewal radar buckets, project milestone progress, separated finance totals, missing invoice due-date wording, report tabs, pipeline stage movement, and import preview/confirmation state.
- Fixed the stale SheetJS import after `xlsx` was removed for known advisories: the current preview accepts CSV only and reports malformed or unsupported files; XLSX support remains part of the unstarted Step 10.
- Verification: `cd frontend && npm run build` passed after the fix.
- Corrected the frontend to a light-only reference palette; removed dark-mode and pink/rose values, added cream GOT chips on green surfaces, and made the warning trace line a cream/bordo chip.
- Verification: `cd frontend && npm run build` passed; repository scan for `prefers-color-scheme`, `data-theme`, `dark:`, pink/rose values returned no matches. Vite reported only the existing chunk-size warning.
- API/data impact: no backend routes or contracts changed; demo records remain client-side, typed, fictional, and labelled `source_label="demo"`.

## Team decisions (recorded only when actually made)

- Keep FastAPI as the single backend (Step 2 approval).
- Step 2 architecture approved: computed-on-read alerts with persisted review decisions, data model and rule set in `ARCHITECTURE.md`.
- Commit and push to GitHub at the end of each approved step; no AI attribution in commits.

## Firebase Hosting setup (17 Oct 2026)

- Selected existing Firebase project `obligot-95487`; updated the default Firebase CLI alias and configured the registered web app in ignored `frontend/.env`.
- Hosting serves `frontend/dist`. The frontend still requires a publicly reachable FastAPI URL for API-backed screens; `VITE_API_BASE_URL` currently targets local development only. Do not deploy as a working application until a production API endpoint and auth configuration are ready.
- 17 Oct 2026: use the teammate's new frontend (`App.tsx`, `reference/obligot.html` design) and wire it to the FastAPI backend screen by screen, replacing the synthetic `src/data/repository.ts` data and client-side alerts.
- 17 Oct 2026: Step 8a — commit the backend part; drop the 8a edits to the old, now-unrouted pages.
- 17 Oct 2026: spreadsheet parsing for Import uses the existing backend `POST /api/import/preview` instead of the browser `xlsx` package.
- 17 Oct 2026: the external partner submission workflow (planned as 8e–8f) is **cancelled**. It existed only in the docs; no code was written. Its plan, architecture, and demo references were removed. Internal staff forms stay.
- 17 Oct 2026: product pivot — MOU/addendum PDF → page-aware extraction → evidence-linked structured data → deterministic validation → human approval → Excel-compatible records and export → deterministic alerts → grounded AI explanation → dashboard. Phases P0–P8 replace Steps 9–13.
- 17 Oct 2026 (defaults accepted with the P1a approval): PDFs are stored privately — Firebase Storage in `obligot-95487` through the Admin SDK when a bucket is configured, otherwise a local folder outside git; never in Firestore. `pymupdf` is added to `requirements.txt` in P2. Records entered through the existing staff forms count as approved; only PDF-derived values need review. Only synthetic, labelled fixtures until real MOU samples are shared.

## Open questions (awaiting team input)

1. Gemini key for the backend; confirm Firestore works with the service account on a teammate's machine; a Firebase Storage bucket for private PDFs.
2. Real (or redacted) MOU and addendum samples to replace the synthetic fixtures; the sample partnership workbook.
3. Backend hosting: Cloud Run (recommended) or Render (`render.yaml` exists).
4. Freeze `followups` and use `actions` as the only task model?

## Step 1 audit summary

- Existing backend tests: 9 passed (`python -m pytest -q`, in-memory mode). Live Firestore, Gemini, auth flow, and frontend build untested (no credentials / `node_modules`).
- Verified defects (probe script, in-memory mode):
  1. Deadline findings ignore status — a submitted report is still "Overdue".
  2. "Missing due date" findings for every finance record, including fund receipts and budgets.
  3. Projects/milestones are never evaluated.
  4. PATCH cannot clear a field (`null` ignored).
  5. No start/expiry date-order validation.
  6. Multipart import accepts any `entity_type`; XLSX reads only the active sheet.
  7. No `GET /api/followups` list route.
  8. Deleting a partner orphans child records.
  9. Finance `status` accepts arbitrary text.
- Suspected (unverified): frontend `tsc -b` fails without `vite-env.d.ts`; auth middleware may call `verify_id_token` before the Admin app is initialized; Gemini errors swallowed and call blocks the event loop; server-local `date.today()`.
- Gaps: 7 of 11 pages are scaffolds; dashboard computes metrics client-side (inconsistent with `/api/dashboard`); no pipeline, milestones, signed-copy tracking, audit log, users/roles, or rule config.
- Cleanup candidates: committed `.bak` files, unmounted SQLite `domain_store.py`/`domain_routes.py` (the earlier "removed" note was inaccurate), `OBLIGOT_DB_PATH` in `docker-compose.yml`, unused `xlsx@0.18.5` (known advisories), outdated `docs/API_ENDPOINTS.md`.

## Step 4 repair groups (proposed)

- **4a** Status-aware deadline findings, no missing-date noise on finance, Asia/Kolkata "today".
- **4b** PATCH null-clearing, date-order validation, import `entity_type` validation, `GET /followups`.
- **4c** Partner DELETE 409 with children _(contract change — needs approval)_, auth init fix, Firestore errors → 503.
- **4d** Per-type finance statuses _(contract change — needs approval)_.
- **4e** Non-blocking Gemini call with honest error reporting.
- **4f** Cleanup (`.bak`, legacy SQLite, `OBLIGOT_DB_PATH`, `xlsx`), refresh `docs/API_ENDPOINTS.md`.

## Acceptance criteria

| Scenario         | Pass condition                                                                                               |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| A MOU expiry     | Active MOU 30 days out → `MOU_EXPIRING` with dates as evidence; mark renewed → alert gone on next evaluation |
| B Overdue report | Pending report past due → `REPORT_OVERDUE`, high priority; submit → alert gone                               |
| C AI             | Output cites only supplied fact ids; failure → `ai_used=false` with reason, alerts intact                    |
| D Human action   | Task from alert → assign → complete; status persists, activity logged, dashboard updates                     |
| E Missing data   | Active MOU without expiry → `DATA_MISSING`; nothing invented                                                 |
| F Finance        | Invoice without due date shown by age, never "overdue"; no cross-currency/type totals                        |
| G Dashboard      | KPIs change only via records; no hard-coded numbers                                                          |
| H Import         | Preview writes nothing; duplicates/invalid rows counted; commit only on confirmation                         |
| API              | Each existing route tested for success, 404, 422, 401/403                                                    |

Baseline checks: `cd backend && python -m pytest -q` passes; `cd frontend && npm run build` passes; `GET /api/health` reports storage mode honestly.

## Product pivot — document-to-Excel partnership intelligence (17 Oct 2026)
**Thesis:** turn MOUs and their addenda into verified, Excel-ready records, then use those records to power explainable alerts and the management dashboard.

**Approval gate:** PDF → page text (PyMuPDF) → Gemini proposes fields, clauses, obligations, and changes with page and quote → deterministic checks (types, page range, quote found on the page, dates, amounts) → human review → only approved values reach the operational records, the workbook, and the rules engine. A schema-valid model response is not treated as correct.

**Reused unchanged:** record models and CRUD, link checks, rules engine and priority score, alert review loop and activity log, import preview (re-import path for exported workbooks), the new UI and its forms.

**Known limitations (current):** no real MOU samples (synthetic fixtures only); scanned pages are detected as low-text and need OCR or manual review — no OCR engine is installed; Gemini has not been called successfully (no key); Firestore and Google sign-in are not verified on this machine.

## Sample MOUs (17 Oct 2026)
- Three real MOUs are kept locally in `samples/` (git-ignored with `*.pdf`; never committed). Local inspection with PyMuPDF only (no content printed, nothing sent to Gemini): `MoU 1.pdf` 9 pages, `MoU 2.pdf` 27, `mou_3.pdf` 28 — every page is a single scanned image with no text layer. Before S1 the app would have blocked all three.
- Sending real sample pages to Gemini awaits team confirmation of the API project's data terms (the key behaves like a free-tier key: Pro models return quota errors).
- Gemini model: `gemini-2.5-flash` returns 404 for this key (no longer offered to new projects); default changed to `gemini-3.5-flash` (verified to answer).

## Step A2 notes — Finance and Reports live; faster Gemini
- Finance page: budgets, funds received, invoices, and utilization certificates from `/api/finance`; each record shows its own amount and currency (no totals across records, types, or currencies — the synthetic page summed them); dates as recorded; ageing/due-soon wording from the rules engine's alerts; status changed through a selector limited to the record type's allowed statuses.
- Reports & UCs page: reports from `/api/reports` plus UC finance records; tabs All / Pending / Overdue / Submitted with counts; "Overdue" comes from `REPORT_OVERDUE` / `UC_OVERDUE` alerts (no browser date maths); "Mark submitted" asks for the actual submission date for reports. `src/data/repository.ts` is no longer used by any page.
- Gemini: when the main model answers 503 (overloaded), the next model in `GEMINI_FALLBACK_MODELS` (default `gemini-flash-latest`) is tried at once before waiting; page readings are saved per batch, so a later extraction failure does not force re-reading (and re-sending) pages.
- Verification: `pytest` 268 passed (new fallback test). Headless Chrome (temporary Firebase user, in-memory backend with demo data): four finance sections, no KPI totals; invoice set to paid → saved and its ageing alert cleared; reports tabs All 3 / Pending 1 / Overdue 1 / Submitted 1 → marking the overdue report submitted with a date → Overdue 0 / Submitted 2; 0 px overflow at 390 px on both pages; no console errors.
- Real MoU 1 run (team-approved, free tier): the first attempt read all 9 pages, then extraction failed after repeated 503s from Google; rerun with the fallback model.

## Step A1 notes — document screens aligned with the API
- Context: a teammate's commit (9da70ea, merged in ceff5a5) added Documents and Document review screens. Its API client called routes that do not exist (`/documents/{id}/review`, `/documents/{id}/fields/{id}`, `/documents/{id}/pdf`, `/agreements/{id}/amendments`) and sent `{status}` where the backend expects `{decision}`; nothing started extraction; the PDF link could not carry the sign-in token.
- API client (`functions.service.ts`): `extract`, `review` (from `/extraction`, mapped to the screen's shape), `decide` (any proposal type), `resolveIssue`, `approvalCheck`, `approve` (partner choice / create partner), `pageImage` (authenticated JPEG), `history`, `decideAmendment` (`decision`, effective date, note). Structured 409 details (`blockers`, `conflicts`) are shown as readable messages; blob requests report errors like JSON ones. Types mirror the backend (evidence basis/section/printed page, tables, deadline rules, issues, approval results, amendment changes).
- Document review screen (teammate's layout and classes kept): "Read & extract with Gemini" with live progress (pages read, parts extracted) while the job runs; fields, tables (rendered with unverified rows marked), obligations with their deadline wording, financial terms, clauses, and scope, each with Approve / Reject / Defer and a note (required by the backend to defer or to approve an unverified quote); issues with Resolve / Defer and a resolution note; evidence lines show page, printed page, section, and whether the quote matched the PDF text or an AI reading; clicking a page opens it in the page-image viewer; the backend's approval blockers are listed; partner choice or "create from the approved partner name" when the document has none.
- Documents page: after upload, "Open to extract and review" replaces the metadata-only "demo Excel sheet" (the real workbook export exists).
- Removed synthetic fallbacks added in 9da70ea: the app shell showed a hard-coded sample partner, alert, task, and dashboard metrics while loading, on API errors, or with no records — on the dashboard without any notice — and Partner 360 showed an invented MOU, project, and milestones for the selected real partner while loading. Pages now show their loading, error, and empty states only (project rule: no fabricated records or numbers).
- Dashboard document strip: counts from the real document list (awaiting review, failed/blocked, addenda awaiting review); the `DashboardResponse` fields the backend never sent were removed from the type.
- Restored from F1 (lost in the merge): Log out signs out of Firebase; "Signed in as …" in the sidebar.
- Layout: review rows let wide tables scroll inside the row (0 px page overflow at 390 px; was 94 px); long quotes wrap.
- Verification: `npx tsc -b` clean; `npm run build` passes; `pytest` 267 passed (backend unchanged). Headless Chrome with a temporary Firebase user (deleted afterwards), backend in-process on the in-memory store with Gemini faked (no Firestore writes, no Gemini calls): sign-in → empty Documents list (no sample rows) → upload a synthetic scanned agreement for a partner → "Open to extract and review" → extraction with progress "Reading scanned pages with Gemini: 0 of 3…" → Needs Review → page image loads; evidence link moves the viewer to page 3 → table with 2 rows; 2 issues → blockers listed → approving an unverified quote without a note is refused with the backend's explanation; with a note it is saved → all values and issues decided, blockers cleared → Approve records → Approved → dashboard document strip from real data; no sample partner anywhere → 390 px: 0 px overflow → Log out signs out → backend stopped: dashboard shows the API error and no KPI cards or sample data. Only console error: the expected 422 for the refused approval (plus connection errors after the backend was stopped).
- Not in A1: addendum screens (link, compare, decide changes) — client methods exist, no UI yet; older browser drives from Steps 8b/8c use the pre-F1 fake sign-in and were not re-run.

## Step S2 notes — tables, deadlines, sections, templates
- Tables (`tables` collection, `ExtractedTable`): title, kind (budget, tranches, targets, milestones, logframe, coverage, reporting, other), section, pages, headers as written (multi-level joined with " / "), rows with their page and raw cell text, currency, unit statements (kept, never applied), notes/footnotes, `continues_across_pages`. Each row is checked: every non-empty cell must appear on that row's page text (`verified`); rows that do not match, have the wrong number of cells, or cite a page outside the document are flagged (`TABLE_ROWS_NOT_VERIFIED`); a table without headers is not kept. Numbers are stored as written; nothing is computed or converted. Tables are reviewed like other proposals (approve / reject / defer; title, kind, section, currency, units, notes correctable) and linked to the agreement on approval.
- Continuing tables: pages flagged by the page reading as continuing a table are kept in the same extraction chunk (`chunk_pages(..., keep_with_previous)`), and the prompt asks for one table with its headers across the break.
- Deadlines (`Obligation.deadline`, `DeadlineRule`): type (fixed_date, relative, recurring, unspecified), verbatim wording, offset number and unit (calendar days, working days, months), trigger (month/quarter/half-year/year end, agreement start/end, or an event with its wording), recurrence. A calendar date is kept only for a stated fixed date; a date proposed for a relative or recurring deadline is dropped with a warning; event-based deadlines say a date is set only when the event is recorded. Similar deliverables with different offsets for the same trigger (e.g. 15 vs 20 days after year end) are both kept and flagged `DEADLINE_CONFLICT` with both wordings and pages.
- Evidence gains `section` (clause/schedule/annexure label as printed, from the model) and `printed_page` (from the page reading — never from the model), alongside the physical `page`. Scope rows gain `location` and `period`.
- Templates: values or tables cited from a page read as `receipt_template` are flagged `TEMPLATE_VALUE` and need review (a receipt format is not a payment).
- Prompt additions: read schedules/annexures after the signature page; templates are not payments; budget schedules are planned allocations; keep tables as tables, one per continuing table; deadline wording and type; section labels.
- Verification: `pytest` → 267 passed (9 new in `tests/test_structure.py`, synthetic fixtures modelled on the team's descriptions of the samples: schedules after the signature page kept as budget and tranche tables with rows intact and linked to the agreement on approval; a Q1–Q4 budget table across a page break sent in one chunk and kept as one table with headers; receipt-template values flagged; 15- vs 20-day year-end deadlines both kept and flagged; monthly/quarterly recurring and a 7-working-day event deadline kept as rules with no invented date; row checks; no duplicates on re-run). Real Gemini on the synthetic scanned agreement: budget schedule returned as a table (4 headers, 3 rows, all verified, INR, section "SCHEDULE A"); "within 15 days after the end of each financial year" stored as relative, 15 calendar days, year end, annual; both parties proposed as partner name → flagged as conflicting values. Gemini returned 503 (overloaded) on several attempts today; retries recovered on the second run.
- Not verified: the real sample MOUs through Gemini (awaiting the team's data-use confirmation); amount parsing, cross-checks of totals, and table export (S3).

## Step S1 notes — scan-aware page reading
- `app/page_reading.py`: pages without a text layer are rendered to JPEG (`PAGE_RENDER_DPI`, 150) and read by Gemini in batches (`VISION_BATCH_PAGES`, 4) with a structured schema: faithful transcript in reading order (tables one row per line, cells separated by ` | `; `[unreadable]` / `[redacted]` instead of guesses), printed page number (kept separate from the physical index), page type (cover/stamp, main agreement, signature, schedule, annexure, project proposal, budget, milestone, reporting, receipt template, blank, other), section labels, table continuation flags, unreadable spots, stamps/handwriting, legibility. Each batch must return exactly the pages sent, or the run fails.
- New `document_pages` collection (`PageReading`): one record per physical page, `method` text_layer or gemini_vision; saved only when the whole run succeeds; reused on re-runs (pages are not re-sent). Extraction uses text layer or transcript per page; the prompt tells the model how each page was read, its type, printed number, sections, and table continuation; templates and budget schedules are described as such.
- Evidence records `basis`: `text_layer` or `ai_transcript` (quote matched an AI transcription — weaker; compare with the page image). Page readings add review issues: `UNREADABLE` (each unreadable/redacted spot), `POOR_LEGIBILITY`, `TEMPLATE_PAGE` (receipt formats are not payments).
- `GET /documents/{id}/pages` (document map) and `GET /documents/{id}/pages/{n}/image` (authenticated JPEG for side-by-side review).
- Scanned uploads are `uploaded` (not `blocked`) when Gemini is configured. Gemini calls retry on 429 and 503; tests can never call the real API (guard in `conftest.py`).
- Verification: `pytest` → 258 passed (12 new in `tests/test_page_reading.py`, including 3 local checks on the real sample MOUs — page counts, all pages detected as scanned, accepted for reading, last page renders; no Gemini). Real Gemini run on a **synthetic** 3-page scanned agreement (no real data): pages read with correct types (main agreement, signature, schedule after the signature), printed page "2" detected, table detected; extraction found title, parties, reference, effective/expiry dates, total and two tranches, UC and report obligations, all quotes matched (basis `ai_transcript`). First attempt hit a 503 from Google, which led to the 503 retry.
- Gaps seen in that run (next steps): budget table rows are not kept as rows (S2 tables); "within 15 days after year end" has no due date and the rule itself is not stored (S2 relative deadlines); the model labelled the grantor as the legal entity — reviewer correction needed.
- Not verified: any real sample MOU through Gemini (awaiting data-use confirmation).

## Step P4a notes — addenda (backend)
- New `app/amendments.py`: agreement candidates (suggestions with reasons, never auto-linked), `link`, change building against the agreement's current values, per-change decisions, addendum approval, application in effective-date order, and `GET /api/agreements/{id}/history`.
- Rules: the addendum's `execution_date` is the amendment date and its `effective_date` the date of effect. Changeable terms: expiry and start dates (on the agreement record; drive alerts) and renewal/termination terms, duration, scope, programme name (effective view and workbook). Additions (new obligations, financial terms, clauses) are separate "add" changes. Approval needs verified evidence and a known effective date (the reviewer may enter it from the document). Two values in one addendum, or a different value with the same effective date in another addendum, are `unresolved` and never applied. Originals are never overwritten: every change keeps prior and proposed values; `history` reports the original values.
- Application: on addendum approval, approved changes already in effect are applied (latest effective date wins per term; agreement status recomputed as active/expired from the new expiry); future-dated ones are applied when the date arrives — checked whenever alerts or agreements are read (idempotent, logged as "System (effective date reached)"). Alerts follow because they are computed from records.
- Workbook: `amended`, `unresolved_changes`, renewal terms from the effective view, and the `Addenda_Change_History` sheet.
- Shared helpers moved into `document_review.py` (`create_operational`, `ensure_project`) so MOU and addendum obligations follow the same rules. The P3b test "addenda cannot be approved" was replaced by "an unlinked addendum cannot be approved".
- Verification: `pytest` → 246 passed (10 new in `tests/test_amendments.py`, "today" fixed at 17 Oct 2026: one partner with two independent MOUs; candidates suggested not linked; linking rules; prior/proposed comparison; restated value not a change; approval applies the change, clears `MOU_EXPIRING`, keeps the original, creates the added impact report, updates the workbook; effective date required and future changes applied only when due; two addenda applied in effective-date order regardless of approval order; conflicting addenda unresolved and not applied; two values in one addendum unresolved; unverified evidence cannot be approved; decided changes lock the link).
- **Validation limit:** tested only with synthetic addenda. Real addendum formats are unvalidated until a sample is available.

## Step P3c notes — workbook export
- `GET /api/export/workbook` (`app/workbook_export.py`, openpyxl, off the event loop): nine contract sheets plus `About`, built from the persisted records only — operational records and approved document values; pending/rejected/deferred proposals excluded. Values are written as stored with contract types (real dates, numbers, booleans); missing values stay empty; no storage paths or hashes.
- Agreements carry the approved execution/effective dates and renewal terms from their source document; approved obligations show the status of the record they created and are not listed twice.
- Verification: `pytest` → 236 passed (7 new in `tests/test_workbook_export.py`: download headers and sheet order; every sheet's headers, required cells, types, formats, enum values; references resolve; rows match the store and missing values stay empty; unapproved and rejected values excluded and approved ones included with page and quote; no private metadata; the `Partners` sheet re-imports through the existing preview with all rows valid). Real export from Firestore: Partners 3, Agreements 3, Programmes_Projects 1, Obligations_Milestones 6; opened with openpyxl.
- Found while testing: a third-party `tests` package in this machine's site-packages shadows `tests.*` imports; test helpers are imported as sibling modules instead.
- Not verified: opening the file in Microsoft Excel itself (no Excel here; checked with openpyxl).

## Step P3b notes — review and approval gate (backend)
- New `app/document_review.py`: per-proposal decisions (approve with optional correction, reject, defer, reset), issue resolution, `approval-check`, and `approve`. Every decision records reviewer and time and is logged in `activities`.
- Safeguards: approving needs a value (nothing is approved empty); dates must be real ISO dates; approving a value whose quote was not verified requires a note; deferring requires a reason; only listed fields can be corrected; decisions are locked once the document is approved.
- Approval gate (MOU only; addenda wait for P4): every value decided, every issue resolved or deferred with a note, one approved value per field, expiry not before start, a partner chosen (or created from the approved partner name on request). All payloads are validated before any write.
- Effects: agreement created (`status` active, or expired when the approved expiry has passed — computed, not guessed; `start_date` = approved effective date, else start date; `signed_copy` stays `unknown`; `source_document_id` set) or, for a linked agreement, empty fields filled and differing values returned as `conflicts` (409, nothing written) unless `overwrite_existing`. A project is created when milestones, scope, or a programme name are approved. Approved obligations become milestones (milestone/deliverable), reports (progress/impact; type from frequency), or UC finance records; fund releases and others stay in the obligations register (no money record invented). Rejected and deferred values never reach operational records. Alerts follow automatically because they are computed from records.
- Model additions: `Agreement.source_document_id`, `Obligation.operational_ref`, reviewer fields on `ProgrammeScope`.
- Tests now ignore a developer's local `.env` (auth, Firebase credentials, Gemini key) — found when the local `REQUIRE_FIREBASE_AUTH=true` broke them.
- Verification: `pytest` → 229 passed (12 new in `tests/test_document_review.py`). On real Firestore (in-process, Gemini faked): upload → extract → review → approve with partner creation → agreement, project, milestone, report, UC in Firestore → alerts `MOU_EXPIRING`, `MOU_SIGNED_COPY_MISSING`, `REPORT_OVERDUE` on the approved records; all 29 created records deleted afterwards and Firestore matched its previous state.
- Known limits: recurring reports ("within 15 days of each quarter end") become one report without a due date (a data-quality alert), not a generated schedule; approval writes are validated first but not transactional; no UI yet (P6).

## Step F1 notes — Firebase connection and sign-in
- Backend: new setting `FIREBASE_CREDENTIALS_FILE` (service-account JSON, relative paths resolve inside `backend/`) passed to the Admin SDK — a `GOOGLE_APPLICATION_CREDENTIALS` value written only in `.env` was never seen by the SDK. Locally: `backend/firebase-admin.json` (git-ignored), `FIREBASE_CREDENTIALS_FILE=firebase-admin.json`, `REQUIRE_FIREBASE_AUTH=true` in the ignored `backend/.env`. `firebase-admin` 7.7.0 installed from `requirements.txt`.
- Firestore verified on project `obligot-95487`: temporary record written, read, deleted; the database was empty. `backend/scripts/seed_demo.py` loaded the 21 fictional demo records once (partners 3, actions 2, agreements 3, projects 1, finance 4, reports 2, opportunities 3, milestones 3); a second run added nothing. Seeded dates are fixed at 17 Oct 2026.
- No Firebase Storage bucket exists in the project (`obligot-95487.firebasestorage.app` and `.appspot.com` both absent), so PDFs stay in the private local folder. Enabling Storage is needed before deploying the backend to Cloud Run.
- Frontend (`lib/auth.tsx`, `App.tsx` Auth/AppShell; teammate's design kept): real email/password sign-in and sign-up (display name), Google sign-in kept (popup, redirect fallback); readable error messages; the read-only "Role: Manager" field removed (roles are not implemented); workspace routes require a signed-in user (`RequireAuth`, return to the requested page via `next`, only same-app paths accepted); signed-in user shown in the sidebar; Log out signs out of Firebase.
- Verification: `pytest` → 217 passed (new test: credentials file reaches the Admin SDK). `npm run build` passes. Live backend on Firestore with auth required: health `firestore`/`auth_required: true`; no token and a bad token → 401. Headless Chrome with temporary Firebase users (created and deleted via the Admin SDK): signed-out `/dashboard` → `/auth?next=/dashboard`; wrong password → "Email or password is incorrect."; sign-in → dashboard from Firestore (8/2/1/0, user in sidebar); reload keeps the session; `/auth` while signed in → dashboard; log out → `/agreements` asks to sign in; sign-up → back to `/agreements` with live data; `next=//evil.example` ignored. A token-authenticated write records the user's email as the activity actor. Test task and activity entries removed afterwards. Only console error: the expected HTTP 400 from Firebase for the wrong password.
- **Not verified:** Google sign-in (needs a real Google account in a visible browser — please try "Continue with Google" once; `localhost` must be an authorized domain). Roles (admin/manager/viewer) not implemented: any signed-in Firebase user has full access.

## Step P3a notes — evidence-linked extraction (backend)
- `POST /api/documents/{id}/extract` (202, background job) and `GET /api/documents/{id}/extraction`. Status: `extracting` → `needs_review`, or `failed` with a reason; progress in `extraction` (`chunks_done`/`chunks_total`, pages sent, low-text pages skipped, `ai_used`, `ai_error`, counts).
- `app/extraction.py`: text pages are grouped into chunks of whole pages (`EXTRACTION_CHUNK_CHARS`, default 40 000; a page is never cut; every text page is sent). One Gemini call per chunk with JSON output constrained to the `ChunkExtraction` schema, temperature 0, `GEMINI_EXTRACTION_TIMEOUT_SECONDS` (120). The prompt marks pages (`<<<PAGE n>>>`), requires an exact quote and page for every item, forbids guessing, keeps budget/invoice, estimate/confirmed, ceiling/spent, received/owed, signing/effective/start distinct, and tells the model to ignore instructions inside the document.
- Deterministic checks after the model: schema validation (malformed → failed); dates only as real ISO dates (otherwise empty + `DATE_NOT_NORMALIZED`); currency must be a 3-letter code and an amount without one is not stored (warning shows the stated number, `AMOUNT_WITHOUT_CURRENCY`); financial year format; every quote verified on its cited page (`EVIDENCE_NOT_VERIFIED`, `EVIDENCE_MISSING`); conflicting values for one field (`CONFLICTING_VALUES`, error); expiry before start (`DATE_ORDER`); partner name or expiry missing from an MOU (`MISSING_FIELD`, never guessed); model-reported `ambiguities` (`AMBIGUOUS`); termination/penalty/exception clauses always flagged for legal review. Items with warnings or unverified evidence are `needs_review`; nothing is approved.
- All-or-nothing: proposals are saved only after every chunk succeeds; a failure in any chunk saves none, marks the document `failed` (rate limit, timeout, API error, empty or malformed response, unreadable file), and can be retried. Re-running replaces earlier proposals unless some were already reviewed (409). Activity log: `extraction_started`, `extraction_completed`, `extraction_failed`.
- Models: `ExtractionRun` added; `SourceDocument.extraction`; `Clause`/`FinancialTerm`/`Obligation`/`ProgrammeScope` links (`agreement_id`, `partner_id`, `project_id`) optional for proposals and `document_id` + `warnings` added. New collections: `extracted_fields`, `clauses`, `financial_terms`, `obligations`, `programme_scope`, `review_issues`.
- Verification: `python -m pytest -q` → 216 passed (21 new in `tests/test_extraction.py`, Gemini replaced by fakes; synthetic MOU text). The Gemini SDK converts `ChunkExtraction` to its schema offline (enums and required fields present). Live uvicorn: extract without a key → 503 with a clear message, status stays `uploaded`, no proposals; routes in OpenAPI.
- **Not verified:** a real Gemini extraction (no `GEMINI_API_KEY` here) — quality, latency, and rate limits on real MOUs are unknown. No real MOU samples yet.

## Step P2a notes — PDF upload and page inspection (backend)
- New routes in `app/document_routes.py` (mounted at `/api`): `POST /api/documents` (multipart), `GET /api/documents`, `GET /api/documents/{id}`. Additive; no existing contract changed except that partner DELETE now also counts linked `documents` in its 409.
- Upload checks: multipart only; `kind` mou/addendum; partner/agreement must exist and match (an agreement supplies its partner); non-empty; size ≤ `MAX_DOCUMENT_MB` (20); PDF signature in the first 1024 bytes; same file (SHA-256) already uploaded → 409 with the existing id.
- `app/pdf_inspect.py` (PyMuPDF, run off the event loop): reads every page; page count and per-page character count and `text`/`low_text` status. Damaged, password-protected, or over-`MAX_DOCUMENT_PAGES` (500) PDFs → record saved with `status: failed` and a readable reason; the file is not stored. Nothing is truncated: too many pages is a failure, not a partial read.
- Status after upload: `uploaded` when there is usable text; low-text pages listed in `warnings` ("not extracted"); `blocked` when no page has text (likely scanned — OCR not available yet). An addendum without an agreement gets a warning to choose one. Upload never extracts values or approves anything.
- `app/document_storage.py`: private local folder (`DOCUMENT_STORAGE_DIR`, default `backend/.document_store/`, git-ignored); files named only by server-generated id (`doc-<12 hex>.pdf`); the original filename is kept for display only (path parts and control characters removed). No download route. Firestore holds metadata only.
- `SourceDocument` gains `size_bytes` and `sha256` (additive). Every upload is logged in `activities` (`document_uploaded`).
- `pymupdf>=1.24.0,<2.0.0` added to `requirements.txt` (tested with 1.28.2). New settings: `DOCUMENT_STORAGE_DIR`, `MAX_DOCUMENT_MB`, `MAX_DOCUMENT_PAGES` (in `backend/.env.example`).
- Verification: `python -m pytest -q` → 195 passed (15 new in `tests/test_document_upload.py`, synthetic PDFs generated in the tests: 3-page text PDF, 60-page PDF with page 60 intact in storage, blank page flagged, all-blank PDF blocked, CSV/renamed binary/empty/oversized rejected and nothing stored, damaged and password-protected PDFs failed, page limit, duplicate 409, link validation, unsafe filename, list filters/404, activity log and partner-delete 409). Live check against a running uvicorn: upload 201 (3 pages, page 3 low-text warning), duplicate 409, CSV 415, list, one file in the private folder, activity entry, both routes in OpenAPI, no server errors.
- Limitations: local storage only (not durable on Cloud Run; Firebase Storage adapter once a bucket exists); no OCR; no frontend yet (P6); agreement DELETE does not yet check linked documents (would be a contract change — to propose with P4).

## Step P1a notes — data contract
- New `backend/app/documents.py` (models only, no routes yet): `SourceDocument` (kind mou/addendum, status uploaded → extracting → needs_review → approved, failed, blocked; private `storage_ref`; per-page text status), `Evidence` (document, page, quote, verified), `ExtractedField` (verbatim, proposed value, warnings, review state, approved value, reviewer), `Clause`, `FinancialTerm` (contractual terms, separate from finance records; basis confirmed/estimated/ceiling/unspecified), `Obligation`, `ProgrammeScope`, `AgreementChange` (prior and proposed value, amendment/effective dates, evidence, status), `ReviewIssue`.
- Validation rules: approved/rejected states need reviewer and time; an unapproved field cannot carry an approved value; a document is approved only with an approval record; an amount needs a currency; financial year as `2026-27`; an addendum change can be approved only with verified evidence; effective date not before amendment date; resolved/deferred issues need a note. Missing values stay `null`.
- `verify_evidence`: deterministic — page must exist and the quote must appear on that page after documented normalization (NFKC, straight quotes/dashes, whitespace, case, line-break hyphens). A `verified` flag from model output is ignored and recomputed. `page_text_status` marks pages under 40 characters as low-text.
- New `backend/app/workbook.py`: nine-sheet contract (Partners, Agreements, Programmes_Projects, Programme_Scope, Financial_Terms, Obligations_Milestones, Clauses, Addenda_Change_History, Validation_Review_Issues) with column types, required flags, enum values taken from the models, and references between sheets. `Programme_Scope` is added to the proposed eight sheets so one MOU covering several states/courses stays one row per item. Documented in `docs/WORKBOOK_SCHEMA.md` (generated from the contract).
- No routes, collections, or existing contracts changed.
- Verification: `python -m pytest -q` → 180 passed (21 new in `tests/test_documents.py`); `npm run build` passes (frontend unchanged).

## Step 8c notes — Partner 360, Pipeline, Agreements, Projects on the API
- Partner 360: partner picker (`/partner-360?id=`), title from the selected partner; profile with Edit (reuses `PartnerForm`); MOU timeline from the partner's agreement dates (active agreement with the nearest expiry; elapsed share computed against the backend's `as_of` date); open alerts for the partner (open the shared drawer); linked-record counts linking to each register; recent activity.
- Pipeline: reference kanban columns mapped onto the API lifecycle stages (Opportunity = identified, MOU = agreement, Implementation = active, Closure = closed); cards show partner, title, owner, next step and date; "Move to …" PATCHes the stage; Add/Edit/Delete via `OpportunityForm`.
- Agreements: expiry radar buckets come from the backend `expiring_within_days` filter (30/60/90; the browser only subtracts counts); table with real fields (signed copy, renewal, safe document links); search and status filter; Add/Edit/Delete via `AgreementForm`.
- Projects: reference cards with real milestones and progress; Add/Edit project (`ProjectForm`), Add/Edit/Complete milestones (`MilestoneForm`, completion date required).
- The tested API forms and native `<dialog>` are reused; their classes (`.dialog`, `.form-grid`, `.form-field`, `.button-*`, …) are restyled with the reference palette tokens. Edits reload the shared alerts so the sidebar count updates.
- Responsive fixes: `.project-grid` was two columns at every width (pre-existing) → one column under 700 px; card headings wrap; `.small-btn` no longer stretches inside toolbars and button rows.
- Verification: `npm run build` passes. Headless Chrome on the live API: Partner 360 (timeline 94% elapsed, 8 alerts open the drawer, linked counts, picker switch, edit persists across reload), Pipeline (stage move, create with validation), Agreements (radar 1/0/0, filters, marking renewal "renewed" lowers open alerts 8→7), Projects (completion requires a date; progress 1→2 of 3; alerts 7→6; add project); 0 px overflow at 375/390/768/1280 on all four pages and the dashboard; dialog fits at 390 px; no console errors. Regression: 8b drive passes on a fresh backend.
- Not in 8c: Finance and Reports still synthetic (8d).

## Step 8b notes — new UI wired to the API (core) and build fix
- Build fixed: `App.tsx` no longer imports `xlsx`; `package-lock.json` re-synced (no `xlsx`). Verified with a clean `npm ci` + `npm run build` in an isolated copy.
- `App.tsx` (teammate's reference UI, design and CSS classes kept): hard-coded `initialAlerts` removed. `AppShell` loads `/api/alerts`, `/api/actions`, `/api/partners`; alerts are adapted to the UI's view model (`toViewAlert`). Dashboard KPIs (open, overdue, MOUs expiring ≤ 30 d, open follow-ups from alerts), Today's 5 (shared `todaysAlerts`), and "Alerts by category" are derived from API data. Action Center lists all outstanding alerts and real tasks with Mark done; a note shows how many alerts are deferred/dismissed.
- Drawer: verified record facts and computed values from the engine's evidence, rule explanation with the priority breakdown, rule-based next step, and human decisions that call the API (create follow-up task with owner, acknowledge, defer with date, dismiss with reason, reopen). The previous simulated "Ask Gemini" (timer + canned text) was replaced by a real call to `POST /api/intelligence/analyze`; with no key it states "AI was not used (not_configured)". Escape closes the drawer.
- Import: files are parsed by `POST /api/import/preview` (real headers, valid/invalid counts, row issues); "Confirm import" stays disabled until Step 10 instead of showing a fake success. API client sends `FormData` without a JSON content type.
- Loading, error (with Retry), and success states added for the API-backed screens (`.api-state`, reference palette tokens).
- Merge note: a teammate's concurrent fix (26024c4, CSV-only browser parsing for Import) was merged; per team decision the ImportPage conflict was resolved in favour of the backend `/api/import/preview` version, and the unused browser CSV parser was removed. The teammate's Step 6 note about a CSV-only preview therefore describes the superseded version.
- Not in 8b: Partner 360, Pipeline, Agreements, Projects, Finance, Reports still use the synthetic `src/data/repository.ts` (Steps 8c/8d). The previous API-connected pages under `src/pages` are no longer routed; they are kept for reuse while wiring 8c/8d.
- Verification: `npm run build` passes; clean `npm ci` + build passes; `pytest` 159 passed. Headless Chrome on the live API: landing → sign-in screen → dashboard (KPIs 8/2/1/0 match the API; Today's 5 and categories from API) → drawer (facts, computed, breakdown 50+15+10) → AI returns honest `not_configured` → create task (empty owner rejected) → follow-ups KPI 0→1 → dismiss (reason required; 8→7 outstanding, hidden note) → ageing alert evidence (50 days since issue) → defer (min tomorrow) → acknowledge → mark task done → backend activity log shows each decision → CSV import preview (2 valid, 2 invalid with reasons; confirm disabled) → synthetic pages still render → 390 px: 0 px overflow, drawer fits after its slide-in animation; no console errors.

## Step 8a notes — finance (backend)
- Finance records gain optional `issue_date` and `received_date`; `currency` must be a 3-letter uppercase code; due date ≥ issue date and received date ≥ issue date (422). `GET /api/finance` gains a `record_type` filter. Linked `project_id` must exist (404) and belong to the same partner (422) on create and PATCH (shared `_check_links`, also used by agreements).
- New rule `INVOICE_AGING` (risk): a raised/sent invoice with no due date and an issue date older than `invoice_aging_days` (config, default 30, range 7–365) is described by its age ("Days since issue"), never as overdue. `INVOICE_DUE_DATE_MISSING` now applies only when there is neither a due date nor an issue date.
- Demo: the demo invoice has an issue date 50 days ago (now `INVOICE_AGING`); the demo fund receipt has a received date.
- Verification: `pytest` → 159 passed (15 new in `tests/test_finance.py`).
- Frontend: the 8a edits to the old Finance/Partner 360 pages were discarded per the team decision; the finance screen will be wired in the new UI. `FinanceRecord` type in `frontend/src/types/index.ts` updated to mirror the API.
- Known issue on `main` (teammate commit 3ab0689): `App.tsx` imported `xlsx`, which is not in `package.json`, so `npm run build` failed on a clean install. Fixed in Step 8b.

## Step 7c notes — action center UI

- Action center: summary strip; Today's 5 (shared definition with the dashboard); all alerts with filters and a reviewed toggle; tasks with mark done and reassign; alert detail dialog with evidence split into record/computed values, why it matters, priority breakdown, related alerts, and review actions with validated forms (owner required for tasks, reason ≥ 5 chars to dismiss, defer date after today). Deep links `?alert=` / `?task=`; a stale alert link shows an explanatory message.
- Dashboard: "Open alerts" KPI (by level) and Today's 5 from `/api/alerts` (links into the Action center); open tasks link to their row. Partner 360: "Open alerts" tab from `/api/alerts?partner_id=` and a new Activity tab. `FindingList` removed; nothing in the UI reads dashboard `findings` any more.
- Small backend additions found while testing: review records store `rule_title`/`record_title` so the "reopened" activity entry is readable (test updated). Evidence values are presented readably (dates formatted, snake_case statuses title-cased).
- Verification: `pytest` → 144 passed. `npm run build` passes. Headless Chrome full loop: dashboard KPI 8 (2/3/3) and Today's 5 → deep link → detail (evidence, score 50+15+10=75, 7 related) → create task (validation, then success; alert leaves Today's 5) → dismiss (reason required; hidden count 1; visible with toggle; banner) → reopen → defer (min date tomorrow) → acknowledge → complete the milestone (alert clears; task shows "from a resolved alert") → reassign and mark task done → dashboard KPI 6 (1/3/2) → Partner 360 activity log of every step in IST → stale deep link message → keyboard open/Escape → 390 px: 0 px overflow, dialog fits; no console errors. Regression drives 6a–6d pass on a fresh backend (only expected 409s).
- Open decision: dashboard `findings` (legacy `rules.scan_deadlines`) is now unused by the UI; propose removing it (contract change) and retiring `scan_deadlines`.
- Not in 7c: Reports and Finance pages are still placeholders (Step 8), so alert "Record" links for those types land on placeholder pages until then.

## Step 7b notes — review loop and activity log

- `app/reviews.py`: review model and validation, fact fingerprint, review attachment (hide dismissed / still-deferred), activity logging, actor resolution.
- Routes: `POST|DELETE /api/alerts/{id}/review`, `POST /api/alerts/{id}/task` (prefilled from alert, `source_alert_id`, duplicate open task → 409), `GET /api/activities`; `GET /api/alerts` gains `include_reviewed`, per-alert `review` / `previous_review` / `hidden_by_review`, and `counts.hidden_by_review`. Actions log creation, status changes, and reassignment. `ActionItem` gains optional `source_alert_id` (additive).
- Bug found by tests and fixed: activity timestamps had one-second precision, so events in the same second could be listed out of order; now microsecond timestamps plus a per-process sequence tie-breaker.
- Verification: `pytest` → 144 passed (12 new in `tests/test_reviews.py`: acknowledge, dismiss with reason and reappearance after a fact change, dismissal surviving daily day-count changes, defer validation and expiry, reopen, 404 for resolved alerts, task creation prefill and duplicate 409, task completion and reassignment logging, full alert → task → resolution loop, activity ordering/filters/limit). Repeated 3× and in reverse file order: all pass.
- Not in 7b: UI (7c); role restrictions on who may dismiss or change config (5c).

## Step 7a notes — deterministic rules engine

- New `app/engine.py`: 19 rules with stable ids, descriptions, why-it-matters text, and recommended actions; alerts computed on read with id `{rule_id}:{record_type}:{record_id}`; evidence lists stored values (`source: record`) and derived values (`source: computed`); `related_alert_ids` link alerts for the same partner; transparent priority breakdown; deterministic ordering.
- Renewal-aware: `renewed`/`not_renewing` suppress expiry alerts; `in_progress` keeps the alert with −10 priority.
- Invoices without a due date are reported as missing data (age cannot be determined without an issue date); never called overdue.
- Routes: `GET /api/alerts` (filters partner, level, category), `GET /api/rules`, `GET|PATCH /api/rules/config` (stored as `config/rules`).
- Dashboard `findings` intentionally unchanged (still `rules.scan_deadlines`) so the current UI keeps working; 7c moves the UI to `/api/alerts`, after which retiring `findings` will be proposed as a contract change.
- Demo data yields 8 alerts (2 high, 3 medium, 3 low).
- Verification: `pytest` → 132 passed (55 new in `tests/test_engine.py`: every rule's boundaries and non-firing statuses, config thresholds, score arithmetic and levels, cross-record threshold, evidence shape, determinism, API filters, resolve-clears-alert, config validation); also passes run alone and in reverse file order.

## Step 6d notes — projects and milestones

- New `milestones` collection and routes. `partner_id` is always derived server-side from the milestone's project (client value ignored), so milestones cannot drift from their project's partner. Status `planned`/`in_progress`/`completed`/`missed`/`cancelled`; `completed_date` is required for and only allowed on `completed`.
- Integrity: `DELETE /api/projects/{id}` → 409 while milestones, agreements, finance, or reports reference it; changing a project's partner → 409 while such records exist; partner delete also counts milestones.
- Demo milestones on demo-project-001: one completed, one in progress and past due, one planned.
- Frontend: Projects register (search, status filter, add/edit with confirmed delete showing 409 details); expandable milestone rows (`aria-expanded`/`aria-controls`) with add, edit, delete, and "Mark complete" (status preset, user must enter the actual completion date — never assumed). Partner 360 Projects tab gains add (partner locked) and edit. On phones the milestone panel is sticky inside the horizontally scrolling table so it stays readable.
- Verification: `pytest` → 77 passed (7 new in `tests/test_milestones.py`, demo integrity extended). `npm run build` passes. Headless Chrome: expand/collapse state; mark complete blocked without a date then succeeds (count 1→2 of 3); add, complete, reopen (completed date dropped), delete milestone; partner change and delete of the demo project blocked with link counts; date-order validation; create/delete unlinked project; Partner 360 add with locked partner; milestone panel within viewport at 375/390 px whether the table is scrolled left or right; 0 px page overflow; only expected 409s in console.
- Not in 6d: overdue-milestone rule (Step 7).

## Step 6c notes — agreements/MOU register

- Agreement fields added (optional, backward compatible): `signed_copy` (default `unknown`), `renewal_status` (default `none`), `project_id`, `opportunity_id`. Links must exist (404) and belong to the agreement's partner (422), checked on create and PATCH (including when the partner changes).
- Security: `document_url` restricted to http(s) server-side (blocks `javascript:`/`data:` links that the UI renders as anchors); the UI renders only http(s) links, opened with `rel="noopener noreferrer"`.
- `GET /api/agreements?expiring_within_days=N` filter evaluated on the backend against the IST business date (inclusive window, active agreements only), so the browser does no deadline date math.
- Demo: MOU-001 signed copy received, renewal in progress, linked to demo project and a document link; addendum signed copy pending; draft MOU linked to demo-002's opportunity.
- Frontend: Agreements register (search; status, signed-copy, and backend "expiring within 60 days" filters; sorted by expiry; add/edit with confirmed delete); Partner 360 Agreements tab gains add (partner locked) and edit. Project/opportunity choices are limited to the selected partner and cleared when the partner changes.
- Accessibility fix (found by the browser tests): hints and errors were inside `<label>`, so they became part of each field's accessible name. New shared `FormField` links them via `aria-describedby` and sets `aria-invalid`; applied to the partner, opportunity, and agreement forms.
- Verification: `pytest` → 70 passed (9 new in `tests/test_agreements.py`). `npm run build` passes. Headless Chrome: 6c drive (register columns, safe link attributes, filters incl. backend expiry window, partner-scoped link options, client validation, direct API `javascript:` URL → 422, create/edit/delete, Partner 360 add with locked partner, 0 px overflow at 390 px, no console errors) plus regression reruns of the 6a and 6b drives (pass; only expected 409). Field accessible names verified to equal the label text with hints/errors as descriptions.
- Not in 6c: signed-copy-missing, expired-without-renewal, and renewal-aware expiry rules (Step 7).

## Step 6b notes — partnership pipeline

- New `opportunities` collection and routes (`GET/POST /api/opportunities`, `GET/PATCH/DELETE /api/opportunities/{id}`); stages `identified → qualification → proposal → approval → agreement → active → renewal → closed` validated server-side; `updated_at` set on create and every PATCH; partner must exist. Additive — no existing contract changed.
- Partner DELETE 409 now also counts opportunities.
- Shared `_read_json_object`: malformed JSON on PATCH routes (agreements, projects, finance, reports, opportunities) and JSON import preview now returns 422 instead of 500.
- Demo opportunities: demo-001 renewal (linked to its expiring MOU), demo-002 proposal, demo-003 identified.
- Frontend: Pipeline page with stage filter chips (counts, `aria-pressed`), table sorted by stage then next-step date, one-click "advance to next stage" (none once closed), add/edit dialog with inline delete confirmation; Partner 360 gains a Pipeline tab. Form field errors now clear as the field is edited (also fixed in PartnerForm).
- Verification: `pytest` → 61 passed (6 new in `tests/test_opportunities.py`, demo integrity extended). `npm run build` passes. Headless Chrome: stage counts 1/0/1/0/0/0/1/0; filters incl. empty stage state; advance Proposal→Approval refreshes updated date; renewal→Closed leaves no advance button; create with validation; edit clears next-step date; delete with confirmation; Partner 360 Pipeline tab; demo-003 delete blocked by `opportunities: 1`; 0 px overflow at 390/768/1280/1440; only the expected 409 in console.
- Not in 6b: stale next-step and approved-without-MOU rules (Step 7); dashboard pipeline chart (Step 11).

## Step 6a notes — partner directory and Partner 360

- Demo dataset (in-memory fallback only; all `source_label=demo`, fictional, dates relative to the IST business date) in `backend/app/demo_data.py`. demo-001 produces exactly five findings: MOU expiring in 21 days, active addendum missing expiry, monthly report 6 days overdue, invoice without due date, UC due in 10 days; a submitted report and received/approved finance records produce none. demo-002 has a draft MOU only; demo-003 has no linked records.
- `GET /api/actions` gains optional `related_partner_id` filter (additive).
- Tests: new `tests/conftest.py` isolates the in-memory store per test (restores collections after each test) — previously tests leaked records into each other; `tests/test_demo_data.py` checks labels, references, create-model validity, and the exact expected findings.
- Frontend: partner directory with search, status filter, clear filters, and "Add partner" dialog; `PartnerForm` (create/edit, client validation mirroring backend limits, blank optional fields sent as `null` to clear). Partner 360: profile, Edit, Delete (409 linked-record message shown, confirm disabled), keyboard-accessible tabs (Open findings, Agreements, Projects, Finance, Reports, Actions) with counts and empty states. Finance amounts shown per record in their own currency; never totalled. Native `<dialog>` wrapper (focus trap, Escape). Shared `FindingList` used by dashboard and Partner 360. Inline SVG favicon.
- Verification: `pytest` → 55 passed. `npm run build` passes. Headless Chrome against live servers: filter + clear; empty-submit and bad-email validation; create → navigates to new partner with zero-count tabs; edit clears contact; delete returns to directory; demo-001 tab counts 5/2/1/4/2/1 and the five expected findings; ArrowRight moves tab selection and focus; finance tab shows ₹ amounts per record and "Not set" for the invoice due date; deleting demo-001 shows the 409 counts; Escape closes the dialog; 0 px overflow at 390 px; dialog fits at 390 px; only expected 409 in console.
- Not done in 6a: creating/editing agreements, projects, finance, reports from Partner 360 (6c/6d/Step 8); activity history and AI summary (Steps 7/9); role restrictions (5c).

## Step 5a notes — frontend foundation

- `npm install` (npm 11.16, Node 26.3); `package-lock.json` committed. npm 11 skipped install scripts for esbuild, @firebase/util, protobufjs (not approved); build works without them.
- Build was failing (verified): untyped `import.meta.env` and `replaceAll` vs ES2020 lib. Added `src/vite-env.d.ts`; tsconfig target/lib → ES2021. `npm run build` now passes.
- Typed API client per resource (`api.partners|actions|agreements|projects|finance|reports|followups`, `dashboard`, `health`, `analyze`) with `ApiError(status)`; status 0 = backend unreachable. JSON `Content-Type` only on requests with a body. FastAPI validation errors are flattened to readable messages.
- `useResource` hook (ignores superseded responses; clears data on error so stale values never sit next to an error). `StatusBadge`; `StateMessage` gains `action` and ARIA roles.
- Dashboard reads `/api/dashboard` metrics and findings (no client-side metric derivation); shows `as_of`, the in-memory storage warning, and evidence per finding. Removed a misleading "partners in pipeline" (total − active) card and the raw finance count.
- Partner detail uses `GET /api/partners/{id}` with distinct 404 vs error states and Retry.
- `formatDate` parses date-only strings in local time (no day shift west of UTC).
- CSS fixes found in the browser: mobile nav forced 280 px horizontal page scroll (flex `min-width:auto`, pre-existing); dashboard grid overflowed at all widths (grid children `min-width:auto`); hidden table label escaped its scroll container.
- Verification (headless Chrome via Python Playwright against live uvicorn + Vite): dashboard, partners, partner detail, missing partner render API data; 0 px horizontal overflow at 375/390/768/1280/1440 on all three pages; backend stopped → "API connection unavailable" + Retry, all metrics "—", badge "AI STATUS UNKNOWN"; restart + Retry recovers; no page errors. Remaining console 404s are the expected API 404 for a missing partner (twice in dev due to React StrictMode) and a missing favicon.
- `npm audit`: 8 advisories (5 high, 3 moderate) in firebase→@grpc/grpc-js, vite/esbuild (dev server), react-router; every fix is a major upgrade (Vite 8, React Router 7) — awaiting team decision.

## Step 4f notes — cleanup

- Removed (verified unreferenced with `git grep`): `backend/app/models.py.bak`, `routes.py.bak`, `routes.routes-fix.bak`, legacy SQLite `domain_store.py` and `domain_routes.py` (never mounted).
- `docker-compose.yml`: removed `OBLIGOT_DB_PATH` and the `obligot_data` volume (SQLite only); set `PORT: "8000"` because the Dockerfile defaults to 8080 while compose publishes 8000 (found by reading; Docker not run).
- `frontend/package.json`: removed unused `xlsx@0.18.5` (no imports; known advisories). No lockfile is tracked.
- `backend/requirements.txt`: `google-genai>=1.0.0,<3.0.0` (code tested against 2.23.0).
- Added `.gitattributes` (`* text=auto eol=lf`). All tracked files were already LF in the index, so no content renormalization was needed.
- Rewrote `docs/API_ENDPOINTS.md`, checked against `app.openapi()`.
- Step 4 route repair is complete. Remaining verified defect from Step 1: projects/milestones not evaluated (Step 7).

## Step 4e notes — non-blocking Gemini with honest errors

- `analyze_context` uses `client.aio.models.generate_content` under `asyncio.wait_for` (`GEMINI_TIMEOUT_SECONDS`, default 20), so a slow Gemini call no longer blocks other requests.
- `AnalyzeResponse` gains optional `ai_error` (additive): `not_configured`, `timeout`, `empty_response`, `api_error:<code>`, `error:<ExceptionType>`. Summary text states the reason. Errors are logged by type/code only.
- Frontend `api.analyze` return type updated with `ai_error`.
- Verification: `python -m pytest -q` → 51 passed (8 new in `tests/test_intelligence.py`, including a concurrency test that fails if the blocking client is used). Real library check with an invalid key → `ai_error=api_error:400`, fallback returned.
- Not yet tested: a successful live Gemini call (no valid key). Output is still line-split free text — replaced by validated structured output in Step 9.
- Note: `requirements.txt` pins `google-genai<2.0.0` while this machine has 2.23.0; the code uses APIs present in both. Align in 4f.

## Step 4d notes — per-type finance statuses

- `FinanceCreate.status` is validated against `FINANCE_STATUSES[record_type]` (approved contract change). Default on create is the first entry:
  - budget: `planned`, approved, revised, closed
  - fund_received: `expected`, received, cancelled
  - invoice: `raised`, draft, sent, paid, cancelled
  - utilization_certificate: `pending`, submitted, accepted, rejected
- Invalid or cross-type statuses → 422 on POST and PATCH; changing `record_type` requires a compatible status in the same request.
- `FinanceRecord` (response) still accepts any string, so legacy records remain readable; editing one requires choosing a valid status.
- Deadline rules unchanged: resolved finance statuses (`paid`, `received`, `submitted`, `accepted`, `cancelled`, …) already covered.
- Verification: `python -m pytest -q` → 43 passed (12 new in `tests/test_finance_statuses.py`). Probe defect 9 (free-text status) → 422.

## Step 4c notes — referential integrity, auth init, store errors

- `DELETE /api/partners/{id}` returns 409 listing linked record counts (agreements, projects, finance, reports via `partner_id`; actions, follow-ups via `related_partner_id`). Approved contract change.
- New `app/firebase_app.py` creates the Firebase Admin app once; Firestore and token verification share it, so token checks no longer depend on a prior repository call.
- `app/auth.py` now exposes `verify_token` (unused `verify_bearer_token` dependency removed). Middleware: missing/invalid token → 401; Firebase not configured, not installed, or certificates unreachable → 503.
- Firestore operation failures raise `DataStoreUnavailable` → 503 with a clear message and a server log; fallback to in-memory mode is now logged with its reason.
- Verification: `python -m pytest -q` → 31 passed (9 new in `tests/test_auth_and_store.py`). Startup check without `firebase_admin`: warning logged, health reports `demo-memory-fallback`.
- Untested: real `firebase_admin` token verification and live Firestore (package and credentials not available locally). Auth outcomes are covered with monkeypatched `verify_token`.

## Step 4b notes — validation and missing routes

- PATCH `/api/partners/{id}` and `/api/actions/{id}` now apply explicit `null` to clear optional fields. The merged record is validated against the full model, so clearing a required field (e.g. partner `name`) returns 422 instead of corrupting the record. Omitted fields are unchanged; unknown stored fields are preserved.
- `AgreementCreate` (expiry ≥ start) and `ProjectCreate` (end ≥ start) validate date order → 422 on POST and PATCH.
- `POST /api/import/preview` multipart uploads now reject unknown `entity_type` with 422 (checked before reading the file), same set as the JSON path; default remains `projects`.
- New `GET /api/followups` with optional `status` and `related_partner_id` filters.
- Contract impact: inverted dates and bad upload `entity_type` now return 422 (previously accepted). No frontend callers affected.
- Verification: `python -m pytest -q` → 22 passed (8 new in `tests/test_route_repairs.py`). Probe: defects 4–7 fixed.

## Step 4a notes — status-aware deadline findings

- `scan_deadlines` now skips resolved records: reports `submitted`/`accepted`; finance `paid`/`received`/`submitted`/`accepted`/`completed`/`closed`/`cancelled` (case-insensitive, finance status is still free text until 4d); agreements `closed`.
- Agreements are evaluated only when `active` or `expired`, with "Expired"/"Expiring soon"/"Missing expiry date" wording. Drafts and under-review agreements are skipped.
- Finance: only `invoice` and `utilization_certificate` are evaluated; budgets and fund receipts no longer produce "Missing due date" noise.
- Each finding now includes `Recorded status: …` evidence when a status exists.
- "Today" comes from `business_today()` (UTC offset setting `BUSINESS_UTC_OFFSET_MINUTES`, default 330 = IST, no DST). Used by rules, dashboard, partner `updated_at`, and demo data.
- API contract: unchanged except the additive `as_of` field on `GET /api/dashboard`. Finding shape unchanged.
- Verification: `python -m pytest -q` → 14 passed (5 new tests). Probe: defects 1 and 2 fixed; defect 3 (projects/milestones) deferred to Step 7 as planned.

## Step 3 notes

- Created `CLAUDE.md` and seven project skills in `.claude/skills/` (`build-feature`, `firebase-workflow`, `review`, `ui-polish`, `motion`, `data-import`, `demo-check`).
- Risk: the project skill `/review` shares its name with a Claude Code built-in review command; verify which one `/review` invokes. Renaming requires team approval.
