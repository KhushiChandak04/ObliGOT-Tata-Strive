import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import repository
from app.models import FINANCE_STATUSES


@pytest.fixture
def c():
    repository._firestore_client = None
    repository._firestore_attempted = True
    repository._COLLECTIONS["finance"].clear()
    return TestClient(app)


def create(c, record_type, **extra):
    return c.post("/api/finance", json={"partner_id": "demo-001", "record_type": record_type, "title": f"Sample {record_type}", **extra})


@pytest.mark.parametrize("record_type,expected", [
    ("budget", "planned"), ("fund_received", "expected"), ("invoice", "raised"), ("utilization_certificate", "pending"),
])
def test_default_status_depends_on_record_type(c, record_type, expected):
    response = create(c, record_type)
    assert response.status_code == 201, response.text
    assert response.json()["status"] == expected


@pytest.mark.parametrize("record_type", sorted(FINANCE_STATUSES))
def test_every_allowed_status_is_accepted(c, record_type):
    for status in FINANCE_STATUSES[record_type]:
        assert create(c, record_type, status=status).status_code == 201


def test_status_from_another_type_or_free_text_is_rejected(c):
    assert create(c, "invoice", status="received").status_code == 422
    assert create(c, "fund_received", status="paid").status_code == 422
    response = create(c, "invoice", status="banana")
    assert response.status_code == 422
    assert "draft, sent, paid, cancelled" in response.text


def test_patch_validates_status_against_record_type(c):
    finance_id = create(c, "invoice").json()["id"]
    assert c.patch(f"/api/finance/{finance_id}", json={"status": "paid"}).json()["status"] == "paid"
    assert c.patch(f"/api/finance/{finance_id}", json={"status": "received"}).status_code == 422
    assert c.get(f"/api/finance/{finance_id}").json()["status"] == "paid"


def test_changing_record_type_requires_a_compatible_status(c):
    finance_id = create(c, "invoice", status="paid").json()["id"]
    assert c.patch(f"/api/finance/{finance_id}", json={"record_type": "fund_received"}).status_code == 422
    changed = c.patch(f"/api/finance/{finance_id}", json={"record_type": "fund_received", "status": "received"})
    assert changed.status_code == 200 and changed.json()["status"] == "received"


def test_legacy_status_still_readable_but_must_be_fixed_on_edit(c):
    repository._COLLECTIONS["finance"]["legacy-1"] = {
        "id": "legacy-1", "partner_id": "demo-001", "record_type": "invoice",
        "title": "Legacy invoice", "status": "pending", "source_label": "demo",
    }
    assert c.get("/api/finance/legacy-1").json()["status"] == "pending"
    assert c.get("/api/finance").status_code == 200
    assert c.patch("/api/finance/legacy-1", json={"title": "Renamed legacy invoice"}).status_code == 422
    fixed = c.patch("/api/finance/legacy-1", json={"title": "Renamed legacy invoice", "status": "sent"})
    assert fixed.status_code == 200 and fixed.json()["status"] == "sent"
