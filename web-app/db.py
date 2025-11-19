# web-app/db.py
import os

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/study_mood_tracker")

DB_NAME = os.getenv("MONGO_DB_NAME", "study_mood_tracker")

_client: MongoClient | None = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        if not MONGODB_URI:
            raise RuntimeError("MONGODB_URI not set. Please configure it in .env or docker-compose.")
        _client = MongoClient(MONGODB_URI)
    return _client


def get_db():
    return get_client()[DB_NAME]


def get_collection(name: str):
    return get_db()[name]
