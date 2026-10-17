# ObliGOT — Claude Code project guide

ObliGOT is an AI-assisted partnership management system for Tata STRIVE Code Odyssey 5.0 (30-hour hackathon). It consolidates partners, pipeline, MOUs, projects, finance, reporting obligations, and follow-ups, and explains what needs attention, why, and what to do next.

## Working protocol (non-negotiable)
- Work only on the currently approved step (see `IMPLEMENTATION_PLAN.md`). After every step, send a checkpoint report and **stop for explicit approval**. Silence is not approval.
- Checkpoint report: step completed, what changed, verification (exact commands + real results), API/data impact, review notes, open issues, next proposed step, approval request.
- Inspect existing code before changing it. Make the smallest safe change. Never claim an unrun check passed or an untested feature works.
- Changing a public route or its request/response contract needs explicit approval first (explain problem, callers, compatibility).
- Git: no commits, pushes, resets, rebases, or history rewrites without explicit instruction. Preserve teammates' work.
- **Never list Claude, Anthropic, or any AI as author, co-author, or contributor** — no `Co-Authored-By` trailers, credits, or file headers.
- Never commit `.env` files, service-account JSON, or API keys.

## Stack and layout
- `frontend/` — React 18, Vite 5, TypeScript, React Router, Lucide, Firebase Web SDK (Auth only). Plain CSS in `src/index.css`. API client in `src/services/functions.service.ts`.
- `backend/` — FastAPI + Pydantic (the **only** backend). Routes in `app/routes.py` mounted at `/api`; models in `app/models.py`; persistence in `app/repository.py` (Firestore via Admin SDK, or labelled in-memory fallback); rules in `app/rules.py`; Gemini in `app/intelligence.py`.
- Firestore client access is denied (`firestore.rules`); all reads/writes go through FastAPI. Authorization is enforced in FastAPI, not by hiding UI.

## Commands
- Backend tests: `cd backend && python -m pytest -q`
- Backend dev: `cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` (docs at `/docs`)
- Frontend: `cd frontend && npm install && npm run dev` / `npm run build`
- Ad-hoc Python scripts: run with `python -I` and insert `backend/` into `sys.path` — another project's `app` package can shadow imports on this machine.

## Domain rules
- Deterministic code owns dates, deadlines, status evaluation, arithmetic, scoring, and alert creation/resolution. Gemini only summarizes, explains, recommends, and drafts — grounded in supplied fact IDs, validated, and reviewed by a human.
- Alerts are computed from current records with stable IDs `{rule_id}:{record_type}:{record_id}`; only human review decisions are persisted. "Today" uses Asia/Kolkata.
- Every alert shows: issue → evidence (actual fields/values) → why it matters → priority (with breakdown) → recommended action → owner → due date.
- Never fabricate metrics, dates, amounts, commitments, or AI success. AI failure returns `ai_used=false` with a reason and keeps deterministic alerts.
- Keep invoices, UCs, receipts, budgets, milestones, and reporting deadlines distinct. Never sum amounts across currencies or record types. An invoice without a due date is described by age, not called overdue.
- Demo data is fictional and labelled `source_label="demo"`; never attach invented obligations to real organizations.
- Every page needs loading, empty, error, and success states. No placeholder buttons or dead controls.

## Project skills
`/build-feature`, `/firebase-workflow`, `/review`, `/ui-polish`, `/motion`, `/data-import`, `/demo-check` — in `.claude/skills/`.

## Docs to keep current
`IMPLEMENTATION_PLAN.md` (progress, decisions, tests, blockers), `ARCHITECTURE.md`, `README.md`, `DEMO_SCRIPT.md`, `docs/API_ENDPOINTS.md`. Record only decisions the team actually made.
