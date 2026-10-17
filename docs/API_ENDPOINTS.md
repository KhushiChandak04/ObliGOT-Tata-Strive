# ObliGOT API endpoint inventory

All routes are defined in `backend/app/routes.py` and mounted under `/api` by `backend/app/main.py`. The interactive schema is at `/docs` while the backend runs. This table was checked against `app.openapi()` in Step 4f.

Status legend: **tested** = covered by backend pytest in in-memory mode; live Firestore, live Gemini success, and real Firebase token verification are not yet tested.

## System and dashboard
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/` | Service pointer to docs and health | Public |
| GET | `/api/health` | Status, storage mode (`firestore` / `demo-memory-fallback`), `ai_configured`, `auth_required` | Public even when auth is required |
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
| POST | `/api/intelligence/analyze` | Gemini analysis of `partner_id` summary + `context` | Returns `ai_used`; when false, `ai_error` is `not_configured`, `timeout`, `empty_response`, `api_error:<code>`, or `error:<type>` |

## Import
| Method | Path | Purpose | Notes |
|---|---|---|---|
| POST | `/api/import/preview` | Validate JSON rows (`entity_type`, `rows`) or preview a CSV/XLSX upload (`file`, `entity_type`) | Never writes data (`committed: false`); 422 for unknown `entity_type`; XLSX reads the active sheet only; 5 MB limit |

## Documents (Step P2a)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| POST | `/api/documents` | Upload an MOU/addendum PDF (multipart: `file`, `kind` = `mou`/`addendum`, optional `partner_id`, `agreement_id`) and inspect it page by page | 201 with the document. 415 not multipart or not a PDF (checked by file signature); 413 over `MAX_DOCUMENT_MB`; 422 empty file or bad `kind`; 404 unknown partner/agreement; 422 agreement of another partner; 409 same file already uploaded (`detail.document_id`). A damaged, password-protected, or over-`MAX_DOCUMENT_PAGES` PDF returns 201 with `status: failed` and `error` (file not stored). No text extraction or approval happens here. |
| GET | `/api/documents` | List documents, newest first | Filters: `partner_id`, `agreement_id`, `status`, `kind` |
| GET | `/api/documents/{id}` | One document with per-page text status | 404 when missing. There is no download route; files are private. |
| POST | `/api/documents/{id}/extract` | Start Gemini extraction in the background (Step P3a) | 202 with `status: extracting`; poll `GET /api/documents/{id}` (`extraction.chunks_done` / `chunks_total`) until `needs_review` or `failed` (`error`, `extraction.ai_error`). 503 when Gemini is not configured (status unchanged). 409 while running (unless stale > 15 min), when approved, when the file was unreadable, when no page has text, or when proposals were already reviewed. 404 when missing. |
| PATCH | `/api/documents/{id}/proposals/{collection}/{item_id}` | Review one proposal (Step P3b). `collection`: `extracted_fields`, `clauses`, `financial_terms`, `obligations`, `programme_scope`. Body: `decision` (`approve`/`reject`/`defer`/`reset`), optional `value` (corrected extracted field), `changes` (corrected fields of other proposals, approve only), `note` | 422: approving with nothing to approve, bad date, unknown/forbidden change, defer without a note, approving unverified evidence without a note. 409 unless the document needs review. Reviewer and time recorded; logged. |
| PATCH | `/api/documents/{id}/issues/{issue_id}` | Resolve, defer, or reopen a review issue (`status`, `resolution`) | Resolution note required for resolved/deferred |
| GET | `/api/documents/{id}/approval-check` | `{ready, blockers}` (optional `partner_id`, `create_partner`) | Blockers: undecided values, open issues, two different approved values for one field, expiry before start, no partner, addendum (P4), wrong status |
| POST | `/api/documents/{id}/approve` | Approve a reviewed MOU. Body: `partner_id`, `create_partner`, `owner`, `overwrite_existing` | 409 with `blockers`, or with `conflicts` when approved values differ from an already linked agreement (nothing written). Creates/fills the agreement (`source_document_id`), a project when milestones/scope/programme are approved, and milestones, reports, and UC finance records from approved obligations; fund releases and other obligations stay register-only. The document becomes `approved` and locked. |
| GET | `/api/documents/{id}/extraction` | Proposals for review: `extracted_fields`, `clauses`, `financial_terms`, `obligations`, `programme_scope`, `review_issues`, plus `document` | None of these are approved or operational. |

## Scanned pages (Step S1)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/documents/{id}/pages` | Document map: per physical page, `method` (`text_layer` / `gemini_vision`), `page_type`, `printed_page_number`, section labels, table continuation flags, unreadable spots, legibility, transcript | Filled by extraction; transcripts of scanned pages are AI readings, not verified facts |
| GET | `/api/documents/{id}/pages/{n}/image` | JPEG of one page for side-by-side review (`dpi` 50–200, default 110) | Requires sign-in like every route; `Cache-Control: private, no-store`; 404 outside the page range |

`GET /api/documents/{id}/extraction` also returns `tables` (S2): headers, rows with page and raw cells, per-row `verified`, units, notes, section; obligations carry a `deadline` rule (type, wording, offset, unit, trigger, recurrence); evidence carries `section` and `printed_page`. Tables are reviewed through `PATCH /api/documents/{id}/proposals/tables/{item_id}`.

`POST /api/documents/{id}/extract` now reads scanned pages first (page images in batches of `VISION_BATCH_PAGES`), then extracts from the text layer and the transcripts; `extraction.pages_to_read` / `pages_read` report progress. Scanned PDFs are accepted (`uploaded`) when Gemini is configured, and `blocked` only when it is not. Rate limits (429) and temporary overload (503) are retried (`GEMINI_RETRY_DELAYS`); otherwise the run fails with `rate_limited` / `unavailable`.

## Addenda (Step P4a)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/documents/{id}/agreement-candidates` | Agreements an addendum may amend, with reasons (same partner, reference number found) | Suggestion only; nothing is linked automatically |
| PATCH | `/api/documents/{id}/link` | Choose the agreement an addendum amends (`agreement_id`) | Addenda only (422 for an MOU); 422 other partner; 409 once changes were decided or after approval |
| POST | `/api/documents/{id}/changes` | Compare the extracted addendum with the agreement's current values; create proposed changes (prior → proposed, amendment/effective dates, evidence) | Restated values are reported as `unchanged`; two values for one term, or a different value from another addendum with the same effective date → `unresolved`. 409 before linking/extraction or after decisions |
| GET | `/api/documents/{id}/changes` | The addendum's changes in effective-date order | |
| PATCH | `/api/agreement-changes/{id}` | `decision` approve / reject / unresolved / reset; optional `effective_date`, `amendment_date`, corrected `proposed_value` (with `note`) | Approve needs a known effective date and verified evidence (422); 409 when a different value is already approved for the same term and effective date; unresolved needs a note |
| GET | `/api/agreements/{id}/history` | Original values, every change, current effective values, counts (proposed/approved/rejected/unresolved/applied/scheduled) | |

`POST /api/documents/{id}/approve` also approves an addendum once it is linked, compared, every change decided, and issues closed: approved changes in force are applied to the agreement (latest effective date wins per term; status recomputed from the new expiry), future-dated ones are applied when their date arrives (checked when alerts or agreements are read), unresolved and rejected changes are never applied; approved added obligations become operational records.

## Export (Step P3c)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/export/workbook` | Download the standard workbook (`docs/WORKBOOK_SCHEMA.md`) | XLSX attachment `obligot-workbook-<date>.xlsx`; operational records and approved document values only; logged as `workbook_exported`. Requires sign-in when `REQUIRE_FIREBASE_AUTH=true`. |

## Common error responses
- `401` missing or invalid Firebase ID token (only when `REQUIRE_FIREBASE_AUTH=true`).
- `404` record not found. `409` delete blocked by linked records. `422` validation failure.
- `503` Firestore or Firebase Auth unavailable or misconfigured.
