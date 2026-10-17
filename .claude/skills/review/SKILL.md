---
name: review
description: Review the current ObliGOT changes for verified defects (correctness, security, authorization, date handling, data integrity, AI grounding, API contracts, accessibility, responsiveness), fix safe scoped issues, and report check results honestly.
argument-hint: <optional focus area>
---

# Review: $ARGUMENTS

## 1. Establish scope
- Run `git status` and `git diff` (and `git diff --staged`). Identify what changed and what is unrelated.
- Never discard, stash, reset, or overwrite uncommitted or unrelated work.

## 2. Review checklist
- **Correctness:** logic errors, wrong status filters, unhandled None/empty values, off-by-one.
- **Dates:** date-only vs datetime parsing, timezone (Asia/Kolkata "today"), inclusive/exclusive thresholds, overdue vs due-soon boundaries, invoices without due dates described by age.
- **Data integrity:** referential checks, orphaned records, enum validation, start ≤ end, no silent overwrites, no sums across currencies or record types.
- **Fake data:** hard-coded metrics, alerts, or AI responses presented as live.
- **Security/authorization:** secrets in frontend or repo, auth bypass, role checks enforced server-side, input validation, error messages leaking internals.
- **AI grounding:** only supplied facts sent and cited, output validated, failures return `ai_used=false` with reason, deterministic alerts preserved.
- **API contracts:** frontend types and calls match backend paths, methods, request/response fields, and status codes.
- **UX:** loading/empty/error/success states, dead buttons, keyboard access, focus states, contrast, mobile layout.

## 3. Classify findings
Report only verified defects (reproduced or proven from code), ranked Critical → High → Medium → Low, each with file:line, evidence, and impact. Label anything unproven as "suspected" — do not present speculation as fact.

## 4. Fix
- Fix safe, clearly scoped issues and add a regression test where practical.
- Ask before destructive changes, broad rewrites, dependency changes, or API contract changes.

## 5. Run checks
- `cd backend && python -m pytest -q`
- `cd frontend && npm run build` (type-check + build) if dependencies are installed
- Any lint/test scripts that exist.
Report each command and its actual result. If a check could not run, say so and why. Never claim an unrun check passed.

## 6. Report and stop
Findings (fixed / not fixed / needs decision), checks run, remaining risks. Update `IMPLEMENTATION_PLAN.md`. **Stop for approval.**
