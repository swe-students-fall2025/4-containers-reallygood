# web-app/tests/test_db_service.py
"""Tests for the db_service helper functions."""
from datetime import datetime

import pytest  # pylint: disable=import-error
import db_service  # pylint: disable=import-error


@pytest.fixture
def fake_collection(monkeypatch):
    """Provide a fake Mongo collection and patch get_collection."""

    class FakeCollection:
        def __init__(self):
            self.inserted_docs = []
            self.queries = []
            self.next_find_one_result = None

        def insert_one(self, doc):
            """Simulate insert_one and remember the document."""
            self.inserted_docs.append(doc)

            class Result:
                inserted_id = "fake-id"

            return Result()

        def find_one(self, query):
            """Simulate find_one by returning a pre-set document."""
            self.queries.append(query)
            return self.next_find_one_result

    collection = FakeCollection()

    def fake_get_collection(name: str):  # pylint: disable=unused-argument
        assert name == "mood_snapshots"
        return collection

    monkeypatch.setattr(db_service, "get_collection", fake_get_collection)

    return collection


# ---------- create_mood_snapshot ----------


def test_create_mood_snapshot_inserts_document(fake_collection):
    """create_mood_snapshot 应该插入文档并返回字符串 id。"""
    snapshot_id = db_service.create_mood_snapshot(
        "base64-data",
        {"user_id": "u123", "extra": 42},
    )

    assert snapshot_id == "fake-id"

    assert len(fake_collection.inserted_docs) == 1
    doc = fake_collection.inserted_docs[0]

    assert doc["image_data"] == "base64-data"
    assert doc["processed"] is False
    assert isinstance(doc["created_at"], datetime)
    assert doc["user_id"] == "u123"
    assert doc["extra"] == 42


# ---------- get_snapshot_by_id_raw ----------


def test_get_snapshot_by_id_raw_invalid_id_returns_none(
    fake_collection,
):  # pylint: disable=unused-argument
    """Wrong ObjectId String Should return None。"""
    result = db_service.get_snapshot_by_id_raw("not-a-valid-object-id")
    assert result is None


def test_get_snapshot_by_id_raw_valid_id(fake_collection):
    """Good id shoud pass collection.find_one and get the document"""
    fake_doc = {"_id": "some-oid", "mood": "happy"}
    fake_collection.next_find_one_result = fake_doc

    result = db_service.get_snapshot_by_id_raw("651111111111111111111111")

    assert result is fake_doc
    query = fake_collection.queries[0]
    assert "_id" in query
    assert isinstance(query["_id"], db_service.ObjectId)


# ---------- get_snapshot_view ----------


def test_get_snapshot_view_not_found(monkeypatch):
    """If there is no document then return None。"""
    monkeypatch.setattr(
        db_service,
        "get_snapshot_by_id_raw",
        lambda snapshot_id: None,  # pylint: disable=unused-argument
    )

    assert db_service.get_snapshot_view("whatever") is None


def test_get_snapshot_view_pending(monkeypatch):
    """If process is False then the status='pending', there is no processed_at。"""
    now = datetime.utcnow()
    doc = {
        "_id": "id-pending",
        "created_at": now,
    }

    monkeypatch.setattr(
        db_service,
        "get_snapshot_by_id_raw",
        lambda snapshot_id: doc,  # pylint: disable=unused-argument
    )

    view = db_service.get_snapshot_view("id-pending")

    assert view["id"] == "id-pending"
    assert view["processed"] is False
    assert view["created_at"] == now.isoformat()
    assert "processed_at" not in view
    assert view["status"] == "pending"


def test_get_snapshot_view_done(monkeypatch):
    """When dealing with error, the status should be 'done'"""
    created = datetime.utcnow()
    processed = datetime.utcnow()
    doc = {
        "_id": "id-done",
        "processed": True,
        "created_at": created,
        "processed_at": processed,
        "mood": "happy",
        "emotions": {"happy": 0.9},
        "face_detected": True,
    }

    monkeypatch.setattr(
        db_service,
        "get_snapshot_by_id_raw",
        lambda snapshot_id: doc,  # pylint: disable=unused-argument
    )

    view = db_service.get_snapshot_view("id-done")

    assert view["id"] == "id-done"
    assert view["processed"] is True
    assert view["created_at"] == created.isoformat()
    assert view["processed_at"] == processed.isoformat()
    assert view["mood"] == "happy"
    assert view["emotions"]["happy"] == 0.9
    assert view["face_detected"] is True
    assert "error" not in view
    assert view["status"] == "done"


def test_get_snapshot_view_error(monkeypatch):
    """
    When the process is True but there is error, 
    the status should be 'error', and view should have error
    """
    doc = {
        "_id": "id-error",
        "processed": True,
        "created_at": datetime.utcnow(),
        "processed_at": datetime.utcnow(),
        "error": "something went wrong",
    }

    monkeypatch.setattr(
        db_service,
        "get_snapshot_by_id_raw",
        lambda snapshot_id: doc,  # pylint: disable=unused-argument
    )

    view = db_service.get_snapshot_view("id-error")

    assert view["id"] == "id-error"
    assert view["processed"] is True
    assert view["status"] == "error"
    assert view["error"] == "something went wrong"
