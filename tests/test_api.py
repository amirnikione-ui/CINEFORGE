"""API smoke tests over the full HTTP surface (health, CRUD, chat, files)."""
from __future__ import annotations

from pathlib import Path


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "llm" in body["providers"] and "mock" in body["providers"]["llm"]


def test_project_crud(client):
    created = client.post(
        "/api/projects",
        json={"title": "T1", "brief": "b", "platform": "youtube", "duration_hint_s": 20},
    )
    assert created.status_code == 201
    pid = created.json()["id"]

    listing = client.get("/api/projects")
    assert listing.status_code == 200
    assert any(p["id"] == pid for p in listing.json())

    detail = client.get(f"/api/projects/{pid}")
    assert detail.status_code == 200
    assert detail.json()["project"]["platform"] == "youtube"

    assert client.delete(f"/api/projects/{pid}").status_code == 204
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_missing_project_404(client):
    assert client.get("/api/projects/does-not-exist").status_code == 404
    assert client.post("/api/projects/does-not-exist/chat", json={"message": "hi"}).status_code == 404


def test_chat_produces_video_and_file_endpoint_works(client, project):
    resp = client.post(
        f"/api/projects/{project['id']}/chat",
        json={"message": "A 12-second cinematic promo for NOVA running shoes, dark mood"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["meta"]["tools_used"]
    video_assets = [a for a in body["assets"] if a["kind"] == "video"]
    assert video_assets, "chat must return a rendered video asset"

    file_resp = client.get(f"/api/assets/{video_assets[0]['id']}/file")
    assert file_resp.status_code == 200
    assert file_resp.headers["content-type"].startswith("video/mp4")
    assert int(file_resp.headers.get("content-length", 0)) > 50_000

    detail = client.get(f"/api/projects/{project['id']}")
    kinds = {a["kind"] for a in detail.json()["assets"]}
    assert {"storyboard", "frame", "audio", "video", "project"} <= kinds
    assert any(j["status"] == "done" for j in detail.json()["jobs"])


def test_media_analyze_endpoint(client, project):
    chat = client.post(
        f"/api/projects/{project['id']}/chat",
        json={"message": "A 10-second cinematic promo for NOVA shoes"},
    )
    video = next(a for a in chat.json()["assets"] if a["kind"] == "video")
    resp = client.post("/api/media/analyze", json={"asset_id": video["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert "scene_cuts" in body["analysis"]
    assert body["analysis"]["media"]["duration_s"] > 0
