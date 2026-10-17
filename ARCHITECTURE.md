# Architecture

Status key: **[current]** exists in the codebase today; **[planned]** approved in Step 2, not yet implemented.

## Overview
- **Frontend [current]:** React 18, TypeScript, Vite, React Router, Lucide, Firebase Web SDK (Auth only). Plain CSS design system in `frontend/src/index.css`.
- **Backend [current]:** FastAPI and Pydantic — the single backend (team decision, Step 2). Router in `app.routes` mounted at `/api` by `app.main`.
- **Persistence [current]:** Cloud Firestore through the Firebase Admin SDK in `app.repository`. Without credentials the backend logs a warning and uses an in-memory demo fallback that resets on restart and is reported as `demo-memory-fallback` by `/api/health`. Firestore operation failures raise `DataStoreUnavailable` → HTTP 503.
- **Authentication [current, partial]:** optional Firebase ID-token middleware (`REQUIRE_FIREBASE_AUTH`) using `app.auth.verify_token`; the Firebase Admin app is created once in `app.firebase_app` and shared with Firestore. Invalid token → 401; auth service unavailable → 503. **[planned]** role checks (admin / manager / viewer) via FastAPI dependencies, roles stored in `users`.
- **AI [current, partial]:** server-side Gemini via the async `google-genai` client with a timeout; failures return `ai_used=false` plus `ai_error` and are logged without request details. **[planned]** structured, validated, fact-grounded output and human review.
- **Import [current]:** CSV/XLSX/JSON preview only; never writes data.

## Request flow
```
React page → api client (adds Firebase ID token) → FastAPI route
  → services (rules.py, priority, intelligence.py)
  → repository.py (Firestore | labelled in-memory fallback)
  → typed JSON → page state (loading / empty / error / success)
```
The browser never reads Firestore directly: `firestore.rules` denies all client access. Authorization is enforced in FastAPI, never only by hiding UI. Gemini keys stay server-side.

## Data model
Existing collection names and fields are preserved; new fields are optional for backward compatibility.

| Collection | Status | Key fields |
|---|---|---|
| `partners` | current | name, category, contribution_types, status, owner, contacts, summary, source_label; **[planned]** relationship_types |
| `opportunities` | planned | partner_id, title, stage (identified → qualification → proposal → approval → agreement → active → renewal → closed), owner, next_step, next_step_date, updated_at |
| `agreements` | current | partner_id, title, reference_number, status, start_date, expiry_date, owner, document_url; **[planned]** project_id, opportunity_id, signed_copy, renewal_status |
| `projects` | current | partner_id, name, status, owner, start_date, end_date, milestone_summary |
| `milestones` | planned | project_id, partner_id, title, due_date, completed_date, status, owner |
| `finance` | current | partner_id, project_id, record_type (budget / fund_received / invoice / utilization_certificate), amount, currency, due_date, status (per-type allowed values, `FINANCE_STATUSES` in `models.py`); **[planned]** issue_date, received_date |
| `reports` | current | partner_id, project_id, report_type (monthly / quarterly / impact / other), due_date, submitted_date, status, owner |
| `actions` | current | title, priority, status, due_date, evidence, recommended_action, related_partner_id, owner; **[planned]** related_record, source_alert_id. Used as the task model |
| `followups` | current | legacy; overlaps `actions` (freeze proposed, pending team decision) |
| `alert_reviews` | planned | id = alert id; decision (acknowledged / deferred_until / dismissed + reason / task_created), reviewer, timestamp |
| `ai_recommendations` | planned | target, fact ids sent, validated output, model, review_status (pending / approved / edited / rejected), reviewer |
| `activities` | planned | entity_type, entity_id, partner_id, event, actor, timestamp, details (audit trail) |
| `users` | planned | uid, email, name, role |
| `config/rules` | planned | rule thresholds |

Every record carries `source_label` (`demo` or `user`). Demo records are fictional.

## Deterministic rules engine [planned]
`evaluate(records, config, today) → list[Alert]` — pure functions in `app/rules.py`; `today` computed in Asia/Kolkata.

- Alerts are **computed on read**, never stored. Stable id: `{rule_id}:{record_type}:{record_id}`. Only human decisions are persisted (`alert_reviews`). Fixing the underlying record makes the alert disappear.
- Each alert: rule_id, rule description, severity, record ref, partner, owner, due date, days remaining/overdue, evidence (field → value), why it matters, template action, priority score with breakdown.
- Rules: `MOU_EXPIRING`, `MOU_EXPIRED_NO_RENEWAL`, `MOU_SIGNED_COPY_MISSING`, `APPROVED_NO_MOU`, `MILESTONE_OVERDUE`/`_DUE_SOON`, `REPORT_OVERDUE`/`_DUE_SOON`, `UC_PENDING`, `INVOICE_OVERDUE` (due date present), `INVOICE_AGING` (no due date — described by age only), `TASK_OVERDUE`, `FOLLOWUP_STALE`, `DATA_MISSING` (material fields only).
- Priority score (illustrative business rule, not a prediction): rule base (overdue 50 / due soon 30 / data 15) + urgency (≤ 30) + cross-record (+10 when partner has ≥ 2 other open alerts) + recorded amount (+5).
- **Today's 5** = top five by score excluding deferred/dismissed; the full list is always available.

## AI [planned]
`POST /api/intelligence/analyze` keeps its contract and gains optional `alert_id` and `mode` (summary / recommendation / message draft).
1. Build a fact pack of relevant records and alerts, each fact with an id.
2. Gemini returns schema-constrained JSON: summary, observations with cited fact ids, suggested action, suggested priority, message draft, missing information.
3. Validate; reject citations to fact ids not supplied.
4. Run off the event loop with a timeout. Failure → `ai_used=false` plus reason; deterministic alerts unaffected.
5. Save as `pending` in `ai_recommendations`; human approves / edits / rejects; decision logged in `activities`.
Gemini never computes dates, scores, or amounts.

## Roles [planned]
Viewer: read. Manager: create/update, review recommendations, tasks. Admin: plus config, import, delete, roles. `REQUIRE_FIREBASE_AUTH=false` is local-only with a visible demo banner.

## Frontend [planned]
Typed API client per resource, `useResource` hook, shared `StatusBadge`, `DataTable`, `Dialog`, `EvidencePanel`, `AlertRow`, `PriorityBreakdown`. Pages: Dashboard (management overview + Today's 5), Action center (team workspace), Partners, Partner 360 (tabbed), Pipeline, Agreements, Projects, Finance, Reports, Import, Sign-in. Recharts and `motion` only when approved (Step 11).

## Routing
`backend/app/main.py` mounts `app.routes.router` at `/api`. `app.openapi()` is exercised in tests to detect missing or malformed route registration. Detail routes return 404 for missing IDs. `app/domain_routes.py` and `app/domain_store.py` are unmounted legacy SQLite code (removal proposed in Step 4f).
