"""Portfolio at a glance: every signed MOU summarised, monthly cashflow, and how each funder is being serviced.

Deterministic arithmetic over current records only. Amounts are kept per currency and never converted or summed
across currencies; expected money comes from approved payment terms with a due date, received money from
recorded fund receipts. Nothing is estimated.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta

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
        if not committed and a.get("total_budget") is not None and a.get("budget_currency"):
            _add(committed, a["budget_currency"], a["total_budget"])  # stated on the MOU record itself
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
            "programme_type": a.get("programme_type"), "total_target": a.get("total_target"),
            "signed_copy": a.get("signed_copy"),
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
            "funders": sorted(funders.values(), key=lambda f: (f["partner_name"] or "").lower()),
            "overview": _overview(today, mous, partners)}


OPEN_DEAL_STAGES = {"identified", "qualification", "proposal", "approval", "agreement", "renewal"}


def _overview(today: date, mous: list[dict], partners: dict[str, dict]) -> dict:
    """Manager's portfolio view: counts and per-currency totals only, all computed from the records."""
    projects = list_records("projects")
    active = [m for m in mous if m["status"] == "active"]
    soon = today + timedelta(days=90)
    committed, received, pipeline = {}, {}, {}
    for m in mous:
        for currency, amount in m["committed"].items():
            _add(committed, currency, amount)
        for currency, amount in m["received"].items():
            _add(received, currency, amount)
    deals = [o for o in list_records("opportunities") if o.get("stage") in OPEN_DEAL_STAGES]
    for o in deals:
        _add(pipeline, o.get("currency"), o.get("amount"))
    targets: dict[str, float] = {}
    for s in list_records("programme_scope"):
        if s.get("review_state") == "approved" and s.get("target_value") is not None:
            unit = s.get("target_unit") or s.get("value") or "target"
            targets[unit] = targets.get(unit, 0) + float(s["target_value"])
    stated = sum(float(m["total_target"]) for m in mous if m.get("total_target") is not None)
    total = lambda key, field: sum(m[key][field] for m in mous)
    top = lambda counter, n=6: [{"label": k, "count": v} for k, v in counter.most_common(n)]
    return {
        "projects": {"total": len(projects), "ongoing": sum(p.get("status") == "active" for p in projects),
                     "by_status": top(Counter(p.get("status") or "unknown" for p in projects), 10)},
        "mous": {"total": len(mous), "active": len(active),
                 "expiring_90d": sum(1 for m in active if _date(m["expiry_date"]) and today <= _date(m["expiry_date"]) <= soon),
                 "expired": sum(m["status"] == "expired" for m in mous),
                 "signed_copy_pending": sum(1 for m in active if m.get("signed_copy") != "received"),
                 "by_type": top(Counter(m.get("programme_type") or "Not specified" for m in mous)),
                 "by_group": top(Counter(m.get("group") or "not_set" for m in mous)),
                 "by_location": top(Counter(m.get("location") or "Not recorded" for m in mous))},
        "partners": {"total": len(partners), "by_tier": top(Counter(p.get("tier") or "not_set" for p in partners.values()))},
        "money": {"committed": committed, "received": received, "pipeline_open": pipeline, "open_deals": len(deals)},
        "targets": {"stated_on_mous": stated, "from_extracted_mous": targets},
        "reporting": {"reports_total": total("reports", "total"), "reports_done": total("reports", "done"),
                      "reports_overdue": total("reports", "overdue"), "ucs_total": total("ucs", "total"),
                      "ucs_done": total("ucs", "done"), "ucs_overdue": total("ucs", "overdue")},
    }


CONSOLIDATED_HEADERS = [
    "Funder", "Tier", "Group", "Location", "MOU", "Programme type", "Status", "Start date", "End date", "Signed copy",
    "Committed", "Received", "Total target", "Reports done", "Reports total", "Reports overdue", "UCs done", "UCs total",
    "UCs overdue", "Deliverables done", "Deliverables total", "Next due date", "Next due item",
]


def consolidated_rows() -> tuple[list[list], list[list]]:
    """Rows for the "All_MOUs" sheet appended to every exported workbook, then a totals block (per currency)."""
    data = portfolio()
    money = lambda m: "; ".join(f"{c} {v:,.2f}" for c, v in m.items()) or None
    rows = [[m["partner_name"], m["tier"], m["group"], m["location"], m["title"], m.get("programme_type"), m["status"],
             m["start_date"], m["expiry_date"], m.get("signed_copy"), money(m["committed"]), money(m["received"]),
             m.get("total_target"), m["reports"]["done"], m["reports"]["total"], m["reports"]["overdue"], m["ucs"]["done"],
             m["ucs"]["total"], m["ucs"]["overdue"], m["milestones"]["done"], m["milestones"]["total"],
             (m["next_deadline"] or {}).get("date"), (m["next_deadline"] or {}).get("title")] for m in data["mous"]]
    o = data["overview"]
    totals = [["TOTALS (all MOUs in ObliGOT)"], ["MOUs", o["mous"]["total"]], ["Active MOUs", o["mous"]["active"]],
              ["Expiring within 90 days", o["mous"]["expiring_90d"]], ["Expired", o["mous"]["expired"]],
              ["Signed copy not received (active)", o["mous"]["signed_copy_pending"]]]
    totals += [[f"Committed ({c})", v] for c, v in o["money"]["committed"].items()]
    totals += [[f"Received ({c})", v] for c, v in o["money"]["received"].items()]
    totals += [["Total target stated on MOUs", o["targets"]["stated_on_mous"]]]
    totals += [[f"Target from extracted MOUs ({unit})", v] for unit, v in o["targets"]["from_extracted_mous"].items()]
    r = o["reporting"]
    totals += [["Reports done / total / overdue", f"{r['reports_done']} / {r['reports_total']} / {r['reports_overdue']}"],
               ["UCs done / total / overdue", f"{r['ucs_done']} / {r['ucs_total']} / {r['ucs_overdue']}"],
               ["Amounts are per currency and never added across currencies.", None]]
    return rows, totals
