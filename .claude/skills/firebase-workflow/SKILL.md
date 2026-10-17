---
name: firebase-workflow
description: Implement or change ObliGOT Firebase work — Firestore data access through the FastAPI repository, Firebase Auth token verification, roles, security rules, and Firebase console setup — without weakening security. Use for any Firestore, Auth, rules, or Firebase config task.
argument-hint: <firebase task>
---

# Firebase workflow: $ARGUMENTS

## 1. Inspect current configuration
- Read `.firebaserc`, `firebase.json`, `firestore.rules`, `firestore.indexes.json`, `backend/app/repository.py`, `backend/app/config.py`, `backend/app/main.py` (auth middleware), `frontend/src/lib/firebase.ts`, and both `.env.example` files.
- Check which services are actually configured (project ID, web config, credentials). Do not read or print secret values; only check presence.
- Preserve the existing Firebase project and collection names. No migrations unless approved.

## 2. Access model (keep it)
- Browser uses Firebase Auth only. All Firestore reads/writes go through FastAPI with the Admin SDK. `firestore.rules` stays deny-all for clients unless the team approves client access, in which case write explicit auth + role rules.
- FastAPI verifies Firebase ID tokens (ensure `firebase_admin` app is initialized before `verify_id_token`). Roles (`admin`, `manager`, `viewer`) come from the `users` collection and are enforced with route dependencies — never only by hiding UI controls.
- `REQUIRE_FIREBASE_AUTH=false` is local-only and must be visibly labelled.

## 3. Data access
- Use typed Pydantic models, stable document IDs, and explicit references (`partner_id`, `project_id`, ...). Keep partners, agreements, projects, milestones, finance records, reports, and actions distinct.
- Go through `repository.py` functions; add filtered queries (`where`) instead of streaming whole collections where it matters.
- Add needed composite indexes to `firestore.indexes.json`.
- Map Firestore/network/permission failures to clear HTTP errors (e.g. 503) — never silently fall back or return fake success. The in-memory fallback must stay clearly labelled as non-persistent.
- Frontend must show loading and error states for every Firestore-backed request.

## 4. Secrets
- Gemini keys and service-account credentials live only in backend env/secret manager. Never use `VITE_` variables for secrets. Never commit `.env` or credential JSON.

## 5. Verify
- Run backend tests (`cd backend && python -m pytest -q`). Test authorized, unauthorized (401), forbidden (403), not-found, and validation cases.
- If live Firestore is unavailable, say so and mark live behaviour as untested.
- Never weaken rules or auth to make a demo work.

## 6. Report and stop
List console steps a human must perform (enable providers, create service account, set env vars). Update `README.md`/`IMPLEMENTATION_PLAN.md`. Send the checkpoint report and **stop for approval**.
