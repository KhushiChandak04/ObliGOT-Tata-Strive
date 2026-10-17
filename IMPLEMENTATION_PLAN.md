# Implementation Plan

## Current status
- [x] FastAPI app router mounted under `/api` and OpenAPI contract test added.
- [x] Project GET/PATCH/DELETE endpoints added and covered by CRUD tests.
- [x] Agreement, finance, report, action, and follow-up item retrieval/deletion endpoints added; typed updates added for agreement/finance/report.
- [x] Import preview supports JSON row validation and CSV/XLSX upload preview without committing records.
- [x] Removed unused SQLite-backed legacy domain store/routes; Firestore remains the persistent-store path.
- [x] Backend tests pass in the build environment.
- [ ] Configure Firebase project credentials and verify live Firestore writes in the target environment.
- [ ] Install frontend dependencies and run the production TypeScript/Vite build in a network-enabled environment.
- [ ] Replace remaining frontend scaffold pages with connected CRUD screens before operational use.

## Acceptance checks
1. `cd backend && python -m pytest -v tests` passes.
2. `GET /api/health` responds with status `ok`.
3. OpenAPI lists all registered endpoints, including project detail CRUD and import preview.
4. Import preview never commits records.
5. No SQLite persistence is used. Without Firestore credentials, data uses an explicitly labelled in-memory demo fallback.
