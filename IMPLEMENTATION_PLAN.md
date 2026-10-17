# Implementation Plan

Each step ends with a checkpoint report and requires explicit team approval before the next step begins. Approved steps are committed and pushed to `origin/main` at the end of the step (fetch first; stop and ask if teammates have pushed).

## Step log

| Step | Name                                          | Status                                    |
| ---- | --------------------------------------------- | ----------------------------------------- |
| 1    | Repository and API audit                      | Done — approved                           |
| 2    | Architecture proposal                         | Done — approved                           |
| 3    | Project instructions and custom skills        | Done — approved                           |
| 4    | Existing API route repairs (groups 4a–4f)     | Done — approved                           |
| 5    | Application foundation (5a, 5b, 5c)           | 5a done (API-connected UI, now unrouted); 5b/5c blocked on Firebase credentials |
| 6    | Core partnership workflows (6a–6d)            | Done — approved (backend APIs in use; original pages now unrouted) |
| 7    | Deadline engine and action center (7a–7c)     | 7a, 7b approved; 7c done (UI now unrouted) |
| 8    | Funding and compliance + new-UI integration (8a finance backend, 8b core UI wiring, 8c partner/pipeline/agreements/projects, 8d finance/reports) | 8a approved; 8b done — awaiting review |
| 9    | Gemini AI integration                         | Not started                               |
| 10   | Spreadsheet import                            | Not started                               |
| 11   | Management dashboard and UI polish (+ motion) | Not started                               |
| 12   | Testing and review                            | Not started                               |
| 13   | Deployment and demo preparation               | Not started                               |

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
- Corrected the frontend to a light-only reference palette; removed dark-mode and pink/rose values, added cream GOT chips on green surfaces, and made the warning trace line a cream/bordo chip.
- Verification: `cd frontend && npm run build` passed; repository scan for `prefers-color-scheme`, `data-theme`, `dark:`, pink/rose values returned no matches. Vite reported only the existing chunk-size warning.
- API/data impact: no backend routes or contracts changed; demo records remain client-side, typed, fictional, and labelled `source_label="demo"`.

## Team decisions (recorded only when actually made)

- Keep FastAPI as the single backend (Step 2 approval).
- Step 2 architecture approved: computed-on-read alerts with persisted review decisions, data model and rule set in `ARCHITECTURE.md`.
- Commit and push to GitHub at the end of each approved step; no AI attribution in commits.
- 17 Oct 2026: use the teammate's new frontend (`App.tsx`, `reference/obligot.html` design) and wire it to the FastAPI backend screen by screen, replacing the synthetic `src/data/repository.ts` data and client-side alerts.
- 17 Oct 2026: Step 8a — commit the backend part; drop the 8a edits to the old, now-unrouted pages.
- 17 Oct 2026: spreadsheet parsing for Import uses the existing backend `POST /api/import/preview` instead of the browser `xlsx` package.

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

## Step 8b notes — new UI wired to the API (core) and build fix
- Build fixed: `App.tsx` no longer imports `xlsx`; `package-lock.json` re-synced (no `xlsx`). Verified with a clean `npm ci` + `npm run build` in an isolated copy.
- `App.tsx` (teammate's reference UI, design and CSS classes kept): hard-coded `initialAlerts` removed. `AppShell` loads `/api/alerts`, `/api/actions`, `/api/partners`; alerts are adapted to the UI's view model (`toViewAlert`). Dashboard KPIs (open, overdue, MOUs expiring ≤ 30 d, open follow-ups from alerts), Today's 5 (shared `todaysAlerts`), and "Alerts by category" are derived from API data. Action Center lists all outstanding alerts and real tasks with Mark done; a note shows how many alerts are deferred/dismissed.
- Drawer: verified record facts and computed values from the engine's evidence, rule explanation with the priority breakdown, rule-based next step, and human decisions that call the API (create follow-up task with owner, acknowledge, defer with date, dismiss with reason, reopen). The previous simulated "Ask Gemini" (timer + canned text) was replaced by a real call to `POST /api/intelligence/analyze`; with no key it states "AI was not used (not_configured)". Escape closes the drawer.
- Import: files are parsed by `POST /api/import/preview` (real headers, valid/invalid counts, row issues); "Confirm import" stays disabled until Step 10 instead of showing a fake success. API client sends `FormData` without a JSON content type.
- Loading, error (with Retry), and success states added for the API-backed screens (`.api-state`, reference palette tokens).
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
