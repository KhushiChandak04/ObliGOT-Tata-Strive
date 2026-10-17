from datetime import timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.rules import business_today

client = TestClient(app)
REPORT_ALERT = "REPORT_OVERDUE:reports:demo-report-001"
MILESTONE_ALERT = "MILESTONE_OVERDUE:milestones:demo-milestone-002"


def alerts(**params):
    return client.get("/api/alerts", params=params).json()


def ids(**params):
    return {a["id"] for a in alerts(**params)["alerts"]}


def review(alert_id, **body):
    return client.post(f"/api/alerts/{alert_id}/review", json=body)


def activities(**params):
    return client.get("/api/activities", params=params).json()


def test_unreviewed_alerts_have_null_review():
    body = alerts()
    assert all(a["review"] is None and a["hidden_by_review"] is False for a in body["alerts"])
    assert body["counts"]["hidden_by_review"] == 0


def test_acknowledge_keeps_alert_visible_and_logs_activity():
    response = review(REPORT_ALERT, decision="acknowledged", note="Owner is on it")
    assert response.status_code == 200, response.text
    current = next(a for a in alerts()["alerts"] if a["id"] == REPORT_ALERT)
    assert current["review"]["decision"] == "acknowledged" and current["review"]["reviewer"] == "Demo user"
    latest = activities(partner_id="demo-001")[0]
    assert latest["event"] == "alert_acknowledged" and "Report overdue" in latest["summary"] and latest["details"]["note"] == "Owner is on it"


def test_dismiss_requires_reason_and_hides_alert_until_facts_change():
    assert review(REPORT_ALERT, decision="dismissed").status_code == 422
    assert review(REPORT_ALERT, decision="dismissed", reason="no").status_code == 422
    assert review(REPORT_ALERT, decision="dismissed", reason="Partner confirmed extension by email").status_code == 200
    assert REPORT_ALERT not in ids()
    assert REPORT_ALERT in ids(include_reviewed="true")
    assert alerts()["counts"]["hidden_by_review"] == 1
    # A new due date changes the facts, so the dismissal no longer applies and the alert returns.
    new_due = (business_today() - timedelta(days=2)).isoformat()
    client.patch("/api/reports/demo-report-001", json={"due_date": new_due})
    current = next(a for a in alerts()["alerts"] if a["id"] == REPORT_ALERT)
    assert current["review"] is None and current["previous_review"]["decision"] == "dismissed"


def test_dismissal_survives_daily_change_in_days_overdue():
    # Only stored facts are fingerprinted, so an unchanged record stays dismissed on later days.
    from app import engine, reviews
    from app.repository import list_records
    review(REPORT_ALERT, decision="dismissed", reason="Extension agreed in writing")
    later = business_today() + timedelta(days=3)
    alerts_later = engine.evaluate({n: list_records(n) for n in ("reports",)}, later)
    stored = {r["id"]: r for r in list_records("alert_reviews")}
    active, hidden = reviews.attach_reviews(alerts_later, stored, later)
    assert hidden == 1 and REPORT_ALERT not in {a["id"] for a in active}


def test_defer_validation_and_expiry():
    today = business_today()
    assert review(REPORT_ALERT, decision="deferred").status_code == 422
    assert review(REPORT_ALERT, decision="deferred", deferred_until=today.isoformat()).status_code == 422
    assert review(REPORT_ALERT, decision="deferred", deferred_until=(today + timedelta(days=400)).isoformat()).status_code == 422
    assert review(REPORT_ALERT, decision="acknowledged", deferred_until=(today + timedelta(days=3)).isoformat()).status_code == 422
    assert review(REPORT_ALERT, decision="deferred", deferred_until=(today + timedelta(days=3)).isoformat()).status_code == 200
    assert REPORT_ALERT not in ids()
    # Once the defer date arrives the alert is active again.
    from app import engine, reviews
    from app.repository import list_records
    on_date = today + timedelta(days=3)
    later = engine.evaluate({"reports": list_records("reports")}, on_date)
    active, hidden = reviews.attach_reviews(later, {r["id"]: r for r in list_records("alert_reviews")}, on_date)
    assert hidden == 0 and REPORT_ALERT in {a["id"] for a in active}


def test_clear_review_reopens_alert():
    review(REPORT_ALERT, decision="dismissed", reason="Handled elsewhere for now")
    assert client.delete(f"/api/alerts/{REPORT_ALERT}/review").status_code == 204
    assert REPORT_ALERT in ids()
    assert client.delete(f"/api/alerts/{REPORT_ALERT}/review").status_code == 404
    latest = activities()[0]
    assert latest["event"] == "alert_review_cleared"
    assert latest["summary"] == "Reopened “Report overdue” for Monthly progress report (demo) (previously dismissed)"


def test_review_unknown_or_resolved_alert_is_404():
    assert review("REPORT_OVERDUE:reports:missing", decision="acknowledged").status_code == 404
    client.patch("/api/reports/demo-report-001", json={"status": "submitted"})
    assert review(REPORT_ALERT, decision="acknowledged").status_code == 404


def test_create_task_from_alert_prefills_and_blocks_duplicates():
    response = client.post(f"/api/alerts/{MILESTONE_ALERT}/task", json={"owner": "Program Lead"})
    assert response.status_code == 201, response.text
    task, alert = response.json()["task"], response.json()["alert"]
    assert task["title"] == "Milestone overdue: Cohort 2 enrolment complete (demo)"
    assert task["owner"] == "Program Lead" and task["priority"] == "high" and task["status"] == "open"
    assert task["related_partner_id"] == "demo-001" and task["source_alert_id"] == MILESTONE_ALERT
    assert any(line.startswith("Due date: ") for line in task["evidence"])
    assert alert["review"]["decision"] == "task_created" and alert["review"]["task_id"] == task["id"]
    assert MILESTONE_ALERT in ids()  # still visible until the milestone itself is resolved
    assert client.post(f"/api/alerts/{MILESTONE_ALERT}/task", json={}).status_code == 409
    assert client.get(f"/api/actions/{task['id']}").json()["source_alert_id"] == MILESTONE_ALERT
    events = [a["event"] for a in activities(partner_id="demo-001")]
    assert "task_created_from_alert" in events


def test_completing_task_logs_status_change_and_allows_new_task():
    task = client.post(f"/api/alerts/{MILESTONE_ALERT}/task", json={}).json()["task"]
    client.patch(f"/api/actions/{task['id']}", json={"status": "done", "owner": "Someone Else"})
    events = {a["event"]: a for a in activities(entity_id=task["id"])}
    assert events["task_status_changed"]["details"] == {"field": "status", "from": "open", "to": "done"}
    assert "task_reassigned" in events
    assert client.post(f"/api/alerts/{MILESTONE_ALERT}/task", json={}).status_code == 201


def test_task_from_alert_validation():
    assert client.post(f"/api/alerts/{MILESTONE_ALERT}/task", json={"priority": "urgent"}).status_code == 422
    assert client.post(f"/api/alerts/{MILESTONE_ALERT}/task", json={"title": "x"}).status_code == 422
    assert client.post("/api/alerts/MILESTONE_OVERDUE:milestones:missing/task", json={}).status_code == 404


def test_full_loop_alert_to_task_to_resolution():
    task = client.post(f"/api/alerts/{MILESTONE_ALERT}/task", json={}).json()["task"]
    client.patch("/api/milestones/demo-milestone-002", json={"status": "completed", "completed_date": business_today().isoformat()})
    client.patch(f"/api/actions/{task['id']}", json={"status": "done"})
    assert MILESTONE_ALERT not in ids(include_reviewed="true")
    assert "TASK_OVERDUE" not in {a["rule_id"] for a in alerts()["alerts"]}


def test_activities_ordering_filters_and_limit():
    client.post("/api/actions", json={"title": "First task", "related_partner_id": "demo-002"})
    client.post("/api/actions", json={"title": "Second task", "related_partner_id": "demo-002"})
    rows = activities(partner_id="demo-002")
    assert [r["summary"] for r in rows][:2] == ["Created task “Second task”", "Created task “First task”"]
    assert all(r["id"].startswith("activity-") for r in rows)
    assert len(activities(limit=1)) == 1
    assert client.get("/api/activities", params={"limit": 0}).status_code == 422
