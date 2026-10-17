# ObliGOT — VS Code setup (Windows)

## Prerequisites
- VS Code
- Node.js LTS (includes npm)
- Python 3.12 recommended (3.10+ supported by the README)
- A terminal in VS Code (PowerShell is fine)

## 1. Open the workspace
Extract the ZIP, then open the `ObliGOT` folder in VS Code. You can also open `ObliGOT.code-workspace`.

## 2. Frontend terminal
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```
Open the local URL printed by Vite, normally `http://127.0.0.1:5173`.

## 3. Backend terminal
Open a second VS Code terminal:
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
If PowerShell blocks activation, use this for the current terminal only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
Check `http://127.0.0.1:8000/api/health` and API docs at `http://127.0.0.1:8000/docs`.

## 4. Configure Firebase and Gemini
- Fill `frontend/.env` with Firebase Web App values. Use only Firebase web configuration values there.
- Fill `backend/.env` with the Firebase project ID and optional `GEMINI_API_KEY`.
- For local Firestore access, configure Application Default Credentials or set `GOOGLE_APPLICATION_CREDENTIALS` to the absolute path of a service-account JSON file stored outside this repository.
- Do not commit `.env` files, service-account JSON, or API keys.
- The backend may use in-memory illustrative demo data if Firestore credentials are unavailable. This is not persistent storage.
- Keep `REQUIRE_FIREBASE_AUTH=false` only for local initial smoke testing. Enable it after sign-in and token forwarding are configured and verified.

## 5. VS Code shortcuts
- `Terminal > Run Task...` to run the included project tasks.
- `Run and Debug` > `ObliGOT: Debug FastAPI` to debug the backend.
- Use separate terminals for frontend and backend.

## 6. First verification
1. Frontend loads without a Vite error.
2. Backend health endpoint returns a healthy response.
3. Open `/docs` and try `GET /api/dashboard`.
4. Sign in only after Firebase web configuration is complete.
5. Test a create/update flow and confirm the backend is using Firestore before treating data as persistent.
