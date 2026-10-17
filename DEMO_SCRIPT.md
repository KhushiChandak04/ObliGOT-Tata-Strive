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
- **Core story (P2–P6), synthetic MOU only:** upload a labelled synthetic MOU PDF → page-by-page extraction status → review fields and clauses with page and quote → correct one value, approve → export the multi-sheet workbook → the approved MOU's expiry/reporting dates raise a deterministic alert on the dashboard.
- **Addendum (P4):** upload a synthetic addendum → choose the MOU it amends → old vs proposed values with evidence → approve → effective view updates while the original and history stay visible.
- **Finance and Reports on live records** (P6) and **grounded Gemini explanations** (P7).
