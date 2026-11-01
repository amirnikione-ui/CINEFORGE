"""Contract tests: /health + projects REST per docs/API_CONTRACTS.md v0.1."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_contract_shape():
    with TestClient(app) as client:
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["version"] == "0.1.0"
        assert set(body["providers"]) == {"llm", "image", "tts", "stt", "music", "video"}
        assert "mock" in body["providers"]["llm"]
        assert "storage_root" in body


def test_project_lifecycle():
    with TestClient(app) as client:
        created = client.post("/api/projects", json={
            "title": "Nova Runners promo",
            "brief": "30s cinematic promo, dark mood, English narration",
            "style": "cinematic-dark",
            "platform": "instagram",
            "duration_hint_s": 30,
        })
        assert created.status_code == 201, created.text
        project = created.json()
        assert project["id"] and len(project["id"]) == 36  # uuid4
        assert project["status"] == "draft"
        assert project["platform"] == "instagram"

        listed = client.get("/api/projects").json()
        assert any(p["id"] == project["id"] for p in listed)

        detail = client.get(f"/api/projects/{project['id']}").json()
        assert detail["project"]["id"] == project["id"]
        assert detail["messages"] == [] and detail["assets"] == [] and detail["jobs"] == []

        assert client.delete(f"/api/projects/{project['id']}").status_code == 204
        assert client.get(f"/api/projects/{project['id']}").status_code == 404


def test_project_404():
    with TestClient(app) as client:
        assert client.get("/api/projects/nope").status_code == 404
