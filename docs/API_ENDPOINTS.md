# ObliGOT API endpoint inventory

All routes are defined in `backend/app/routes.py` and mounted under `/api` by `backend/app/main.py`. The interactive schema is at `/docs` while the backend runs. This table was checked against `app.openapi()` in Step 4f.

Status legend: **tested** = covered by backend pytest in in-memory mode; live Firestore, real-MOU extraction accuracy, and real Firebase token verification are not yet tested. Synthetic text-extraction and scanned-image Groq smoke requests have succeeded.

Live Firestore is the default. Setting `OBLIGOT_DEMO_MODE=true` before starting the backend explicitly selects a separate, synthetic in-memory dataset. `/api/health` and `/api/dashboard` report `demo-memory-fallback` in this mode; demo mutations stay in memory and reset on backend restart. Firestore errors in live mode return `503` and do not switch to synthetic records. Firebase authentication remains enabled according to `REQUIRE_FIREBASE_AUTH` in either mode.

`POST /api/intelligence/analyze` and document PDF extraction use Groq chat completions when `GROQ_API_KEY` is configured. Groq vision reads scanned page images using `GROQ_VISION_MODEL`; structured text extraction uses `GROQ_MODEL`. Keys are server-only. Gemini is not used by document extraction.

## System and dashboard
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/` | Service pointer to docs and health | Public |
| GET | `/api/health` | Status, storage mode (`firestore` / `demo-memory-fallback`), `ai_configured` (Groq), `document_extraction`, `auth_required` | Public even when auth is required; legacy `extraction_without_gemini` is retained as an alias; live-store initialization failure returns 503; demo mode is not a Firestore health check |
| GET | `/api/dashboard` | Record-derived metrics, deterministic deadline `findings`, `as_of` (IST business date), storage mode | Findings skip resolved records (Step 4a) |
| GET | `/api/alerts?partner_id=&level=&category=&include_reviewed=` | Deterministic alerts from the rules engine (`app/engine.py`), computed on every call and sorted by priority score; each has `rule_id`, evidence (record vs computed values), why it matters, recommended action, owner, due date, `related_alert_ids`, and a priority breakdown | `level` must be `high`, `medium`, or `low` (422 otherwise). Each alert has `review` (current, or `null`), `previous_review` when the facts changed since, and `hidden_by_review`. Dismissed and still-deferred alerts are omitted unless `include_reviewed=true`; `counts.hidden_by_review` reports how many |
| POST | `/api/alerts/{alert_id}/review` | Record `acknowledged`, `deferred` (`deferred_until` after today, ≤ 365 days), or `dismissed` (`reason` ≥ 5 chars); stored in `alert_reviews` with a fingerprint of the alert's stored facts; logs an activity | 404 if the alert is not currently raised; 422 on invalid combinations |
| DELETE | `/api/alerts/{alert_id}/review` | Clear a review (reopen); logs an activity | 404 if no review |
| POST | `/api/alerts/{alert_id}/task` | Create an action prefilled from the alert (title, evidence, recommended action, partner, owner, priority; optional overrides `title`, `owner`, `due_date`, `priority`), linked by `source_alert_id`; review becomes `task_created` | 201; 404 if alert not raised; **409** if an open/in-review task already exists for the alert |
| GET | `/api/activities?partner_id=&entity_id=&limit=` | Audit log, newest first (default 50, max 500) | |
| GET | `/api/rules` | Rule catalogue: id, title, description, category, severity, why it matters, recommended action | |
| GET / PATCH | `/api/rules/config` | Thresholds: `mou_expiry_warning_days` (1–365, default 60), `deadline_warning_days` (1–180, default 30), `stale_opportunity_days` (7–365, default 30) | Unknown keys or out-of-range values → 422 |
| GET | `/api/rules/deadline-preview` | Preview one deadline finding for `record_id`, `record_type`, `label`, `due_date` | Preview only |

## Partners
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/partners?q=` | List/search by name, category, owner | |
| POST | `/api/partners` | Create (201) | `source_label=user` |
| GET | `/api/partners/{partner_id}` | Detail | 404 if missing |
| PATCH | `/api/partners/{partner_id}` | Partial update; `null` clears optional fields | 422 if a required field is cleared |
| DELETE | `/api/partners/{partner_id}` | Delete (204) | **409** while opportunities, agreements, projects, milestones, finance, reports, actions, or follow-ups reference it |

## Actions (tasks)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/actions?status=&related_partner_id=` | List with optional status and partner filters | |
| POST | `/api/actions` | Create (201), status starts `open` | 404 if `related_partner_id` missing |
| GET / PATCH / DELETE | `/api/actions/{action_id}` | Detail / update (`null` clears optional fields) / delete | 404 if missing |

## Agreements, projects, finance, reports
Each collection has the same shape:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/{collection}?partner_id=` | List, optional partner filter |
| POST | `/api/{collection}` | Create (201); 404 if the partner does not exist |
| GET / PATCH / DELETE | `/api/{collection}/{id}` | Detail / merged-and-validated update / delete (204); 404 if missing |

`{collection}` is `agreements`, `projects`, `finance`, or `reports`. Validation:
- Agreements: `expiry_date` ≥ `start_date` (422). Optional `signed_copy` (`received`, `pending`, `unknown`; default `unknown`), `renewal_status` (`none`, `in_progress`, `renewed`, `not_renewing`; default `none`), `project_id`, `opportunity_id` (must exist → 404, and must belong to the same partner → 422). `document_url` must start with `https://` or `http://` (422); blank becomes `null`.
- `GET /api/agreements?expiring_within_days=N` (0–3650): active agreements whose `expiry_date` is between today (IST) and today + N days, inclusive.
- Projects: `end_date` ≥ `start_date` (422); PATCH rejects unknown fields.
- Finance: `status` must be allowed for the `record_type` (`FINANCE_STATUSES` in `models.py`); default is the first allowed value. `currency` must be a 3-letter uppercase code. Optional `issue_date` and `received_date`; due date ≥ issue date and received date ≥ issue date (422). `project_id` must exist (404) and belong to the same partner (422). `GET /api/finance?record_type=` filters by type.

## Milestones
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/milestones?project_id=&partner_id=&status=` | List with optional filters | |
| POST | `/api/milestones` | Create (201) | 404 if project missing; `partner_id` is copied from the project (client value ignored); status `planned`, `in_progress`, `completed`, `missed`, `cancelled`; `completed_date` required for and only allowed on `completed` (422) |
| GET / PATCH / DELETE | `/api/milestones/{milestone_id}` | Detail / merged-and-validated update (partner re-derived from project) / delete (204) | 404 if missing |

Projects: `DELETE /api/projects/{id}` returns **409** while milestones, agreements, finance records, or reports reference it; `PATCH` returns **409** when changing `partner_id` while such records exist.

## Pipeline (opportunities)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/opportunities?partner_id=&stage=` | List with optional partner and stage filters | |
| POST | `/api/opportunities` | Create (201); `updated_at` set to the IST business date | 404 if partner missing; 422 for unknown `stage` (`identified`, `qualification`, `proposal`, `approval`, `agreement`, `active`, `renewal`, `closed`) |
| GET / PATCH / DELETE | `/api/opportunities/{opportunity_id}` | Detail / merged-and-validated update (refreshes `updated_at`) / delete (204) | 404 if missing |

Malformed JSON bodies on PATCH routes and JSON import preview return 422 (previously 500).

## Follow-ups (legacy; `actions` is the planned task model)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/followups?status=&related_partner_id=` | List with optional filters |
| POST | `/api/followups` | Create (201) |
| GET / PATCH / DELETE | `/api/followups/{followup_id}` | Detail / status update / delete |

## Intelligence
| Method | Path | Purpose | Notes |
|---|---|---|---|
| POST | `/api/intelligence/analyze` | Groq analysis of `partner_id` summary + `context` | Returns `ai_used`; when false, `ai_error` is `not_configured`, `timeout`, `empty_response`, `api_error:<code>`, or `error:<type>` |

## Import
| Method | Path | Purpose | Notes |
|---|---|---|---|
| POST | `/api/import/preview` | Validate JSON rows (`entity_type`, `rows`) or preview a CSV/XLSX upload (`file`, `entity_type`) | Never writes data (`committed: false`); 422 for unknown `entity_type`; XLSX reads the active sheet only; 5 MB limit |

## Summary and options (Step R3)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/dashboard/summary` | Management summary computed from current records and alerts | Amounts summed per currency and per kind only; coverage from approved scope |
| GET | `/api/options` | Allowed values (schema enums) and current partners, projects, agreements, states, programmes | For forms and filters |

## Documents (P6 document-to-workbook workflow)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| POST | `/api/documents` | Upload an MOU/addendum PDF (multipart: `file`, `kind` = `mou`/`addendum`, optional `partner_id`, `agreement_id`) and inspect it page by page | 201 with a new document ID on every upload, including identical file contents. 415 not multipart or not a PDF; 413 over `MAX_DOCUMENT_MB`; 422 empty file or bad `kind`; 404 unknown partner/agreement; 422 agreement of another partner. A damaged, password-protected, or over-`MAX_DOCUMENT_PAGES` PDF returns 201 with `status: failed` and `error` (file not stored). The UI does not require partner selection. |
| GET | `/api/documents` | List documents, newest first | Filters: `partner_id`, `agreement_id`, `status`, `kind` |
| GET | `/api/documents/{id}` | One document with per-page text status | 404 when missing. Source PDFs remain private and have no download route. |
| POST | `/api/documents/{id}/extract` | Start or retry Groq extraction in the background | 202 with `status: extracting`; poll `GET /api/documents/{id}` for progress until `extracted`, `retry_required`, or `failed`. Completed page readings and extraction chunks are reused on retry. 409 while a run is active (unless stale > 15 min), for an unreadable file, when no extraction method is available for scanned pages, or for legacy reviewed/approved records. 404 when missing. |
| GET | `/api/documents/{id}/extraction` | Extracted values: `extracted_fields`, `clauses`, `financial_terms`, `obligations`, `programme_scope`, `tables`, `review_issues`, plus `document` | Values remain scoped to the source document; they do not create or update operational records. |
| GET | `/api/documents/{id}/export/workbook` | Download an editable, document-specific XLSX containing extracted values, evidence, page readings, tables, extraction notes, and any generated addendum changes | 404 when missing. Edits in the workbook are not saved back to ObliGOT or operational collections. Requires sign-in when `REQUIRE_FIREBASE_AUTH=true`. |
| POST | `/api/documents/{id}/create-records` | Explicit user action on an extracted MOU: creates (or reuses by name) the partner, plus an agreement, project, reports, UCs, milestones, and a budget from the extracted values; marks its obligations and financial terms approved and linked, so the rules engine raises alerts from this MOU | Body `{partner_id?, partner_name?, owner?}`. 404 missing document/partner; 409 when records already exist or the document is not extracted; 422 when no partner name is available. Missing dates stay missing. |
| POST | `/api/documents/{id}/archive` | Hide an MOU that has records, plus every record created from it (agreement, project, reports, UCs, milestones, financial terms); they drop out of every list, total and alert but are kept for audit | Body `{reason}` (3–500 chars, logged). 409 when no records were created (remove instead) or already archived. |
| POST | `/api/documents/{id}/restore` | Undo an archive: the document and its linked records reappear | 409 when not archived. |
| DELETE | `/api/documents/{id}` | Permanently remove a mistaken/duplicate upload: PDF, page readings, extraction | 204. 409 when records were created from it (archive instead) or extraction is running. `GET /api/documents?include_archived=true` lists archived ones. |
| GET | `/api/documents/{id}/pipeline-deal` | This MOU's pipeline deal (created from it, or linked to its agreement) and the values a deal is built from: funder, title, location (programme states/regions), total commitment, start date; stage active, or closed if expired | Returns `{deal: Opportunity or null, proposed}`. No probability or follow-up is invented. |
| POST | `/api/documents/{id}/pipeline-deal` | Add an MOU that already has records to the pipeline (Create records now does this automatically when no deal is linked) | 201 deal. 409 when records were not created yet or a deal already exists. |
| GET | `/api/portfolio` | At a glance: every signed MOU (funder, tier, group, location, period, committed vs received per currency, reports/UCs/deliverables done-overdue-without-evidence, next dated deadline), monthly cashflow (expected from approved dated payment terms vs recorded receipts, per currency), and the same rolled up per funder | Returns `{as_of, mous, cashflow, unscheduled_expected, funders}`. Amounts are never converted or summed across currencies. |
| GET | `/api/compliance/timeliness` | Progress reports and UCs: due date vs date actually done (report `submitted_date`, UC `received_date`), each row's state (on_time, late, overdue, pending, no_due_date) and days; totals for the organisation and per account owner | Returns `{as_of, organisation: {report, uc}, owners: [{owner, report, uc}], rows}`; each summary has total, done, on_time, late, overdue, pending, on_time_rate, average_days_late. |
| POST | `/api/import/commit` | Clean a messy CSV/XLSX (header row detection, synonym header mapping, ₹/lakh/crore amounts, day-first dates, status words) and save valid rows as partners/agreements/projects/finance/reports; unknown partner names create partners; existing duplicates skipped | Multipart `file`, `entity_type`, `dry_run` (`true` = clean only). Returns `{mapping, unmapped, cleaned, rejected, skipped, valid_count, created, new_partners}`. 422 when no partner column (non-partner types). |

## Scanned pages (Step S1)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/documents/{id}/pages` | Document map: per physical page, `method` (`text_layer` / `groq_vision`), `page_type`, `printed_page_number`, section labels, table continuation flags, unreadable spots, legibility, transcript | Filled by extraction; transcripts of scanned pages are AI readings, not verified facts |
| GET | `/api/documents/{id}/pages/{n}/image` | JPEG of one page for side-by-side review (`dpi` 50–200, default 110) | Requires sign-in like every route; `Cache-Control: private, no-store`; 404 outside the page range |

Tables (S2) are exported as editable Excel sheets with their original headers, rows, and source pages. Obligations carry a `deadline` rule (type, wording, offset, unit, trigger, recurrence); evidence carries `section` and `printed_page`.

`POST /api/documents/{id}/extract` reads scanned pages first (at most three page images per Groq vision request), then extracts from the text layer and transcripts; `extraction.pages_to_read` / `pages_read` report progress. Existing page readings and completed extraction chunks are reused on retry. Rate limits (429), timeouts, and temporary overload (5xx) are retried with bounded backoff; otherwise the run records an error and available partial output remains exportable. Legacy `gemini` extraction mode values remain readable; new runs report `groq`.

## Addenda (Step P4a)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/documents/{id}/agreement-candidates` | Agreements an addendum may amend, with reasons (same partner, reference number found) | Suggestion only; nothing is linked automatically |
| PATCH | `/api/documents/{id}/link` | Choose the agreement an addendum amends (`agreement_id`) | Addenda only (422 for an MOU); 422 for a different partner. Link is explicit; no record is applied. |
| POST | `/api/documents/{id}/changes` | Compare an extracted addendum with the agreement's current values; create document-scoped changes (prior → proposed, amendment/effective dates, evidence) | Restated values are reported as `unchanged`; conflicting or unclear values remain notes in the workbook. Changes never update the operational agreement. |
| GET | `/api/documents/{id}/changes` | The addendum's changes in effective-date order | |
| GET | `/api/agreements/{id}/history` | Original values, historical changes, and current effective values | Read-only; historical previously approved changes remain visible. |

## Export (Step P3c)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/export/workbook` | Download the standard operational workbook (`docs/WORKBOOK_SCHEMA.md`) | XLSX attachment `obligot-workbook-<date>.xlsx`; does not include new document-scoped extraction output, which uses the per-document route above. Historical operational records remain. Requires sign-in when `REQUIRE_FIREBASE_AUTH=true`. |

## Common error responses
- `401` missing or invalid Firebase ID token (only when `REQUIRE_FIREBASE_AUTH=true`).
- `404` record not found. `409` delete blocked by linked records. `422` validation failure.
- `503` Firestore or Firebase Auth unavailable or misconfigured.
