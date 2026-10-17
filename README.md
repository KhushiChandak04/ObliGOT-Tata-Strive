# ObliGOT — Partnership Command Center

ObliGOT is a hackathon starter for partnership lifecycle visibility, obligations, reporting, financial tracking, and evidence-grounded AI recommendations.

## Stack
- Frontend: React, Vite, TypeScript, React Router, Lucide
- Authentication: Firebase Authentication starter (email/password and Google popup)
- Persistence: Cloud Firestore through Firebase Admin SDK in FastAPI
- Backend: FastAPI + Pydantic
- AI: Gemini via a server-side API key, with an explicit non-AI fallback
- Hosting: Firebase Hosting for frontend; deploy FastAPI separately (Cloud Run or another Python host)

**No SQLite database is used.** If Firestore credentials are not configured, the backend intentionally falls back to in-memory demo records for local development. This fallback resets when the server restarts and is not persistent.

## Local setup

### 1. Backend
Python 3.10+ (Python 3.12 recommended):
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
On Windows, copy `.env.example` to `.env` manually if `cp` is unavailable.
- API root: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

### 2. Frontend
In another terminal:
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open http://127.0.0.1:5173.

### 3. Configure Firebase
1. Create/select your Firebase project.
2. Enable Cloud Firestore in Native mode.
3. Enable Authentication providers you want to use (Email/Password and/or Google).
4. Add a Firebase Web App and copy its public web config into `frontend/.env`.
5. Set `FIREBASE_PROJECT_ID` in `backend/.env`.
6. For local backend Firestore access, create a service account and store its JSON **outside the repository**. Set `GOOGLE_APPLICATION_CREDENTIALS` to its absolute path. Never commit the file.
7. To require verified Firebase ID tokens on API calls, set `REQUIRE_FIREBASE_AUTH=true` in `backend/.env`. The frontend API client attaches the current user's ID token when signed in. Do not enable this until you have tested sign-in and backend credentials.

The Firebase Admin SDK uses Application Default Credentials in supported Google Cloud environments. Prefer attached service identity on Cloud Run instead of shipping service-account keys.

### Gemini
Set `GEMINI_API_KEY` in `backend/.env` or your hosting provider's secret manager. Never use `VITE_GEMINI_API_KEY`; Vite variables are exposed to the browser. When Gemini is absent or errors, the API returns a clear rules-first response with `ai_used=false` and a machine-readable `ai_error` (`not_configured`, `timeout`, `empty_response`, `api_error:<HTTP code>`, or `error:<type>`). `GEMINI_TIMEOUT_SECONDS` (default 20) bounds each request.

## API endpoints
- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/partners?q=...`
- `POST /api/partners`
- `GET /api/partners/{partner_id}`
- `PATCH /api/partners/{partner_id}`
- `DELETE /api/partners/{partner_id}` (409 while agreements, projects, finance, reports, actions, or follow-ups still reference the partner)
- `GET /api/actions?status=...&related_partner_id=...` / `POST /api/actions`
- `GET /api/actions/{action_id}` / `PATCH /api/actions/{action_id}` / `DELETE /api/actions/{action_id}`
- `GET /api/agreements?partner_id=...` / `POST /api/agreements` / `GET|PATCH|DELETE /api/agreements/{agreement_id}`
- `GET /api/projects?partner_id=...` / `POST /api/projects` / `GET|PATCH|DELETE /api/projects/{project_id}`
- `GET /api/finance?partner_id=...` / `POST /api/finance` / `GET|PATCH|DELETE /api/finance/{finance_id}`
- `GET /api/reports?partner_id=...` / `POST /api/reports` / `GET|PATCH|DELETE /api/reports/{report_id}`
- `POST /api/intelligence/analyze`
- `GET /api/opportunities?partner_id=...&stage=...` / `POST /api/opportunities` / `GET|PATCH|DELETE /api/opportunities/{opportunity_id}`
- `GET /api/followups?status=...&related_partner_id=...` / `POST /api/followups` / `GET|PATCH|DELETE /api/followups/{followup_id}`
- `GET /api/rules/deadline-preview`
- `POST /api/import/preview` (CSV/XLSX preview only; does not write records)

## Error responses
- `401` missing/invalid Firebase ID token (only when `REQUIRE_FIREBASE_AUTH=true`).
- `503` Firestore or Firebase Auth unavailable/misconfigured — never reported as success or as an invalid token.
- `409` delete blocked by linked records; `404` missing record; `422` validation failure.

## Tests
```bash
cd backend
pip install -r requirements.txt
pytest
```

## Deploy
### Frontend on Firebase Hosting
From repo root:
```bash
npm install -g firebase-tools
cd frontend && npm install && npm run build && cd ..
firebase login
firebase use --add
firebase deploy --only hosting
```
Set frontend environment values before building; Vite embeds them into the generated bundle.

### Backend on Cloud Run
Build/deploy from the `backend` directory using your selected Google Cloud project and region. Configure environment variables and secrets in the service configuration, allow HTTPS traffic, and use a service identity with only the required Firestore permissions. Set `CORS_ORIGINS` to a JSON array containing your actual deployed frontend origin, for example `[\"https://your-app.web.app\"]`. Keep `REQUIRE_FIREBASE_AUTH=true` for a public service after validating the sign-in flow.

## Current limits and safety
- This is a starter, not a finished production system.
- Demo records are explicitly illustrative. Do not present them as verified partner commitments.
- Firestore is used when credentials are available; otherwise the in-memory fallback is not persistent.
- CSV/XLSX import is preview-only, deliberately not an unsafe bulk write.
- Several frontend modules remain UI scaffolds; the API has more initial CRUD coverage than the UI.
- Before handling real data, test authorization, data ownership/tenant boundaries, backup/restore, validation, error handling, and deployment settings.
