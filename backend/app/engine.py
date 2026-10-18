"""Deterministic partnership rules engine.

Alerts are computed from the current records on every call; nothing here is stored. The same records,
configuration, and date always produce the same alerts, in the same order. Each alert carries the rule
that fired, the record values it is based on (evidence), and a transparent priority breakdown.

The priority score is an illustrative business rule, not a trained or validated prediction model.
"""
from collections import defaultdict
from datetime import date
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.config import settings
from app.rules import _parse_date


class RuleConfig(BaseModel):
    """Configurable thresholds (days). Stored as the `config/rules` record."""
    mou_expiry_warning_days: int = Field(default=60, ge=1, le=365)
    deadline_warning_days: int = Field(default=30, ge=1, le=180)
    stale_opportunity_days: int = Field(default=30, ge=7, le=365)
    invoice_aging_days: int = Field(default=30, ge=7, le=365)
    # Impact (not likelihood): an alert about an amount at or above this, in this currency, gets an impact factor.
    # Amounts in other currencies are never converted, so they do not get it.
    material_amount: float = Field(default=1_000_000, ge=0)
    material_currency: str = Field(default_factory=lambda: settings.default_currency, pattern=r"^[A-Z]{3}$")
    # Deals need a follow-up at least this often; an open deal with no contact for longer raises an alert.
    followup_days: int = Field(default=14, ge=1, le=180)
    # A funder whose committed budgets (material currency) reach this is a large funder: its alerts rank higher.
    large_funder_amount: float = Field(default=10_000_000, ge=0)


# Base points per severity. Overdue items outrank upcoming ones; data gaps rank lowest.
SEVERITY_POINTS = {"overdue": 50, "risk": 30, "due_soon": 25, "missing_data": 15}
# Partner tier set by the team (platinum/gold/silver customers rank higher).
# Big enough that, at the same urgency, Platinum outranks Gold outranks Silver outranks Bronze; timeline still counts.
TIER_POINTS = {"platinum": 25, "gold": 15, "silver": 8, "bronze": 3}
RELATED_ALERTS_THRESHOLD = 2  # other open alerts for the same partner that trigger the cross-record bump

RULES: dict[str, dict[str, str]] = {
    "MOU_EXPIRING": {"title": "MOU expiring soon", "category": "agreements", "severity": "due_soon",
        "description": "An active agreement expires within the MOU warning window and renewal is not recorded as renewed or not renewing.",
        "why": "If the agreement lapses, programme delivery and fund releases tied to it may lose their contractual basis.",
        "action": "Confirm the renewal decision with the partner and record the renewal status."},
    "MOU_EXPIRED_NO_RENEWAL": {"title": "Agreement expired without recorded renewal", "category": "agreements", "severity": "overdue",
        "description": "An active or expired agreement is past its expiry date and renewal is not recorded as renewed or not renewing.",
        "why": "Work may be continuing without a valid agreement, or the record may be out of date.",
        "action": "Confirm whether the agreement was renewed or ended, then update its status and renewal fields."},
    "MOU_SIGNED_COPY_MISSING": {"title": "Signed copy not on file", "category": "agreements", "severity": "risk",
        "description": "An agreement recorded as active does not have its signed copy recorded as received.",
        "why": "An active agreement without a signed copy on file cannot be verified if questioned.",
        "action": "Obtain the signed copy, store it, and update the signed-copy status and document link."},
    "AGREEMENT_EXPIRY_MISSING": {"title": "Active agreement has no expiry date", "category": "data_quality", "severity": "missing_data",
        "description": "An agreement recorded as active has no expiry date, so expiry cannot be monitored.",
        "why": "Without an expiry date, ObliGOT cannot warn before the agreement lapses.",
        "action": "Enter the expiry date from the signed agreement."},
    "APPROVED_NO_AGREEMENT": {"title": "Approved opportunity without an agreement record", "category": "pipeline", "severity": "risk",
        "description": "An opportunity at the approval or agreement stage has no agreement linked to it.",
        "why": "Approved work may start before an agreement exists, or the agreement may not be recorded.",
        "action": "Create the agreement record (draft if unsigned) and link it to this opportunity."},
    "OPPORTUNITY_NEXT_STEP_OVERDUE": {"title": "Pipeline next step overdue", "category": "pipeline", "severity": "overdue",
        "description": "An open opportunity's next-step date has passed.",
        "why": "Missed follow-ups slow partnerships down and can lose partner interest.",
        "action": "Complete or reschedule the next step and record the new date."},
    "OPPORTUNITY_FOLLOWUP_OVERDUE": {"title": "Deal follow-up overdue", "category": "pipeline", "severity": "overdue",
        "description": "An open deal has had no follow-up within the follow-up window and no upcoming next step is scheduled.",
        "why": "Follow-ups keep deals moving; a funder not contacted for weeks may lose interest or go elsewhere.",
        "action": "Contact the funder, then record the follow-up date and the next step on the deal."},
    "OPPORTUNITY_STALE": {"title": "Opportunity not updated recently", "category": "pipeline", "severity": "risk",
        "description": "An open opportunity has no next-step date and has not been updated within the stale-opportunity window.",
        "why": "Opportunities without a next step tend to stall unnoticed.",
        "action": "Review the opportunity, record a next step with a date, or close it."},
    "MILESTONE_OVERDUE": {"title": "Milestone overdue", "category": "projects", "severity": "overdue",
        "description": "A planned or in-progress milestone is past its due date.",
        "why": "Late milestones can delay dependent reporting, fund releases, and outcomes.",
        "action": "Confirm progress with the owner; mark it complete or record a revised plan."},
    "MILESTONE_DUE_SOON": {"title": "Milestone due soon", "category": "projects", "severity": "due_soon",
        "description": "A planned or in-progress milestone is due within the deadline warning window.",
        "why": "Early attention reduces the risk of a missed milestone.",
        "action": "Check with the owner that the milestone is on track."},
    "REPORT_OVERDUE": {"title": "Report overdue", "category": "reporting", "severity": "overdue",
        "description": "A report not marked submitted or accepted is past its due date.",
        "why": "Late reports can breach agreement terms and delay fund releases.",
        "action": "Confirm the submission plan with the owner and record the submission when done."},
    "REPORT_DUE_SOON": {"title": "Report due soon", "category": "reporting", "severity": "due_soon",
        "description": "A report not marked submitted or accepted is due within the deadline warning window.",
        "why": "Preparing reports early avoids last-minute delays.",
        "action": "Confirm the owner has the information needed to submit on time."},
    "REPORT_DUE_DATE_MISSING": {"title": "Report has no due date", "category": "data_quality", "severity": "missing_data",
        "description": "A report that is not submitted or accepted has no due date.",
        "why": "Without a due date, the report cannot be tracked against its commitment.",
        "action": "Enter the due date from the agreement or reporting schedule."},
    "UC_OVERDUE": {"title": "Utilization certificate overdue", "category": "finance", "severity": "overdue",
        "description": "A utilization certificate that is pending or rejected is past its due date.",
        "why": "Outstanding UCs can hold up later fund releases.",
        "action": "Follow up with the owner to submit (or resubmit) the UC and record it."},
    "UC_DUE_SOON": {"title": "Utilization certificate due soon", "category": "finance", "severity": "due_soon",
        "description": "A utilization certificate that is pending or rejected is due within the deadline warning window.",
        "why": "Preparing UCs early avoids delays to later fund releases.",
        "action": "Confirm the UC is being prepared and who will submit it."},
    "UC_DUE_DATE_MISSING": {"title": "Utilization certificate has no due date", "category": "data_quality", "severity": "missing_data",
        "description": "A pending or rejected utilization certificate has no due date.",
        "why": "Without a due date, the UC cannot be tracked.",
        "action": "Enter the UC due date from the agreement or funding terms."},
    "INVOICE_OVERDUE": {"title": "Invoice payment overdue", "category": "finance", "severity": "overdue",
        "description": "An invoice that is raised or sent (not paid or cancelled) is past its due date.",
        "why": "Unpaid invoices affect programme cash flow.",
        "action": "Follow up on payment with the partner and record receipt when paid."},
    "INVOICE_DUE_SOON": {"title": "Invoice payment due soon", "category": "finance", "severity": "due_soon",
        "description": "An invoice that is raised or sent is due within the deadline warning window.",
        "why": "A reminder before the due date reduces late payments.",
        "action": "Confirm the partner has received the invoice."},
    "INVOICE_AGING": {"title": "Unpaid invoice ageing", "category": "finance", "severity": "risk",
        "description": "An invoice that is raised or sent has no due date and was issued more than the invoice-ageing window ago. It is described by its age and is not called overdue.",
        "why": "Without agreed payment terms, an old unpaid invoice can be missed entirely.",
        "action": "Confirm payment status with the partner and record the payment terms or receipt."},
    "INVOICE_DUE_DATE_MISSING": {"title": "Invoice has no due date", "category": "data_quality", "severity": "missing_data",
        "description": "An invoice that is raised or sent has neither a due date nor an issue date, so it cannot be called overdue and its age cannot be determined.",
        "why": "Payment follow-up cannot be scheduled without a due date.",
        "action": "Enter the due date from the invoice terms."},
    "FUND_RELEASE_OVERDUE": {"title": "Contractual fund release overdue", "category": "finance", "severity": "overdue",
        "description": "An approved tranche or payment term from an agreement is past its due date and no receipt is recorded against it.",
        "why": "A missed release can stall programme delivery; it may also mean a receipt was not recorded.",
        "action": "Confirm with the partner whether the tranche was released; record the receipt against the term or agree a revised date."},
    "FUND_RELEASE_DUE_SOON": {"title": "Contractual fund release due soon", "category": "finance", "severity": "due_soon",
        "description": "An approved tranche or payment term from an agreement is due within the deadline warning window and no receipt is recorded against it.",
        "why": "Conditions for the release (reports, UCs, milestones) may need to be met first.",
        "action": "Check the release conditions and confirm the expected date with the partner."},
    "AMENDMENT_UNRESOLVED": {"title": "Amendment conflict unresolved", "category": "agreements", "severity": "risk",
        "description": "An addendum change is marked unresolved (conflicting or unclear), so the agreement's effective terms are uncertain.",
        "why": "Deadlines and amounts may rest on a term that has not been settled; unresolved changes are never applied automatically.",
        "action": "Decide which value governs with the partner and approve or reject the change."},
    "TASK_OVERDUE": {"title": "Action overdue", "category": "tasks", "severity": "overdue",
        "description": "An open or in-review action is past its due date.",
        "why": "Overdue actions often hide the follow-ups that prevent other deadlines from slipping.",
        "action": "Complete the action, reassign it, or record a new due date."},
}

OPEN_PIPELINE_STAGES = {"identified", "qualification", "proposal", "approval", "agreement", "renewal"}
FINAL_RENEWAL = {"renewed", "not_renewing"}
UNRESOLVED_REPORT = lambda status: status not in {"submitted", "accepted"}


def _ev(label: str, value: Any, source: str = "record") -> dict[str, Any]:
    """Evidence item. `source` is "record" for stored values and "computed" for values derived by the rule."""
    if isinstance(value, date):
        value = value.isoformat()
    return {"label": label, "value": "Not recorded" if value in (None, "") else value, "source": source}


def _days(target: date, today: date) -> int:
    return (target - today).days


class _Builder:
    def __init__(self, today: date, config: RuleConfig):
        self.today, self.config, self.alerts = today, config, []

    def add(self, rule_id: str, record_type: str, record: dict, title: str, *, partner_id: str | None, owner: str | None,
            due: date | None = None, evidence: list[dict] | None = None, adjustments: list[tuple[str, int]] | None = None,
            amount_recorded: bool = False, amount: tuple[float, str] | None = None) -> None:
        rule = RULES[rule_id]
        days_remaining = _days(due, self.today) if due else None
        self.alerts.append({
            "id": f"{rule_id}:{record_type}:{record['id']}",
            "rule_id": rule_id, "rule_title": rule["title"], "rule_description": rule["description"],
            "category": rule["category"], "severity": rule["severity"],
            "record_type": record_type, "record_id": record["id"], "record_title": title,
            "partner_id": partner_id, "project_id": record.get("project_id"),
            "owner": owner or "Unassigned", "due_date": due.isoformat() if due else None, "days_remaining": days_remaining,
            "evidence": evidence or [], "why_it_matters": rule["why"], "recommended_action": rule["action"],
            "source_label": record.get("source_label", "user"),
            "_adjustments": adjustments or [], "_amount_recorded": amount_recorded or amount is not None, "_amount": amount,
        })

    def deadline(self, rule_overdue: str, rule_soon: str | None, record_type: str, record: dict, title: str, due: date, *,
                 window: int, partner_id: str | None, owner: str | None, evidence: list[dict], amount_recorded: bool = False,
                 amount: tuple[float, str] | None = None) -> None:
        remaining = _days(due, self.today)
        if remaining < 0:
            evidence = evidence + [_ev("Days overdue", -remaining, "computed")]
            self.add(rule_overdue, record_type, record, title, partner_id=partner_id, owner=owner, due=due, evidence=evidence,
                     amount_recorded=amount_recorded, amount=amount)
        elif rule_soon and remaining <= window:
            evidence = evidence + [_ev("Days remaining", remaining, "computed")]
            self.add(rule_soon, record_type, record, title, partner_id=partner_id, owner=owner, due=due, evidence=evidence,
                     amount_recorded=amount_recorded, amount=amount)


def _agreement_rules(b: _Builder, agreements: list[dict]) -> None:
    for a in agreements:
        status, renewal = a.get("status"), a.get("renewal_status") or "none"
        expiry, title = _parse_date(a.get("expiry_date")), a.get("title", a["id"])
        base = [_ev("Status", status), _ev("Expiry date", expiry), _ev("Renewal status", renewal)]
        common = {"partner_id": a.get("partner_id"), "owner": a.get("owner")}
        if status in {"active", "expired"} and expiry and renewal not in FINAL_RENEWAL:
            remaining = _days(expiry, b.today)
            if remaining < 0:
                b.add("MOU_EXPIRED_NO_RENEWAL", "agreements", a, title, due=expiry, evidence=base + [_ev("Days since expiry", -remaining, "computed")], **common)
            elif remaining <= b.config.mou_expiry_warning_days and status == "active":
                adjustments = [("Renewal already in progress", -10)] if renewal == "in_progress" else []
                b.add("MOU_EXPIRING", "agreements", a, title, due=expiry, adjustments=adjustments,
                      evidence=base + [_ev("Days remaining", remaining, "computed"), _ev("Warning window (days)", b.config.mou_expiry_warning_days, "computed")], **common)
        if status == "active" and (a.get("signed_copy") or "unknown") != "received":
            b.add("MOU_SIGNED_COPY_MISSING", "agreements", a, title, evidence=[_ev("Status", status), _ev("Signed copy", a.get("signed_copy") or "unknown"), _ev("Document link", a.get("document_url"))], **common)
        if status == "active" and not expiry:
            b.add("AGREEMENT_EXPIRY_MISSING", "agreements", a, title, evidence=[_ev("Status", status), _ev("Expiry date", None)], **common)


def _pipeline_rules(b: _Builder, opportunities: list[dict], agreements: list[dict]) -> None:
    linked = {a.get("opportunity_id") for a in agreements if a.get("opportunity_id")}
    for o in opportunities:
        stage, title = o.get("stage"), o.get("title", o["id"])
        common = {"partner_id": o.get("partner_id"), "owner": o.get("owner")}
        if stage in {"approval", "agreement"} and o["id"] not in linked:
            b.add("APPROVED_NO_AGREEMENT", "opportunities", o, title, evidence=[_ev("Stage", stage), _ev("Linked agreements", 0, "computed")], **common)
        if stage not in OPEN_PIPELINE_STAGES:
            continue
        next_date = _parse_date(o.get("next_step_date"))
        if next_date and next_date < b.today:
            b.add("OPPORTUNITY_NEXT_STEP_OVERDUE", "opportunities", o, title, due=next_date,
                  evidence=[_ev("Stage", stage), _ev("Next step", o.get("next_step")), _ev("Next step date", next_date), _ev("Days overdue", _days(b.today, next_date), "computed")], **common)
        elif not next_date:
            # Last contact: the recorded follow-up, else when the deal started. Without either, fall back to staleness.
            contact = _parse_date(o.get("last_followup_date")) or _parse_date(o.get("started_on"))
            if contact:
                due = date.fromordinal(contact.toordinal() + b.config.followup_days)
                if due < b.today:
                    b.add("OPPORTUNITY_FOLLOWUP_OVERDUE", "opportunities", o, title, due=due,
                          evidence=[_ev("Stage", stage), _ev("Last follow-up", o.get("last_followup_date")),
                                    _ev("Deal started", o.get("started_on")), _ev("Follow-up every (days)", b.config.followup_days, "computed"),
                                    _ev("Days since last contact", _days(b.today, contact), "computed")], **common)
                continue
            updated = _parse_date(o.get("updated_at"))
            if updated and _days(b.today, updated) > b.config.stale_opportunity_days:
                b.add("OPPORTUNITY_STALE", "opportunities", o, title,
                      evidence=[_ev("Stage", stage), _ev("Next step date", None), _ev("Last updated", updated), _ev("Days since update", _days(b.today, updated), "computed")], **common)


def _milestone_rules(b: _Builder, milestones: list[dict]) -> None:
    for m in milestones:
        due = _parse_date(m.get("due_date"))
        if m.get("status") in {"planned", "in_progress"} and due:
            b.deadline("MILESTONE_OVERDUE", "MILESTONE_DUE_SOON", "milestones", m, m.get("title", m["id"]), due,
                       window=b.config.deadline_warning_days, partner_id=m.get("partner_id"), owner=m.get("owner"),
                       evidence=[_ev("Status", m.get("status")), _ev("Due date", due)])


def _report_rules(b: _Builder, reports: list[dict]) -> None:
    for r in reports:
        if not UNRESOLVED_REPORT(r.get("status")):
            continue
        due, title = _parse_date(r.get("due_date")), r.get("title", r["id"])
        evidence = [_ev("Report type", r.get("report_type")), _ev("Status", r.get("status")), _ev("Due date", due)]
        common = {"partner_id": r.get("partner_id"), "owner": r.get("owner")}
        if due:
            b.deadline("REPORT_OVERDUE", "REPORT_DUE_SOON", "reports", r, title, due, window=b.config.deadline_warning_days, evidence=evidence, **common)
        else:
            b.add("REPORT_DUE_DATE_MISSING", "reports", r, title, evidence=evidence, **common)


def _finance_rules(b: _Builder, finance: list[dict]) -> None:
    for f in finance:
        kind, status, due, title = f.get("record_type"), f.get("status"), _parse_date(f.get("due_date")), f.get("title", f["id"])
        has_amount = f.get("amount") is not None
        evidence = [_ev("Type", kind), _ev("Status", status), _ev("Issue date", _parse_date(f.get("issue_date"))), _ev("Due date", due),
                    _ev("Amount", f"{f['amount']:,.2f} {f.get('currency', '')}".strip() if has_amount else None), _ev("Reference", f.get("reference_number"))]
        common = {"partner_id": f.get("partner_id"), "owner": None,
                  "amount": (float(f["amount"]), f.get("currency") or "") if has_amount else None}
        if kind == "utilization_certificate" and status in {"pending", "rejected"}:
            if due:
                b.deadline("UC_OVERDUE", "UC_DUE_SOON", "finance", f, title, due, window=b.config.deadline_warning_days, evidence=evidence, **common)
            else:
                b.add("UC_DUE_DATE_MISSING", "finance", f, title, evidence=evidence, partner_id=f.get("partner_id"), owner=None)
        elif kind == "invoice" and status in {"raised", "sent"}:
            issued = _parse_date(f.get("issue_date"))
            if due:
                b.deadline("INVOICE_OVERDUE", "INVOICE_DUE_SOON", "finance", f, title, due, window=b.config.deadline_warning_days, evidence=evidence, **common)
            elif issued:
                age = _days(b.today, issued)
                if age > b.config.invoice_aging_days:
                    b.add("INVOICE_AGING", "finance", f, title, evidence=evidence + [_ev("Days since issue", age, "computed"),
                          _ev("Ageing window (days)", b.config.invoice_aging_days, "computed")], **common)
            else:
                b.add("INVOICE_DUE_DATE_MISSING", "finance", f, title, evidence=evidence, partner_id=f.get("partner_id"), owner=None)


def _fund_release_rules(b: _Builder, terms: list[dict], finance: list[dict], agreements: list[dict]) -> None:
    """Approved contractual tranches/payment terms with a due date, checked against receipts recorded for them."""
    received = {f.get("financial_term_id") for f in finance
                if f.get("record_type") == "fund_received" and f.get("status") == "received" and f.get("financial_term_id")}
    by_id = {a["id"]: a for a in agreements}
    for t in terms:
        due = _parse_date(t.get("due_date"))
        agreement = by_id.get(t.get("agreement_id") or "")
        if (t.get("review_state") != "approved" or t.get("term_type") not in {"tranche", "payment_term"} or not due
                or not agreement or agreement.get("status") in {"closed", "draft"} or t["id"] in received):
            continue
        amount = (float(t["amount"]), t.get("currency") or "") if t.get("amount") is not None else None
        b.deadline("FUND_RELEASE_OVERDUE", "FUND_RELEASE_DUE_SOON", "financial_terms", t, t.get("description", t["id"]), due,
                   window=b.config.deadline_warning_days, partner_id=t.get("partner_id") or agreement.get("partner_id"),
                   owner=agreement.get("owner"), amount=amount,
                   evidence=[_ev("Agreement", agreement.get("title")), _ev("Term", t.get("term_type")),
                             _ev("Amount", f"{amount[0]:,.2f} {amount[1]}".strip() if amount else None), _ev("Basis", t.get("basis")),
                             _ev("Due date", due), _ev("Condition", t.get("condition")),
                             _ev("Receipts recorded against this term", 0, "computed")])


def _amendment_rules(b: _Builder, changes: list[dict], agreements: list[dict]) -> None:
    by_id = {a["id"]: a for a in agreements}
    for c in changes:
        agreement = by_id.get(c.get("agreement_id") or "")
        if c.get("status") != "unresolved" or not agreement:
            continue
        b.add("AMENDMENT_UNRESOLVED", "agreement_changes", c, f"{c.get('field', 'term')} on {agreement.get('title', agreement['id'])}",
              partner_id=agreement.get("partner_id"), owner=agreement.get("owner"),
              evidence=[_ev("Agreement", agreement.get("title")), _ev("Term", c.get("field")), _ev("Current value", c.get("prior_value")),
                        _ev("Proposed value", c.get("proposed_value")), _ev("Effective date", c.get("effective_date")),
                        _ev("Reviewer note", c.get("note"))])


def _task_rules(b: _Builder, actions: list[dict]) -> None:
    for t in actions:
        due = _parse_date(t.get("due_date"))
        if t.get("status") in {"open", "in_review"} and due and due < b.today:
            b.add("TASK_OVERDUE", "actions", t, t.get("title", t["id"]), due=due, partner_id=t.get("related_partner_id"), owner=t.get("owner"),
                  evidence=[_ev("Status", t.get("status")), _ev("Due date", due), _ev("Days overdue", _days(b.today, due), "computed")])


def _score(alert: dict, related_count: int, config: RuleConfig, partner: dict | None = None,
           committed: float = 0.0) -> dict[str, Any]:
    """Transparent points. Each factor is tagged: `urgency` (how soon/late), `impact` (what is at stake), or
    `context`. A large amount raises impact only; it is never treated as evidence of a partner's reliability."""
    factors = [{"label": f"Base: {alert['severity'].replace('_', ' ')}", "points": SEVERITY_POINTS[alert["severity"]], "kind": "urgency"}]
    days = alert["days_remaining"]
    if days is not None and days < 0:
        factors.append({"label": f"{-days} days overdue (max 30)", "points": min(30, -days), "kind": "urgency"})
    elif days is not None and alert["severity"] == "due_soon":
        if days <= 7:
            factors.append({"label": "Due within 7 days", "points": 20, "kind": "urgency"})
        elif days <= 14:
            factors.append({"label": "Due within 14 days", "points": 10, "kind": "urgency"})
    if related_count >= RELATED_ALERTS_THRESHOLD:
        factors.append({"label": f"Partner has {related_count} other open alerts", "points": 10, "kind": "context"})
    if alert["_amount_recorded"]:
        factors.append({"label": "Recorded amount at stake", "points": 5, "kind": "impact"})
    amount = alert["_amount"]
    if amount and amount[1] == config.material_currency and amount[0] >= config.material_amount:
        factors.append({"label": f"Material amount (at least {config.material_currency} {config.material_amount:,.0f})", "points": 10, "kind": "impact"})
    tier = (partner or {}).get("tier")
    if tier in TIER_POINTS:
        factors.append({"label": f"{tier.title()} partner", "points": TIER_POINTS[tier], "kind": "impact"})
    if config.large_funder_amount and committed >= config.large_funder_amount:
        factors.append({"label": f"Large funder ({config.material_currency} {committed:,.0f} committed)", "points": 10, "kind": "impact"})
    factors += [{"label": label, "points": points, "kind": "context"} for label, points in alert["_adjustments"]]
    score = max(0, sum(f["points"] for f in factors))
    level = "high" if score >= 60 else "medium" if score >= 35 else "low"
    return {"score": score, "level": level, "factors": factors,
            "urgency": sum(f["points"] for f in factors if f["kind"] == "urgency"),
            "impact": sum(f["points"] for f in factors if f["kind"] == "impact")}


def evaluate(records: dict[str, list[dict]], today: date, config: RuleConfig | None = None) -> list[dict[str, Any]]:
    """Run every rule over `records` (collection name -> list of records) and return prioritised alerts."""
    config = config or RuleConfig()
    b = _Builder(today, config)
    get: Callable[[str], list[dict]] = lambda name: records.get(name, [])
    _agreement_rules(b, get("agreements"))
    _pipeline_rules(b, get("opportunities"), get("agreements"))
    _milestone_rules(b, get("milestones"))
    _report_rules(b, get("reports"))
    _finance_rules(b, get("finance"))
    _task_rules(b, get("actions"))
    _fund_release_rules(b, get("financial_terms"), get("finance"), get("agreements"))
    _amendment_rules(b, get("agreement_changes"), get("agreements"))

    partners = {p["id"]: p for p in get("partners")}
    # Committed money per funder: budgets in the material currency only (other currencies are never converted).
    committed: dict[str, float] = defaultdict(float)
    for f in get("finance"):
        if f.get("record_type") == "budget" and f.get("amount") is not None and f.get("currency") == config.material_currency:
            committed[f.get("partner_id")] += float(f["amount"])
    by_partner: dict[str | None, list[str]] = defaultdict(list)
    for alert in b.alerts:
        by_partner[alert["partner_id"]].append(alert["id"])
    for alert in b.alerts:
        related = [i for i in by_partner[alert["partner_id"]] if i != alert["id"]] if alert["partner_id"] else []
        alert["related_alert_ids"] = related
        partner = partners.get(alert["partner_id"] or "")
        # Partner facts for filtering (tier, group, location) travel with the alert.
        alert["partner_tier"] = (partner or {}).get("tier")
        alert["partner_group"] = (partner or {}).get("group")
        alert["partner_location"] = (partner or {}).get("location")
        alert["priority"] = _score(alert, len(related), config, partner, committed.get(alert["partner_id"] or "", 0.0))
        del alert["_adjustments"], alert["_amount_recorded"], alert["_amount"]
    # Highest score first; then the most urgent date; then a stable id so ordering is deterministic.
    return sorted(b.alerts, key=lambda a: (-a["priority"]["score"], a["days_remaining"] if a["days_remaining"] is not None else 10**6, a["id"]))


def rule_catalog() -> list[dict[str, str]]:
    return [{"rule_id": rule_id, "title": r["title"], "description": r["description"], "category": r["category"],
             "severity": r["severity"], "why_it_matters": r["why"], "recommended_action": r["action"]} for rule_id, r in RULES.items()]
