# ObliGOT API endpoint inventory

All routes are defined in `backend/app/routes.py` and mounted under `/api` by `backend/app/main.py`. The interactive schema is at `/docs` while the backend runs. This table was checked against `app.openapi()` in Step 4f.

Status legend: **tested** = covered by backend pytest in in-memory mode; live Firestore, live Gemini success, and real Firebase token verification are not yet tested.

## System and dashboard
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/` | Service pointer to docs and health | Public |
| GET | `/api/health` | Status, storage mode (`firestore` / `demo-memory-fallback`), `ai_configured`, `auth_required` | Public even when auth is required |
| GET | `/api/dashboard` | Record-derived metrics, deterministic deadline `findings`, `as_of` (IST business date), storage mode | Findings skip resolved records (Step 4a) |
| GET | `/api/rules/deadline-preview` | Preview one deadline finding for `record_id`, `record_type`, `label`, `due_date` | Preview only |

## Partners
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/partners?q=` | List/search by name, category, owner | |
| POST | `/api/partners` | Create (201) | `source_label=user` |
| GET | `/api/partners/{partner_id}` | Detail | 404 if missing |
| PATCH | `/api/partners/{partner_id}` | Partial update; `null` clears optional fields | 422 if a required field is cleared |
| DELETE | `/api/partners/{partner_id}` | Delete (204) | **409** while agreements, projects, finance, reports, actions, or follow-ups reference it |

## Actions (tasks)
| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/api/actions?status=` | List, optional status filter | |
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
- Agreements: `expiry_date` ≥ `start_date` (422).
- Projects: `end_date` ≥ `start_date` (422); PATCH rejects unknown fields.
- Finance: `status` must be allowed for the `record_type` (`FINANCE_STATUSES` in `models.py`); default is the first allowed value.

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

## Common error responses
- `401` missing or invalid Firebase ID token (only when `REQUIRE_FIREBASE_AUTH=true`).
- `404` record not found. `409` delete blocked by linked records. `422` validation failure.
- `503` Firestore or Firebase Auth unavailable or misconfigured.
