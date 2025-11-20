"""Tests for the Flask web application."""
import pytest  # pylint: disable=import-error
from flask import Flask  # pylint: disable=import-error
from app import create_app  # pylint: disable=import-error


@pytest.fixture
def client():  # pylint: disable=redefined-outer-name
    """Provides a Flask test client for running API tests."""
    flask_app: Flask = create_app()
    flask_app.testing = True
    return flask_app.test_client()


def test_index(client):  # pylint: disable=redefined-outer-name
    """Index route should return a simple health-check message."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Mood dashboard is running" in response.data


def test_api_snapshots_list(client):  # pylint: disable=redefined-outer-name
    """`/api/snapshots` should return a list of snapshots and a count field."""
    response = client.get("/api/snapshots")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, dict)
    assert "count" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
