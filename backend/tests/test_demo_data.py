from fastapi.testclient import TestClient

from app import demo_data
from app.main import app
from app.models import FINANCE_STATUSES, AgreementCreate, FinanceCreate, ProjectCreate
from app.rules import scan_deadlines
from app.repository import _serialize

DEMO_COLLECTIONS = {
    "agreements": demo_data.AGREEMENTS, "projects": demo_data.PROJECTS,
    "finance": demo_data.FINANCE, "reports": demo_data.REPORTS, "actions": demo_data.ACTIONS,
}


def records(collection):
    return [_serialize(r) for r in collection.values()]


def test_every_demo_record_is_labelled_and_references_a_demo_partner():
    for name, collection in DEMO_COLLECTIONS.items():
        for record in records(collection):
            assert record["source_label"] == "demo", (name, record["id"])
            partner = record.get("partner_id") or record.get("related_partner_id")
            assert partner is None or partner in demo_data.PARTNERS, (name, record["id"])
    for record in records(demo_data.FINANCE) + records(demo_data.REPORTS):
        assert record.get("project_id") is None or record["project_id"] in demo_data.PROJECTS


def test_demo_records_pass_create_validation():
    for record in records(demo_data.AGREEMENTS):
        AgreementCreate.model_validate(record)
    for record in records(demo_data.PROJECTS):
        ProjectCreate.model_validate(record)
    for record in records(demo_data.FINANCE):
        FinanceCreate.model_validate(record)
        assert record["status"] in FINANCE_STATUSES[record["record_type"]]


def test_demo_data_produces_the_documented_findings():
    findings = scan_deadlines({
        "agreements": records(demo_data.AGREEMENTS), "finance": records(demo_data.FINANCE),
        "reports": records(demo_data.REPORTS),
    }, today=demo_data.today)
    issues = {f["record_id"]: f["issue"] for f in findings}
    assert issues == {
        "demo-agreement-001": "Expiring soon: Skills training MOU (demo)",
        "demo-agreement-002": "Missing expiry date: Data-sharing addendum (demo)",
        "demo-report-001": "Overdue: Monthly progress report (demo)",
        "demo-finance-003": "Missing due date: Invoice for tranche 2 (demo)",
        "demo-finance-004": "Due soon: Utilization certificate for tranche 1 (demo)",
    }


def test_actions_can_be_filtered_by_partner():
    client = TestClient(app)
    linked = client.get("/api/actions", params={"related_partner_id": "demo-001"}).json()
    assert linked and all(a["related_partner_id"] == "demo-001" for a in linked)
    assert client.get("/api/actions", params={"related_partner_id": "demo-003"}).json() == []
