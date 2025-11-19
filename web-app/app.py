"""
Web Dashboard - Flask Application

Provides a simple interface to view activity and analysis results
produced by the MoodAnalyzer machine learning client.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from dotenv import load_dotenv
load_dotenv()

# Configure logging (same pattern as mood_analyzer.py)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _get_database(mongodb_uri: str) -> Database:
    """
    Create and return a MongoDB database handle.

    This mirrors the retry behavior of the machine learning client so that
    the web app is robust to transient connection issues.

    Args:
        mongodb_uri: MongoDB connection string.

    Returns:
        A handle to the `study_mood_tracker` database.

    Raises:
        ConnectionFailure: If all connection attempts fail.
    """
    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            logger.info(
                "Connecting to MongoDB (attempt %d/%d).",
                attempt + 1,
                max_retries,
            )
            client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            # Simple health check
            client.admin.command("ping")
            db = client.study_mood_tracker
            logger.info("Successfully connected to MongoDB")
            return db
        except ConnectionFailure as err:  # pragma: no cover - error path tested via mocks
            logger.error("Failed to connect to MongoDB: %s", err)
            if attempt < max_retries - 1:
                logger.info("Retrying in %d seconds.", retry_delay)
                # Delay import here to keep function focused and easier to test
                import time

                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Giving up.")
                raise


def _serialize_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a MongoDB snapshot document into a JSON-serializable dict.

    Args:
        snapshot: Raw MongoDB document from the `mood_snapshots` collection.

    Returns:
        A dictionary suitable for JSON responses.
    """
    snapshot_id = snapshot.get("_id")
    # Avoid importing bson in this simple layer; str() works for ObjectId.
    snapshot_id_str = str(snapshot_id) if snapshot_id is not None else None

    return {
        "id": snapshot_id_str,
        "mood": snapshot.get("mood", "unknown"),
        "face_detected": snapshot.get("face_detected", False),
        "processed": snapshot.get("processed", False),
        "error": snapshot.get("error"),
        "created_at": snapshot.get("created_at"),
        "processed_at": snapshot.get("processed_at"),
    }


def create_app() -> Flask:
    """
    Flask application factory.

    Reads configuration from environment variables and sets up the
    MongoDB connection and routes.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    mongodb_uri = os.getenv(
        "MONGODB_URI",
        "mongodb://localhost:27017/study_mood_tracker",
    )
    db = _get_database(mongodb_uri)
    app.config["DB"] = db

    @app.route("/", methods=["GET"])
    def index() -> str:
        """
        Simple health-check route.

        Returns:
            Plain-text confirmation that the web app is running.
        """
        return "Mood dashboard is running!"

    @app.route("/api/snapshots", methods=["GET"])
    def api_snapshots():
        """
        Return recent mood snapshots as JSON.

        This endpoint can be consumed directly by a JavaScript-based
        dashboard, or rendered into HTML templates in the future.

        Returns:
            JSON response containing a list of serialized snapshots.
        """
        db_handle: Database = app.config["DB"]
        # Show the 20 most recent snapshots, newest first.
        cursor = (
            db_handle.mood_snapshots.find()
            .sort("created_at", -1)
            .limit(20)
        )
        snapshots: List[Dict[str, Any]] = [_serialize_snapshot(doc) for doc in cursor]
        return jsonify({"count": len(snapshots), "items": snapshots})

    return app


def main() -> None:
    """
    Main entry point.

    Creates the Flask application and runs the development server.
    """
    app = create_app()
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port_str = os.getenv("FLASK_RUN_PORT", "5000")
    try:
        port = int(port_str)
    except ValueError:
        logger.warning("Invalid FLASK_RUN_PORT=%s, falling back to 5000", port_str)
        port = 5000

    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    main()
