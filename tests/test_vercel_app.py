import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vercel_app", ROOT / "app.py")
vercel_app = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(vercel_app)


@pytest.fixture
def client():
    return vercel_app.app.test_client()


def test_home_serves_chat_ui(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"Chatbot" in response.data
    assert b"history:c.m.slice(0,-1)" in response.data


def test_health_does_not_require_provider_credentials(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json["ok"] is True
    assert response.json["provider"] == "openrouter"


def test_chat_rejects_missing_message(client):
    response = client.post("/api/chat", json={"session_id": "session-1"})

    assert response.status_code == 400
    assert response.json["error"] == "invalid_request"


def test_chat_rejects_invalid_history(client):
    response = client.post(
        "/api/chat",
        json={
            "session_id": "session-1",
            "message": "Hello",
            "history": [{"role": "system", "content": "not allowed"}],
        },
    )

    assert response.status_code == 400
    assert "history roles" in response.json["message"]


def test_chat_uses_client_history(monkeypatch, client):
    captured = {}

    def fake_run_model_tool_loop(**kwargs):
        captured.update(kwargs)
        return {
            "assistant_text": "Hi",
            "status": "answered",
            "tool_events": [],
        }

    monkeypatch.setattr(vercel_app, "get_provider", lambda: object())
    monkeypatch.setattr(vercel_app, "run_model_tool_loop", fake_run_model_tool_loop)

    response = client.post(
        "/api/chat",
        json={
            "session_id": "session-1",
            "message": "Follow-up",
            "history": [
                {"role": "user", "content": "Earlier question"},
                {"role": "assistant", "content": "Earlier answer"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json["reply"] == "Hi"
    assert [message["role"] for message in captured["messages"]] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert captured["messages"][-1]["content"] == "Follow-up"


def test_chat_does_not_return_internal_errors(monkeypatch, client):
    monkeypatch.setattr(vercel_app, "get_provider", lambda: object())

    def fail_request(**kwargs):
        raise RuntimeError("internal provider details")

    monkeypatch.setattr(vercel_app, "run_model_tool_loop", fail_request)
    response = client.post(
        "/api/chat",
        json={"session_id": "session-1", "message": "Hello"},
    )

    assert response.status_code == 502
    assert response.json["error"] == "agent_request_failed"
    assert "internal provider details" not in response.json["message"]


def test_reset_accepts_session_id(client):
    response = client.post("/api/reset", json={"session_id": "session-1"})

    assert response.status_code == 200
    assert response.json == {"ok": True}
