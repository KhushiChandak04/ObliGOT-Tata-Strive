"""Backend-computed dashboard summary and form/filter options.

Every number is aggregated from persisted records at request time; nothing is stored or hard-coded. Amounts are
summed only within one currency and one financial concept (e.g. unpaid invoices), never across them.
"""
from collections import Counter, defaultdict
from datetime import date
from typing import get_args

from fastapi import APIRouter

from app.documents import DocumentKind, ScopeDimension
from app.models import (
    FINANCE_STATUSES, OPPORTUNITY_STAGES, AgreementStatus, FinanceType, MilestoneStatus, PartnerStatus, RecordStatus,
    RenewalStatus, SignedCopyStatus,
)
from app.repository import list_records
from app.routes import IMPORT_ENTITY_TYPES, _current_alerts

router = APIRouter(tags=["dashboard"])


def _by_currency(items: list[tuple[float, str]]) -> list[dict]:
    totals: dict[str, float] = defaultdict(float)
    counts: Counter = Counter()
    for amount, currency in items:
        totals[currency or "unknown"] += amount
        counts[currency or "unknown"] += 1
    return [{"currency": c, "amount": round(totals[c], 2), "count": counts[c]} for c in sorted(totals)]


@router.get("/dashboard/summary")
def dashboard_summary() -> dict:
    """Management summary from current records and the deterministic alerts (after review decisions)."""
    today, _, _, active = _current_alerts()
    actions, documents = list_records("actions"), list_records("documents")
    agreements, partners = list_records("agreements"), list_records("partners")
    finance, reports, terms = list_records("finance"), list_records("reports"), list_records("financial_terms")
    scope = [s for s in list_records("programme_scope") if s.get("review_state") == "approved"]
    level, category = Counter(a["priority"]["level"] for a in active), Counter(a["category"] for a in active)
    received_terms = {f.get("financial_term_id") for f in finance if f.get("record_type") == "fund_received" and f.get("status") == "received"}
    due_terms = [t for t in terms if t.get("review_state") == "approved" and t.get("term_type") in {"tranche", "payment_term"}
                 and t.get("due_date") and t["id"] not in received_terms and t.get("amount") is not None]
    overdue_terms = [t for t in due_terms if date.fromisoformat(str(t["due_date"])[:10]) < today]
    unpaid = [f for f in finance if f.get("record_type") == "invoice" and f.get("status") in {"raised", "sent"} and f.get("amount") is not None]
    overdue_reports = {a["record_id"] for a in active if a["rule_id"] in {"REPORT_OVERDUE", "UC_OVERDUE"}}
    return {
        "as_of": today.isoformat(),
        "alerts": {
            "open": len(active),
            "by_level": {k: level.get(k, 0) for k in ("high", "medium", "low")},
            "by_category": dict(sorted(category.items())),
            "overdue": sum(1 for a in active if (a.get("days_remaining") is not None and a["days_remaining"] < 0)),
            "mous_expiring_30d": sum(1 for a in active if a["rule_id"] == "MOU_EXPIRING" and a["days_remaining"] is not None and a["days_remaining"] <= 30),
        },
        "tasks": {
            "open": sum(1 for t in actions if t.get("status") in {"open", "in_review"}),
            "open_from_alerts": sum(1 for t in actions if t.get("status") in {"open", "in_review"} and t.get("source_alert_id")),
        },
        "partners": {"total": len(partners), "active": sum(1 for p in partners if p.get("status") == "active")},
        "agreements": {"active": sum(1 for a in agreements if a.get("status") == "active"),
                       "expired": sum(1 for a in agreements if a.get("status") == "expired")},
        "documents": {
            "awaiting_review": sum(1 for d in documents if d.get("status") == "needs_review"),
            "needs_attention": sum(1 for d in documents if d.get("status") in {"failed", "blocked", "retry_required"}),
            "addenda_awaiting_review": sum(1 for d in documents if d.get("kind") == "addendum" and d.get("status") == "needs_review"),
        },
        "reporting": {
            "overdue": len(overdue_reports),
            "open_reports": sum(1 for r in reports if r.get("status") not in {"submitted", "accepted"}),
            "pending_ucs": sum(1 for f in finance if f.get("record_type") == "utilization_certificate" and f.get("status") in {"pending", "rejected"}),
        },
        "finance": {
            # Each list is one concept, summed per currency only.
            "unpaid_invoices": _by_currency([(float(f["amount"]), f.get("currency") or "") for f in unpaid]),
            "fund_releases_due": _by_currency([(float(t["amount"]), t.get("currency") or "") for t in due_terms]),
            "fund_releases_overdue": _by_currency([(float(t["amount"]), t.get("currency") or "") for t in overdue_terms]),
        },
        "coverage": {
            dimension: [{"label": label, "count": count} for label, count in Counter(
                s["location"] or s["value"] if dimension == "location" else s["value"]
                for s in scope if (s.get("dimension") == dimension if dimension != "location" else s.get("location"))).most_common(12)]
            for dimension in ("state", "region", "course", "location")
        },
    }


@router.get("/options", tags=["system"])
def options() -> dict:
    """Allowed values (from the backend schema) and current record choices for forms and filters."""
    scope = [s for s in list_records("programme_scope") if s.get("review_state") == "approved"]
    return {
        "enums": {
            "partner_status": list(get_args(PartnerStatus)),
            "agreement_status": list(get_args(AgreementStatus)),
            "signed_copy": list(get_args(SignedCopyStatus)),
            "renewal_status": list(get_args(RenewalStatus)),
            "project_status": list(get_args(RecordStatus)),
            "milestone_status": list(get_args(MilestoneStatus)),
            "opportunity_stage": list(OPPORTUNITY_STAGES),
            "finance_record_type": list(get_args(FinanceType)),
            "finance_status": {k: list(v) for k, v in FINANCE_STATUSES.items()},
            "document_kind": list(get_args(DocumentKind)),
            "scope_dimension": list(get_args(ScopeDimension)),
            "import_entity_type": sorted(IMPORT_ENTITY_TYPES),
        },
        "partners": sorted(({"id": p["id"], "name": p["name"]} for p in list_records("partners")), key=lambda p: p["name"].lower()),
        "projects": sorted(({"id": p["id"], "name": p["name"], "partner_id": p.get("partner_id")} for p in list_records("projects")),
                           key=lambda p: p["name"].lower()),
        "agreements": sorted(({"id": a["id"], "title": a["title"], "partner_id": a.get("partner_id")} for a in list_records("agreements")),
                             key=lambda a: a["title"].lower()),
        # Filter values come from approved document data, not from a fixed list.
        "states": sorted({s["value"] for s in scope if s.get("dimension") == "state"} | {s["location"] for s in scope if s.get("location")}),
        "programmes": sorted({s["value"] for s in scope if s.get("dimension") in {"course", "training_type"}}),
    }
