"""Tests for the Flask web application."""
from __future__ import annotations

from typing import List, Dict, Any

import pytest  # pylint: disable=import-error
from flask import Flask  # pylint: disable=import-error
import app as app_module  # pylint: disable=import-error


@pytest.fixture
def client(monkeypatch):  # pylint: disable=redefined-outer-name
    """
    Provide a Flask test client for running API tests.

    The fixture injects a test MongoDB URI into the environment and replaces
    the real DB helpers with lightweight stubs so that tests do not depend
    on a running MongoDB instance.
    """
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017/testdb")

    class FakeCursor:
        """Stub cursor that behaves as if there are no documents."""

        def sort(self, *args, **kwargs):  # pylint: disable=unused-argument
            """Return self to allow method chaining."""
            return self

        def limit(self, *args, **kwargs):  # pylint: disable=unused-argument
            """Return self to allow method chaining."""
            return self

        def __iter__(self):
            """Iterate over an empty result set."""
            return iter([])

    class FakeCollection:  # pylint: disable=too-few-public-methods
        """Stub MongoDB collection that always returns an empty cursor."""

        def find(self, *args, **kwargs):  # pylint: disable=unused-argument
            """Return a fake cursor representing an empty collection."""
            return FakeCursor()

    class FakeDatabase:  # pylint: disable=too-few-public-methods
        """Stub MongoDB database that returns fake collections."""

        def __getitem__(self, name: str):  # pylint: disable=unused-argument
            """Return a fake collection for any collection name."""
            return FakeCollection()

    def fake_get_db() -> FakeDatabase:
        """Return a fake database object instead of a real MongoDB connection."""
        return FakeDatabase()

    def fake_get_collection(name: str) -> FakeCollection:  # pylint: disable=unused-argument
        """Return a fake collection for any requested collection name."""
        return FakeCollection()

    monkeypatch.setattr(app_module, "get_db", fake_get_db)
    monkeypatch.setattr(app_module, "get_collection", fake_get_collection)

    flask_app: Flask = app_module.create_app()
    flask_app.config["TESTING"] = True

    with flask_app.test_client() as test_client:
        yield test_client


def test_index(client):  # pylint: disable=redefined-outer-name
    """Index route should return a simple health-check message."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Mood dashboard is running" in response.data


def test_dashboard_page(client, monkeypatch):  # pylint: disable=redefined-outer-name
    """`/dashboard` should render the dashboard template."""
    def fake_render_template(template_name: str) -> str:
        """Return a simple HTML string instead of rendering a real template."""
        assert template_name == "dashboard.html"
        return "<html>DASHBOARD</html>"

    monkeypatch.setattr(app_module, "render_template", fake_render_template)

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"DASHBOARD" in response.data


def test_api_snapshots_empty(client):  # pylint: disable=redefined-outer-name
    """`/api/snapshots` should return an empty list when no snapshots exist."""
    response = client.get("/api/snapshots")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, dict)
    assert data["count"] == 0
    assert isinstance(data["items"], list)
    assert data["items"] == []


def test_api_create_snapshot_missing_image(client):  # pylint: disable=redefined-outer-name
    """POST /api/snapshots without image_data should return 400."""
    response = client.post("/api/snapshots", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "missing image_data"


def test_api_create_snapshot_success(client, monkeypatch):  # pylint: disable=redefined-outer-name
    """POST /api/snapshots with valid image_data should call create_mood_snapshot."""
    called_with: List[str] = []

    def fake_create_mood_snapshot(image_data: str) -> str:
        """Record the image data and return a fixed snapshot id."""
        called_with.append(image_data)
        return "fake-snapshot-id"

    monkeypatch.setattr(app_module, "create_mood_snapshot", fake_create_mood_snapshot)

    response = client.post(
        "/api/snapshots",
        json={"image_data": "dummy-image-data"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "fake-snapshot-id"
    assert called_with == ["dummy-image-data"]


def test_api_get_snapshot_not_found(client, monkeypatch):  # pylint: disable=redefined-outer-name
    """GET /api/snapshots/<id> should return 404 when snapshot is missing."""
    monkeypatch.setattr(app_module, "get_snapshot_view", lambda _sid: None)

    response = client.get("/api/snapshots/nonexistent-id")
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "not found"


def test_api_get_snapshot_found(client, monkeypatch):  # pylint: disable=redefined-outer-name
    """GET /api/snapshots/<id> should return a view dict when snapshot exists."""
    fake_view = {
        "id": "abc123",
        "processed": True,
        "mood": "happy",
        "face_detected": True,
        "created_at": "2024-01-01T00:00:00",
        "status": "done",
    }

    def fake_get_snapshot_view(snapshot_id: str):
        """Return a predefined snapshot view for a specific id."""
        assert snapshot_id == "abc123"
        return fake_view

    monkeypatch.setattr(app_module, "get_snapshot_view", fake_get_snapshot_view)

    response = client.get("/api/snapshots/abc123")
    assert response.status_code == 200
    data = response.get_json()
    assert data == fake_view


def test_create_app_without_mongodb_uri_raises_runtime_error(monkeypatch):
    """create_app should raise RuntimeError if MONGODB_URI is missing."""
    monkeypatch.delenv("MONGODB_URI", raising=False)

    with pytest.raises(RuntimeError) as excinfo:
        app_module.create_app()

    assert "MONGODB_URI not set" in str(excinfo.value)


def test_api_snapshots_non_empty_list(monkeypatch):
    """
    `/api/snapshots` should build items and status correctly when documents exist.

    This exercises the for-loop and status branching in api_list_snapshots.
    """
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017/testdb")

    doc1: Dict[str, Any] = {
        "_id": "1",
        "processed": False,
        "mood": "neutral",
        "face_detected": False,
        "created_at": "t1",
    }
    doc2: Dict[str, Any] = {
        "_id": "2",
        "processed": True,
        "mood": "happy",
        "face_detected": True,
        "created_at": "t2",
    }

    class NonEmptyCursor:
        """Cursor that yields two snapshot documents."""

        def sort(self, *args, **kwargs):  # pylint: disable=unused-argument
            """Return self to allow method chaining."""
            return self

        def limit(self, *args, **kwargs):  # pylint: disable=unused-argument
            """Return self to allow method chaining."""
            return self

        def __iter__(self):
            """Iterate over the fake snapshot documents."""
            return iter([doc1, doc2])

    class NonEmptyCollection:  # pylint: disable=too-few-public-methods
        """Collection whose find() returns a non-empty cursor."""

        def find(self, *args, **kwargs):  # pylint: disable=unused-argument
            """Return a cursor that yields fake snapshot documents."""
            return NonEmptyCursor()

    class NonEmptyDatabase:  # pylint: disable=too-few-public-methods
        """Database that always returns the same non-empty collection."""

        def __getitem__(self, name: str):  # pylint: disable=unused-argument
            """Return a collection that yields fake snapshot documents."""
            return NonEmptyCollection()

    def fake_get_db() -> NonEmptyDatabase:
        """Return a fake database containing snapshot documents."""
        return NonEmptyDatabase()

    def fake_get_collection(name: str) -> NonEmptyCollection:  # pylint: disable=unused-argument
        """Return a collection that yields fake snapshot documents."""
        return NonEmptyCollection()

    monkeypatch.setattr(app_module, "get_db", fake_get_db)
    monkeypatch.setattr(app_module, "get_collection", fake_get_collection)

    flask_app: Flask = app_module.create_app()
    flask_app.config["TESTING"] = True

    with flask_app.test_client() as test_client:
        response = test_client.get("/api/snapshots")

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2

    items = data["items"]
    ids = {item["id"] for item in items}
    assert ids == {"1", "2"}

    status_by_id = {item["id"]: item["status"] for item in items}
    assert status_by_id["1"] == "pending"
    assert status_by_id["2"] == "done"
