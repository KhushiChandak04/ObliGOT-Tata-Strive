"""Progress reports and utilization certificates: when each was due and when it was actually done.

Deterministic only. Each record gets a state from its own dates (no guessing): on time, late (done after the due
date), overdue (not done and past due), pending (not yet due), or no due date. Totals are given for the whole
organisation and per account owner, separately for reports and UCs.
"""
from datetime import date

from fastapi import APIRouter

from app.repository import list_records
from app.rules import business_today

router = APIRouter(tags=["reports"])


def _date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _row(kind: str, record: dict, done_field: str, today: date) -> dict:
    due, done = _date(record.get("due_date")), _date(record.get(done_field))
    if done and due:
        state, days = ("on_time" if done <= due else "late"), (done - due).days
    elif done:
        state, days = "done_no_due_date", None
    elif not due:
        state, days = "no_due_date", None
    elif due < today:
        state, days = "overdue", (today - due).days
    else:
        state, days = "pending", (due - today).days
    return {"id": record["id"], "kind": kind, "title": record.get("title"), "partner_id": record.get("partner_id"),
            "owner": record.get("owner") or "Unassigned", "due_date": due.isoformat() if due else None,
            "done_date": done.isoformat() if done else None, "state": state,
            # late: days after the due date it was done; overdue: days past due so far; pending: days left
            "days": days}


def _summary(rows: list[dict]) -> dict:
    count = lambda s: sum(r["state"] == s for r in rows)
    late = [r["days"] for r in rows if r["state"] == "late"]
    on_time, n_late = count("on_time"), len(late)
    return {"total": len(rows), "done": on_time + n_late + count("done_no_due_date"), "on_time": on_time, "late": n_late,
            "overdue": count("overdue"), "pending": count("pending"), "no_due_date": count("no_due_date"),
            "on_time_rate": round(100 * on_time / (on_time + n_late)) if on_time + n_late else None,
            "average_days_late": round(sum(late) / n_late, 1) if n_late else None}


@router.get("/compliance/timeliness")  # not under /reports: /reports/{report_id} would match first
def timeliness() -> dict:
    today = business_today()
    rows = [_row("report", r, "submitted_date", today) for r in list_records("reports")]
    rows += [_row("uc", f, "received_date", today) for f in list_records("finance") if f.get("record_type") == "utilization_certificate"]
    rows.sort(key=lambda r: (r["due_date"] or "9999", r["title"] or ""))
    owners = sorted({r["owner"] for r in rows}, key=str.lower)
    by_kind = lambda subset: {kind: _summary([r for r in subset if r["kind"] == kind]) for kind in ("report", "uc")}
    return {"as_of": today.isoformat(), "organisation": by_kind(rows),
            "owners": [{"owner": o, **by_kind([r for r in rows if r["owner"] == o])} for o in owners], "rows": rows}
