---
name: build-feature
description: Implement one ObliGOT feature end to end (UI, FastAPI route, business logic, persistence, validation, states) within the approved step, then stop for review. Use when asked to build or complete a workflow or feature.
argument-hint: <feature description>
---

# Build feature: $ARGUMENTS

## 1. Inspect first
- Read `CLAUDE.md`, `ARCHITECTURE.md`, and the current step in `IMPLEMENTATION_PLAN.md`.
- Run `git status`; note uncommitted or unrelated changes and leave them untouched.
- Read the relevant models (`backend/app/models.py`), routes (`backend/app/routes.py`), rules/services, repository functions, frontend pages, components, types, and the API client.
- Confirm the feature is within the approved scope. If it is not, stop and ask.

## 2. Explain the plan before editing
State: scope, affected routes/collections/pages, any API contract change (needs explicit approval), new dependencies (needs approval), and how you will verify it.

## 3. Implement the complete workflow
- Backend: Pydantic models with real validation (enums, date order, required fields) → route with correct method and status codes (201/204/404/409/422) → deterministic logic in small pure functions → repository access → activity record for important state changes.
- Frontend: typed API function → page/component reusing existing components and CSS classes → loading, empty, error, and success states → refresh dependent data (e.g. dashboard metrics) after mutations.
- Reuse existing routes, components, and business rules; do not duplicate rule logic in the frontend.
- No hard-coded data in components, no fake metrics, no placeholder buttons, no fake success on failure.
- Demo data must be fictional and labelled `source_label="demo"`.
- Preserve existing behaviour and backward-compatible contracts.

## 4. Verify
- Add or update pytest tests for the logic and routes (fixed `today` for date rules).
- Run `cd backend && python -m pytest -q`; run `cd frontend && npm run build` when frontend code changed.
- Exercise the workflow manually where practical (API calls or running app). Report exact commands and real output. Never claim an unrun check passed.

## 5. Report and stop
Use the checkpoint format in `CLAUDE.md`: changed files, verified behaviour, API/data impact, remaining limitations and risks, next proposed step. Update `IMPLEMENTATION_PLAN.md`. Then **stop and wait for explicit approval**.
