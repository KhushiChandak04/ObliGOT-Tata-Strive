---
name: demo-check
description: Verify the complete ObliGOT demonstration workflow end to end (partners, MOUs, obligations, alerts, AI recommendations, human review, tasks, dashboard updates, persistence, import), report passed/failed/blocked/untested honestly, and prepare a 3–4 minute walkthrough.
argument-hint: <optional focus>
---

# Demo check: $ARGUMENTS

## 1. Inspect
- Read `CLAUDE.md`, `IMPLEMENTATION_PLAN.md`, `DEMO_SCRIPT.md`, `frontend/package.json` scripts, `backend/pytest.ini`, routes, and Firebase config.
- Check `GET /api/health`: storage mode (`firestore` vs `demo-memory-fallback`), `ai_configured`, `auth_required`. Persistence claims require `firestore`.

## 2. Automated checks
- `cd backend && python -m pytest -q`
- `cd frontend && npm run build`
- Any lint/type-check/test scripts present.

## 3. Scenario checks (record result for each)
- **A MOU expiry:** active MOU near expiry → `MOU_EXPIRING` with real dates as evidence; mark renewed → alert gone after re-evaluation.
- **B Overdue report:** pending report past due → `REPORT_OVERDUE`, high priority, follow-up offered; submit → alert gone.
- **C AI:** recommendation cites only supplied facts, separates facts from suggestions, no invented data. Simulate AI failure → `ai_used=false` with reason, deterministic alerts still shown, no fake success.
- **D Human action:** approve/edit/reject recommendation, create and assign task, complete it → status persists after reload, activity recorded, dashboard updates.
- **E Missing data:** incomplete record → `DATA_MISSING`, nothing invented.
- **F Finance:** invoice/receipt values correct; invoice without due date described by age; no cross-currency or cross-type totals.
- **G Dashboard consistency:** change a record → metrics change; verify every metric traces to stored records (no hard-coded numbers).
- **H Import (if implemented):** preview non-destructive, warnings shown, confirmed save only.
- Partner 360 sections, Today's 5, management vs team views, loading/empty/error states, no dead buttons or navigation, console free of errors.
- Persistence across reload and a fresh browser session; auth/role restrictions if enabled.

## 4. Fix policy
Fix only safe, clearly scoped blockers, re-run the affected checks, and list each fix. Never fake an integration, stub an AI response as real, or hard-code results to pass a check.

## 5. Report
Separate lists: **Passed**, **Failed**, **Blocked** (with cause, e.g. missing credentials), **Untested**. Never claim the product is fully tested or deployed without evidence.

## 6. Demo walkthrough
Update `DEMO_SCRIPT.md` with a 3–4 minute sequence using only verified features: dashboard → partner directory → Partner 360 → alert + evidence → AI recommendation → review + task → updated dashboard → (import) → management view and impact. Label demo data as fictional and include a tested fallback for AI/network failure. **Stop for approval.**
