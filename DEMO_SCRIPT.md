# Demo Script (3–4 minutes)

All records are fictional demo data (`source_label = "demo"`). Without Firebase credentials the backend runs in a labelled, non-persistent in-memory mode; restart it before a rehearsal to reset the scenario. Gemini is optional: without a key the AI panel states that AI was not used.

## Working now
1. **Dashboard** (`/dashboard`): open alerts, overdue items, MOUs expiring ≤ 30 days, open follow-ups — all derived from `/api/alerts`. Point out "rules evaluated <date>" and Today's 5.
2. **Open the top alert** (milestone overdue): show verified record facts vs computed values, the rule explanation, the priority breakdown (50 + 15 + 10), and the rule-based next step. Click "Ask Gemini" to show the honest AI status.
3. **Human decision:** create a follow-up task assigned to an owner; show the follow-ups KPI change. Dismiss another alert with a reason; show it leave the list.
4. **Partner 360** (`/partner-360`): profile, MOU timeline from real dates, the partner's open alerts together (cross-record context), linked records, activity history.
5. **Fix the record:** on Projects, mark the overdue milestone complete (completion date required) → back on the dashboard the alert is gone and counts update.
6. **Agreements:** expiry radar from the backend; set the expiring MOU's renewal to "Renewed" → the expiry alert clears.
7. **Import:** preview a CSV/XLSX through the backend; show validation issues and that nothing is written (confirmation arrives in Step 10).

## Planned (do not demo until built and verified)
- **Finance and Reports on live records** (Step 8d).
- **External partner submission** (Steps 8e–8f): manager requests a report from Partner 360 → copies the link → a separate browser session submits as the partner → the obligation shows "Received — awaiting review" → the manager accepts → the obligation and dashboard update and the decision appears in the activity history.
- **Grounded Gemini recommendations** (Step 9) and **confirmed import** (Step 10).
