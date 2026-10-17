# ObliGOT — Partnership Command Center

ObliGOT is a hackathon starter for partnership lifecycle visibility, obligations, reporting, financial tracking, and evidence-grounded AI recommendations.

**Direction (17 Oct 2026):** turn MOU and addendum PDFs into verified, Excel-ready records — page-level evidence, human approval, multi-sheet export — and run the deterministic alerts on approved records only. The data contract exists (`backend/app/documents.py`, `backend/app/workbook.py`, `docs/WORKBOOK_SCHEMA.md`); PDF upload with page-by-page inspection works through the API (`POST /api/documents`, private local storage, no OCR); Gemini extraction into evidence-checked proposals works through the API when `GEMINI_API_KEY` is set (not yet tested with a real key); review/approval, export, and the screens are **not built yet** (see `IMPLEMENTATION_PLAN.md`).

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
If you start Uvicorn from the repository root instead of `backend/` on Windows, use the backend virtual environment explicitly:
```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```
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
1. Select the existing Firebase project `obligot-95487` (the web app configuration is in the ignored local `frontend/.env`; do not commit it).
2. Enable Cloud Firestore in Native mode.
3. Enable Authentication providers you want to use (Email/Password and/or Google).
4. The Firebase Web App is already registered and linked to the Hosting site.
5. Set `FIREBASE_PROJECT_ID` in `backend/.env`.
6. For local backend Firestore access, put the service-account JSON at `backend/firebase-admin.json` (git-ignored) and set `FIREBASE_CREDENTIALS_FILE=firebase-admin.json` in `backend/.env` (relative paths resolve inside `backend/`; an absolute path also works). Never commit the file. Alternatively set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable — a value in `.env` alone is not seen by the Admin SDK.
7. Check: `GET /api/health` must report `"database": "firestore"`.
8. Load the fictional demo records once (optional; Firestore starts empty): `cd backend && python scripts/seed_demo.py`. It only adds records whose ID does not exist, so it never overwrites edits; dates are fixed at the time of seeding.
9. Sign-in: the workspace requires a Firebase user (email/password or Google) whenever the web config is present. Set `REQUIRE_FIREBASE_AUTH=true` in `backend/.env` so the API rejects requests without a valid ID token (401). The frontend attaches the signed-in user's token; the activity log records the user's email.

The Firebase Admin SDK uses Application Default Credentials in supported Google Cloud environments. Prefer attached service identity on Cloud Run instead of shipping service-account keys.

### Gemini
Set `GEMINI_API_KEY` in `backend/.env` or your hosting provider's secret manager. Never use `VITE_GEMINI_API_KEY`; Vite variables are exposed to the browser. When Gemini is absent or errors, the API returns a clear rules-first response with `ai_used=false` and a machine-readable `ai_error` (`not_configured`, `timeout`, `empty_response`, `api_error:<HTTP code>`, or `error:<type>`). `GEMINI_TIMEOUT_SECONDS` (default 20) bounds each request.

### Reading scanned MOUs: Gemini first, optional OCR fallback
- Gemini reads scanned pages from page images (keeps tables, stamps, Hindi/English) and extracts the agreement terms.
- If Gemini is unavailable, pages it could not read are read by **Tesseract OCR** when it is installed (plain text; tables may be flattened), then only labelled dates, references, and amounts are extracted by pattern matching. Everything is labelled with how it was read and goes through review.
- Install Tesseract (optional):
  - Windows: `winget install --id UB-Mannheim.TesseractOCR`, then add `C:\Program Files\Tesseract-OCR` to PATH (or set `TESSERACT_CMD` to the full path of `tesseract.exe`). For Hindi, tick "Hindi" under additional languages in the installer and set `OCR_LANGUAGES=eng+hin`.
  - Linux / Docker: `apt-get install tesseract-ocr tesseract-ocr-hin` (already in `backend/Dockerfile`).
- Check: `GET /api/health` → `"ocr_available": true`.
- Regional settings (defaults for Tata STRIVE's Indian agreements): `DEFAULT_CURRENCY=INR`, `DATE_ORDER=dmy` (numeric dates day-first), `NUMBER_DECIMAL_SEPARATOR=.`. Amounts in lakh/crore are kept as written, never converted; a symbol shared by several currencies (e.g. `$`) is flagged, not guessed.

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
- `GET /api/milestones?project_id=...&partner_id=...&status=...` / `POST /api/milestones` / `GET|PATCH|DELETE /api/milestones/{milestone_id}`
- `GET /api/opportunities?partner_id=...&stage=...` / `POST /api/opportunities` / `GET|PATCH|DELETE /api/opportunities/{opportunity_id}`
- `GET /api/followups?status=...&related_partner_id=...` / `POST /api/followups` / `GET|PATCH|DELETE /api/followups/{followup_id}`
- `GET /api/alerts?partner_id=...&level=...&category=...&include_reviewed=...` / `POST|DELETE /api/alerts/{alert_id}/review` / `POST /api/alerts/{alert_id}/task` / `GET /api/rules` / `GET|PATCH /api/rules/config`
- `GET /api/activities?partner_id=...&entity_id=...&limit=...`
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
