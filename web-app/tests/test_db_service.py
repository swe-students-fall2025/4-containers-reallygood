"""Unit tests for db_service helper functions."""
# pylint: disable=missing-function-docstring,too-few-public-methods,unnecessary-lambda
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from bson import ObjectId

from _lint_stubs import (
    get_pytest,
    import_db_service_module,
)

pytest = get_pytest()
db_service = import_db_service_module()


@pytest.fixture(name="fake_collection")
def fake_collection_fixture(monkeypatch):
    """Provide a fake Mongo collection and patch get_collection."""

    class FakeCollection:
        """In-memory stub used by tests."""
        def __init__(self):
            self.inserted = []
            self.next_result = None
            self.last_query = None

        def insert_one(self, doc):
            self.inserted.append(doc)
            return SimpleNamespace(inserted_id="generated-id")

        def find_one(self, query):
            self.last_query = query
            return self.next_result

    collection = FakeCollection()
    monkeypatch.setattr(db_service, "get_collection", lambda _name: collection)
    return collection


def test_create_mood_snapshot_inserts_document(fake_collection):
    """create_mood_snapshot should persist the payload and metadata."""
    inserted_id = db_service.create_mood_snapshot(
        "image-bytes",
        metadata={"user": "leo"},
    )

    assert inserted_id == "generated-id"
    assert len(fake_collection.inserted) == 1

    doc = fake_collection.inserted[0]
    assert doc["image_data"] == "image-bytes"
    assert doc["processed"] is False
    assert isinstance(doc["created_at"], datetime)
    assert doc["user"] == "leo"


def test_get_snapshot_by_id_raw_invalid_id_returns_none(fake_collection):
    """Invalid ObjectId strings should return None instead of raising."""
    result = db_service.get_snapshot_by_id_raw("bad")
    assert result is None
    assert fake_collection.last_query is None


def test_get_snapshot_by_id_raw_fetches_document(fake_collection):
    """Valid ids should be converted and queried."""
    oid = ObjectId()
    fake_collection.next_result = {"_id": oid, "value": 42}

    result = db_service.get_snapshot_by_id_raw(str(oid))
    assert result == {"_id": oid, "value": 42}
    assert fake_collection.last_query == {"_id": oid}


def test_get_snapshot_view_pending(monkeypatch):
    """Pending documents should have pending status and ISO timestamps."""
    oid = ObjectId()
    created_at = datetime(2024, 1, 1, 12, 0, 0)
    monkeypatch.setattr(
        db_service,
        "get_snapshot_by_id_raw",
        lambda _sid: {
            "_id": oid,
            "processed": False,
            "created_at": created_at,
        },
    )

    view = db_service.get_snapshot_view(str(oid))
    assert view["id"] == str(oid)
    assert view["status"] == "pending"
    assert view["processed"] is False
    assert view["created_at"] == created_at.isoformat()


def test_get_snapshot_view_done_with_error(monkeypatch):
    """Processed documents with error field become error status."""
    oid = ObjectId()
    processed_at = datetime(2024, 1, 1, 12, 5, 0)
    monkeypatch.setattr(
        db_service,
        "get_snapshot_by_id_raw",
        lambda _sid: {
            "_id": oid,
            "processed": True,
            "processed_at": processed_at,
            "mood": "happy",
            "error": "boom",
        },
    )

    view = db_service.get_snapshot_view(str(oid))
    assert view["status"] == "error"
    assert view["processed"] is True
    assert view["processed_at"] == processed_at.isoformat()
    assert view["mood"] == "happy"
    assert view["error"] == "boom"
