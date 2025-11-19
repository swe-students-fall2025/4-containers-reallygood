"""Tests for low-level database helpers."""

# pylint: disable=missing-function-docstring,too-few-public-methods,unnecessary-lambda
from __future__ import annotations

from unittest.mock import MagicMock

from _lint_stubs import get_pytest, import_db_module

pytest = get_pytest()
db = import_db_module()


@pytest.fixture(autouse=True)
def reset_client(monkeypatch):
    """Reset cached client between tests."""
    monkeypatch.setattr(db, "_client", None)


def test_get_client_requires_uri(monkeypatch):
    """get_client should raise when URI is missing."""
    monkeypatch.setattr(db, "MONGODB_URI", "")
    with pytest.raises(RuntimeError):
        db.get_client()


def test_get_client_returns_cached_instance(monkeypatch):
    """get_client should create and cache the Mongo client."""
    fake_client = MagicMock(name="MongoClient")
    monkeypatch.setattr(db, "MONGODB_URI", "mongodb://example")
    monkeypatch.setattr("db.MongoClient", lambda uri: fake_client)

    first = db.get_client()
    second = db.get_client()
    assert first is fake_client
    assert second is fake_client


def test_get_db_returns_named_database(monkeypatch):
    """get_db should request DB_NAME from the cached client."""
    fake_client = MagicMock()
    fake_db = MagicMock()
    fake_client.__getitem__.return_value = fake_db

    monkeypatch.setattr(db, "_client", fake_client)
    monkeypatch.setattr(db, "DB_NAME", "study")

    assert db.get_db() is fake_db
    fake_client.__getitem__.assert_called_once_with("study")


def test_get_collection_returns_named_collection(monkeypatch):
    """get_collection should proxy to the db object."""
    fake_db = MagicMock()
    fake_collection = MagicMock()
    fake_db.__getitem__.return_value = fake_collection

    monkeypatch.setattr(db, "get_db", lambda: fake_db)
    result = db.get_collection("mood_snapshots")
    assert result is fake_collection
    fake_db.__getitem__.assert_called_once_with("mood_snapshots")
