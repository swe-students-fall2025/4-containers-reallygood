"""Tests for the Flask web application."""

# pylint: disable=missing-function-docstring,too-few-public-methods,unnecessary-lambda
from __future__ import annotations

from types import SimpleNamespace

from flask import Flask

from _lint_stubs import get_pytest, import_app_modules

pytest = get_pytest()
app_module, create_app = import_app_modules()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Provide default env vars and stub database connection."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017/testdb")
    monkeypatch.setenv("MONGO_DB_NAME", "testdb")
    monkeypatch.setattr(app_module, "get_db", lambda: object())


@pytest.fixture(name="client")
def client_fixture():
    """Return a configured Flask test client."""
    flask_app: Flask = create_app()
    flask_app.testing = True
    return flask_app.test_client()


def test_index(client):
    """Index route should return a simple health-check message."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Mood dashboard is running" in response.data


def test_api_snapshots_empty(monkeypatch, client):
    """`/api/snapshots` should return an empty list when no snapshots exist."""

    class EmptyCursor(list):
        """Cursor that supports sort/limit chain and iteration."""

        def sort(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

    monkeypatch.setattr(
        app_module,
        "get_collection",
        lambda _name: SimpleNamespace(find=lambda: EmptyCursor()),
    )

    response = client.get("/api/snapshots")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, dict)
    assert data["count"] == 0
    assert isinstance(data["items"], list)
    assert data["items"] == []


def test_api_create_snapshot_success(monkeypatch, client):
    """POST /api/snapshots returns the created id."""
    monkeypatch.setattr(app_module, "create_mood_snapshot", lambda _img: "abc123")

    response = client.post("/api/snapshots", json={"image_data": "base64string"})
    assert response.status_code == 200
    assert response.get_json() == {"id": "abc123"}


def test_api_create_snapshot_missing_image(client):
    """POST /api/snapshots without image data returns 400."""
    response = client.post("/api/snapshots", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_api_get_snapshot_found(monkeypatch, client):
    """GET /api/snapshots/<id> returns snapshot when present."""
    monkeypatch.setattr(
        app_module,
        "get_snapshot_view",
        lambda snapshot_id: {"id": snapshot_id, "status": "done"},
    )

    response = client.get("/api/snapshots/xyz")
    assert response.status_code == 200
    assert response.get_json() == {"id": "xyz", "status": "done"}


def test_api_get_snapshot_not_found(monkeypatch, client):
    """GET /api/snapshots/<id> returns 404 when missing."""
    monkeypatch.setattr(app_module, "get_snapshot_view", lambda _sid: None)

    response = client.get("/api/snapshots/missing")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_api_snapshots_with_data(monkeypatch, client):
    """`/api/snapshots` formats database docs for the dashboard."""

    class Cursor(list):
        """Provide minimal chaining behavior for Mongo cursor."""

        def sort(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

    docs = Cursor(
        [
            {
                "_id": "1",
                "processed": True,
                "mood": "happy",
                "face_detected": True,
                "created_at": "now",
            },
            {
                "_id": "2",
                "processed": False,
                "created_at": "later",
            },
        ]
    )

    monkeypatch.setattr(
        app_module,
        "get_collection",
        lambda _name: SimpleNamespace(find=lambda: docs),
    )

    response = client.get("/api/snapshots")
    assert response.status_code == 200
    data = response.get_json()

    assert data["count"] == 2
    assert data["items"][0]["status"] == "done"
    assert data["items"][0]["mood"] == "happy"
    assert data["items"][1]["status"] == "pending"
