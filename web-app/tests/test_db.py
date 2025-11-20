# """Tests for the MongoDB connection helpers in db.py."""
# import pytest  # pylint: disable=import-error

# import db  # pylint: disable=import-error


# class FakeCollection:
#     """Very small fake collection object used for testing."""

#     def __init__(self, name: str):
#         self.name = name


# class FakeDatabase:
#     """Very small fake database object used for testing."""

#     def __init__(self, name: str):
#         self.name = name
#         self._collections: dict[str, FakeCollection] = {}

#     def __getitem__(self, collection_name: str) -> FakeCollection:
#         if collection_name not in self._collections:
#             self._collections[collection_name] = FakeCollection(collection_name)
#         return self._collections[collection_name]


# class FakeClient:
#     """Fake MongoClient that records the URI and returns fake DB objects."""

#     def __init__(self, uri: str):
#         self.uri = uri
#         self._databases: dict[str, FakeDatabase] = {}

#     def __getitem__(self, db_name: str) -> FakeDatabase:
#         if db_name not in self._databases:
#             self._databases[db_name] = FakeDatabase(db_name)
#         return self._databases[db_name]


# def test_get_client_uses_configured_uri_and_caches(monkeypatch):
#     """get_client should use MONGODB_URI and cache the client instance."""
#     # Reset internal client and inject a fake MongoClient implementation.
#     monkeypatch.setattr(db, "_client", None)
#     monkeypatch.setattr(db, "MONGODB_URI", "mongodb://fake:27017/test_db")
#     monkeypatch.setattr(db, "MongoClient", FakeClient)

#     client1 = db.get_client()
#     client2 = db.get_client()

#     # Same object -> cached
#     assert isinstance(client1, FakeClient)
#     assert client1 is client2
#     # The fake client must have received the configured URI
#     assert client1.uri == "mongodb://fake:27017/test_db"


# def test_get_client_raises_when_uri_missing(monkeypatch):
#     """get_client should raise a RuntimeError if MONGODB_URI is empty."""
#     monkeypatch.setattr(db, "_client", None)
#     monkeypatch.setattr(db, "MONGODB_URI", "")

#     with pytest.raises(RuntimeError):
#         db.get_client()


# def test_get_db_returns_named_database(monkeypatch):
#     """get_db should return the database configured in DB_NAME."""
#     monkeypatch.setattr(db, "_client", None)
#     monkeypatch.setattr(db, "MONGODB_URI", "mongodb://fake:27017/another_db")
#     monkeypatch.setattr(db, "DB_NAME", "my_test_db")
#     monkeypatch.setattr(db, "MongoClient", FakeClient)

#     db_obj = db.get_db()
#     assert isinstance(db_obj, FakeDatabase)
#     assert db_obj.name == "my_test_db"


# def test_get_collection_returns_collection_from_db(monkeypatch):
#     """get_collection should return a collection object from the default DB."""
#     monkeypatch.setattr(db, "_client", None)
#     monkeypatch.setattr(db, "MONGODB_URI", "mongodb://fake:27017/collection_db")
#     monkeypatch.setattr(db, "DB_NAME", "collection_db")
#     monkeypatch.setattr(db, "MongoClient", FakeClient)

#     col = db.get_collection("mood_snapshots")
#     assert isinstance(col, FakeCollection)
#     assert col.name == "mood_snapshots"

#     # Same call again should return the same fake collection object
#     col2 = db.get_collection("mood_snapshots")
#     assert col2 is col
