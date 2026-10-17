# Implementation Plan

Each step ends with a checkpoint report and requires explicit team approval before the next step begins. Approved steps are committed and pushed to `origin/main` at the end of the step (fetch first; stop and ask if teammates have pushed).

## Step log
| Step | Name | Status |
|---|---|---|
| 1 | Repository and API audit | Done — approved |
| 2 | Architecture proposal | Done — approved |
| 3 | Project instructions and custom skills | Done — approved |
| 4 | Existing API route repairs (groups 4a–4f) | 4a–4c approved; 4d done — awaiting review |
| 5 | Application foundation | Not started |
| 6 | Core partnership workflows | Not started |
| 7 | Deadline engine and action center | Not started |
| 8 | Funding and compliance | Not started |
| 9 | Gemini AI integration | Not started |
| 10 | Spreadsheet import | Not started |
| 11 | Management dashboard and UI polish (+ motion) | Not started |
| 12 | Testing and review | Not started |
| 13 | Deployment and demo preparation | Not started |

## Team decisions (recorded only when actually made)
- Keep FastAPI as the single backend (Step 2 approval).
- Step 2 architecture approved: computed-on-read alerts with persisted review decisions, data model and rule set in `ARCHITECTURE.md`.
- Commit and push to GitHub at the end of each approved step; no AI attribution in commits.

## Open questions (awaiting team input)
1. Firebase project ID, web-app config, service account, and Gemini key availability (needed by Step 5).
2. Location of the sample partnership workbook and the official problem statement.
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
- **4c** Partner DELETE 409 with children *(contract change — needs approval)*, auth init fix, Firestore errors → 503.
- **4d** Per-type finance statuses *(contract change — needs approval)*.
- **4e** Non-blocking Gemini call with honest error reporting.
- **4f** Cleanup (`.bak`, legacy SQLite, `OBLIGOT_DB_PATH`, `xlsx`), refresh `docs/API_ENDPOINTS.md`.

## Acceptance criteria
| Scenario | Pass condition |
|---|---|
| A MOU expiry | Active MOU 30 days out → `MOU_EXPIRING` with dates as evidence; mark renewed → alert gone on next evaluation |
| B Overdue report | Pending report past due → `REPORT_OVERDUE`, high priority; submit → alert gone |
| C AI | Output cites only supplied fact ids; failure → `ai_used=false` with reason, alerts intact |
| D Human action | Task from alert → assign → complete; status persists, activity logged, dashboard updates |
| E Missing data | Active MOU without expiry → `DATA_MISSING`; nothing invented |
| F Finance | Invoice without due date shown by age, never "overdue"; no cross-currency/type totals |
| G Dashboard | KPIs change only via records; no hard-coded numbers |
| H Import | Preview writes nothing; duplicates/invalid rows counted; commit only on confirmation |
| API | Each existing route tested for success, 404, 422, 401/403 |

Baseline checks: `cd backend && python -m pytest -q` passes; `cd frontend && npm run build` passes; `GET /api/health` reports storage mode honestly.

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
