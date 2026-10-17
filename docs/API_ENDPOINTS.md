# ObliGOT API endpoint inventory

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | API, AI, auth, and storage-mode status |
| GET | `/api/dashboard` | Derived metrics and deterministic deadline findings |
| GET/POST | `/api/partners` | Search/list and create partners |
| GET/PATCH/DELETE | `/api/partners/{partner_id}` | Partner detail, update, delete |
| GET/POST | `/api/actions` | List and create action items |
| PATCH | `/api/actions/{action_id}` | Update status, owner, priority, or due date |
| GET/POST | `/api/agreements` | List/create agreements |
| GET/POST | `/api/projects` | List/create projects |
| GET/POST | `/api/finance` | List/create finance records |
| GET/POST | `/api/reports` | List/create reporting obligations |
| POST | `/api/intelligence/analyze` | Gemini analysis or explicit rules-first fallback |
| POST | `/api/followups` | Create follow-up |
| PATCH | `/api/followups/{followup_id}` | Update follow-up status |
| GET | `/api/rules/deadline-preview` | Preview one deterministic due-date rule |
| POST | `/api/import/preview` | Preview CSV/XLSX data without importing |

Interactive schema: `/docs` while the backend is running.
