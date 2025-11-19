"""
Tests for the Flask web dashboard.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app import create_app


@pytest.fixture(name="app")
def app_fixture() -> Flask:
    """
    Create a Flask app instance with a mocked database.

    pytest-flask will use this fixture to provide the `client` fixture.
    """
    # Fake collection that returns an empty list for find().sort().limit().
    fake_collection = MagicMock()

    class FakeCursor:
        """Minimal cursor implementing sort() and limit()."""

        def __init__(self, items: List[Dict[str, Any]]):
            self._items = items

        def sort(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self._items

        def __iter__(self):
            return iter(self._items)

    fake_collection.find.return_value = FakeCursor([])

    fake_db = MagicMock()
    fake_db.mood_snapshots = fake_collection

    with patch("app._get_database", return_value=fake_db):
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        return flask_app


def test_index(client) -> None:
    """
    Index route should return a simple health-check message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"Mood dashboard is running" in response.data


def test_api_snapshots_empty(client) -> None:
    """
    /api/snapshots should return an empty list when no snapshots exist.
    """
    response = client.get("/api/snapshots")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, dict)
    assert data["count"] == 0
    assert isinstance(data["items"], list)
    assert data["items"] == []
