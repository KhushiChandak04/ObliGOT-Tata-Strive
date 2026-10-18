"""Portfolio at a glance: every signed MOU summarised, monthly cashflow, and how each funder is being serviced.

Deterministic arithmetic over current records only. Amounts are kept per currency and never converted or summed
across currencies; expected money comes from approved payment terms with a due date, received money from
recorded fund receipts. Nothing is estimated.
"""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter

from app.repository import list_records
from app.rules import business_today

router = APIRouter(tags=["dashboard"])

DONE_REPORT = {"submitted", "accepted"}
DONE_UC = {"submitted", "accepted"}


def _date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _add(money: dict, currency: str | None, amount) -> None:
    if amount is not None and currency:
        money[currency] = round(money.get(currency, 0) + float(amount), 2)


def _count(rows: list[dict], done, today: date) -> dict:
    finished = [r for r in rows if done(r)]
    overdue = [r for r in rows if not done(r) and _date(r.get("due_date")) and _date(r.get("due_date")) < today]
    return {"total": len(rows), "done": len(finished), "overdue": len(overdue),
            "no_evidence": sum(1 for r in finished if not (r.get("evidence") or "").strip())}


@router.get("/portfolio")
def portfolio() -> dict:
    today = business_today()
    partners = {p["id"]: p for p in list_records("partners")}
    reports, finance, milestones = list_records("reports"), list_records("finance"), list_records("milestones")
    terms = [t for t in list_records("financial_terms") if t.get("review_state") == "approved"]
    report_done = lambda r: r.get("status") in DONE_REPORT or bool(r.get("submitted_date"))
    uc_done = lambda f: f.get("status") in DONE_UC or bool(f.get("received_date"))
    milestone_done = lambda m: m.get("status") == "completed"

    mous = []
    for a in list_records("agreements"):
        project_id, partner = a.get("project_id"), partners.get(a.get("partner_id"), {})
        mine = lambda rows: [r for r in rows if project_id and r.get("project_id") == project_id]
        ucs = [f for f in mine(finance) if f.get("record_type") == "utilization_certificate"]
        committed, received = {}, {}
        for f in mine(finance):
            if f.get("record_type") == "budget":
                _add(committed, f.get("currency"), f.get("amount"))
            elif f.get("record_type") == "fund_received" and f.get("status") != "cancelled":
                _add(received, f.get("currency"), f.get("amount"))
        upcoming = [(d, kind, r.get("title") or r.get("description")) for kind, rows, done in (
            ("Report", mine(reports), report_done), ("UC", ucs, uc_done), ("Milestone", mine(milestones), milestone_done))
            for r in rows if not done(r) and (d := _date(r.get("due_date"))) and d >= today]
        upcoming += [(d, "Fund release", t.get("description")) for t in terms
                     if t.get("agreement_id") == a["id"] and t.get("term_type") in ("tranche", "payment_term")
                     and (d := _date(t.get("due_date"))) and d >= today]
        upcoming.sort(key=lambda x: x[0])
        mous.append({
            "agreement_id": a["id"], "project_id": project_id, "partner_id": a.get("partner_id"),
            "partner_name": partner.get("name"), "tier": partner.get("tier"), "group": partner.get("group"),
            "location": partner.get("location"), "title": a.get("title"), "status": a.get("status"),
            "start_date": a.get("start_date"), "expiry_date": a.get("expiry_date"), "owner": a.get("owner"),
            "source_document_id": a.get("source_document_id"), "committed": committed, "received": received,
            "reports": _count(mine(reports), report_done, today), "ucs": _count(ucs, uc_done, today),
            "milestones": _count(mine(milestones), milestone_done, today),
            "next_deadline": {"date": upcoming[0][0].isoformat(), "kind": upcoming[0][1], "title": upcoming[0][2]} if upcoming else None,
        })
    mous.sort(key=lambda m: (m["partner_name"] or "").lower())

    # Monthly cashflow: expected (dated payment terms) vs received (recorded receipts), per currency.
    flow: dict[tuple[str, str], dict] = defaultdict(lambda: {"expected": 0.0, "received": 0.0})
    unscheduled: dict[str, float] = {}
    for t in terms:
        if t.get("term_type") not in ("tranche", "payment_term") or t.get("amount") is None or not t.get("currency"):
            continue
        due = _date(t.get("due_date"))
        if due:
            flow[(due.strftime("%Y-%m"), t["currency"])]["expected"] += float(t["amount"])
        else:
            _add(unscheduled, t["currency"], t["amount"])
    for f in finance:
        got = _date(f.get("received_date"))
        if f.get("record_type") == "fund_received" and got and f.get("amount") is not None and f.get("currency") and f.get("status") != "cancelled":
            flow[(got.strftime("%Y-%m"), f["currency"])]["received"] += float(f["amount"])
    cashflow = [{"month": month, "currency": currency, "expected": round(v["expected"], 2), "received": round(v["received"], 2)}
                for (month, currency), v in sorted(flow.items())]

    # Funder servicing: the MOU rows rolled up per partner.
    funders: dict[str, dict] = {}
    for m in mous:
        f = funders.setdefault(m["partner_id"], {
            "partner_id": m["partner_id"], "partner_name": m["partner_name"], "tier": m["tier"], "group": m["group"],
            "location": m["location"], "mous": 0, "committed": {}, "received": {},
            **{k: {"total": 0, "done": 0, "overdue": 0, "no_evidence": 0} for k in ("reports", "ucs", "milestones")}})
        f["mous"] += 1
        for key in ("committed", "received"):
            for currency, amount in m[key].items():
                _add(f[key], currency, amount)
        for key in ("reports", "ucs", "milestones"):
            for k, v in m[key].items():
                f[key][k] += v
    return {"as_of": today.isoformat(), "mous": mous, "cashflow": cashflow, "unscheduled_expected": unscheduled,
            "funders": sorted(funders.values(), key=lambda f: (f["partner_name"] or "").lower())}
