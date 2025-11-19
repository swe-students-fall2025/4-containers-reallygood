"""Database connection helpers for the web application."""
# web-app/db.py
import os

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/study_mood_tracker")

DB_NAME = os.getenv("MONGO_DB_NAME", "study_mood_tracker")

_client: MongoClient | None = None

def get_client() -> MongoClient:
    """Return a cached MongoDB client instance."""
    global _client  # pylint: disable=global-statement
    if _client is None:
        if not MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI not set. Please configure it in .env or docker-compose."
            )
        _client = MongoClient(MONGODB_URI)
    return _client


def get_db():
    """Return the default MongoDB database object."""
    return get_client()[DB_NAME]


def get_collection(name: str):
    """Return a collection object from the default database."""
    return get_db()[name]
