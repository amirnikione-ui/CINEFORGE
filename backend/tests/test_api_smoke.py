"""API smoke tests (CF-019)."""
from __future__ import annotations


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["providers"]["llm"][0] in ("zai", "openai", "anthropic", "mock")
    assert body["providers"]["llm"][-1] == "mock"  # terminal tier always present


def test_project_lifecycle(client, project):
    pid = project["id"]
    assert project["status"] == "draft"
    res = client.get(f"/api/projects/{pid}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["project"]["title"] == "Nova Runners promo"
    assert detail["messages"] == []
    assert client.delete(f"/api/projects/{pid}").status_code == 204
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_project_validation(client):
    res = client.post("/api/projects", json={"title": "", "brief": "x"})
    assert res.status_code == 422
