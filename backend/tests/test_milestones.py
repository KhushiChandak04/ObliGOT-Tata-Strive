from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def new_project(partner_id="demo-002", **extra):
    return client.post("/api/projects", json={"name": "Milestone test project", "partner_id": partner_id, **extra}).json()["id"]


def create(**overrides):
    return client.post("/api/milestones", json={"project_id": "demo-project-001", "title": "Test milestone", **overrides})


def test_create_derives_partner_from_project_and_ignores_client_partner():
    project_id = new_project("demo-002")
    response = create(project_id=project_id, partner_id="demo-001", due_date="2026-12-01")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["partner_id"] == "demo-002" and body["status"] == "planned" and body["source_label"] == "user"


def test_create_validation():
    assert create(project_id="missing-project").status_code == 404
    assert create(title="x").status_code == 422
    assert create(status="done").status_code == 422
    assert create(status="completed").status_code == 422  # needs completed_date
    assert create(status="planned", completed_date="2026-10-01").status_code == 422
    assert create(status="completed", completed_date="2026-10-01").status_code == 201


def test_list_filters():
    ids = lambda **params: {m["id"] for m in client.get("/api/milestones", params=params).json()}
    assert ids(project_id="demo-project-001") == {"demo-milestone-001", "demo-milestone-002", "demo-milestone-003"}
    assert ids(partner_id="demo-001") >= {"demo-milestone-001", "demo-milestone-002", "demo-milestone-003"}
    assert ids(status="completed") == {"demo-milestone-001"}
    assert ids(partner_id="demo-003") == set()


def test_mark_complete_and_reopen():
    done = client.patch("/api/milestones/demo-milestone-002", json={"status": "completed", "completed_date": "2026-10-16"})
    assert done.status_code == 200 and done.json()["completed_date"] == "2026-10-16"
    assert client.patch("/api/milestones/demo-milestone-002", json={"status": "in_progress"}).status_code == 422
    reopened = client.patch("/api/milestones/demo-milestone-002", json={"status": "in_progress", "completed_date": None})
    assert reopened.status_code == 200 and reopened.json()["completed_date"] is None
    assert reopened.json()["source_label"] == "demo"


def test_patch_cannot_set_partner_and_rederives_on_project_move():
    other_project = new_project("demo-003")
    moved = client.patch("/api/milestones/demo-milestone-003", json={"project_id": other_project, "partner_id": "demo-001"})
    assert moved.status_code == 200 and moved.json()["partner_id"] == "demo-003"
    assert client.patch("/api/milestones/demo-milestone-003", json={"project_id": "missing"}).status_code == 404
    assert client.patch("/api/milestones/missing", json={"title": "x y"}).status_code == 404


def test_project_delete_and_partner_change_blocked_while_linked():
    blocked = client.delete("/api/projects/demo-project-001")
    assert blocked.status_code == 409
    for part in ("milestones: 3", "agreements: 1", "finance: 4", "reports: 2"):
        assert part in blocked.json()["detail"]
    moved = client.patch("/api/projects/demo-project-001", json={"partner_id": "demo-002"})
    assert moved.status_code == 409 and "partner cannot be changed" in moved.json()["detail"]
    assert client.patch("/api/projects/demo-project-001", json={"status": "on_hold"}).status_code == 200

    project_id = new_project("demo-002")
    milestone_id = create(project_id=project_id).json()["id"]
    assert client.delete(f"/api/projects/{project_id}").status_code == 409
    assert client.delete(f"/api/milestones/{milestone_id}").status_code == 204
    assert client.patch(f"/api/projects/{project_id}", json={"partner_id": "demo-003"}).status_code == 200
    assert client.delete(f"/api/projects/{project_id}").status_code == 204


def test_partner_delete_counts_milestones():
    project_id = new_project("demo-003")
    create(project_id=project_id)
    detail = client.delete("/api/partners/demo-003").json()["detail"]
    assert "milestones: 1" in detail and "projects: 1" in detail
