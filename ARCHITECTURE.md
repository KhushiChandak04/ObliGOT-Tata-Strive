# Architecture

- **Frontend:** React 18, TypeScript, Vite, React Router, Firebase Web SDK.
- **Backend:** FastAPI and Pydantic; mounted in `app.main` with the application router under `/api`.
- **Persistence:** Cloud Firestore through Firebase Admin SDK in `app.repository`. If credentials are unavailable, the backend uses an in-memory demo fallback that resets on process restart. There is no SQLite storage.
- **Authentication:** Optional Firebase ID-token verification middleware. Keep disabled only for local/demo development; enable after configuring Firebase Auth and verifying the frontend token flow.
- **AI:** Server-side Gemini integration with a rules-first fallback.
- **Import:** CSV/XLSX preview and JSON-row validation only. Preview never writes data.

## Data collections
`partners`, `actions`, `followups`, `agreements`, `projects`, `finance`, and `reports`. Every record should be marked as `demo` or `user` so illustrative data is not mistaken for verified commitments.

## Routing
`backend/app/main.py` imports `router` from `app.routes` and mounts it at `/api`. `app.openapi()` is exercised in tests to detect missing or malformed route registration. Dynamic detail routes return 404 for missing IDs.
