"""Database connection helpers for the machine-learning client."""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "study_mood_tracker")

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return a cached MongoDB client instance."""
    global _client

    if _client is None:
        if not MONGO_URI:
            raise RuntimeError("MONGO_URI is not set. Please configure it in your .env file.")
        _client = MongoClient(MONGO_URI)

    return _client


def get_db():
    """Return the default MongoDB database object."""
    return get_client()[MONGO_DB_NAME]


def get_collection(name: str):
    """Return a collection object from the default database."""
    return get_db()[name]
