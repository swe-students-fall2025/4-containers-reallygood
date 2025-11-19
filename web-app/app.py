"""
Web Dashboard - Flask Application

Provides a user-facing interface to view activity and analysis results
produced by the Study Mood Analyzer machine learning client.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

from db_service import (
    create_mood_snapshot,
    get_snapshot_view,
    list_recent_snapshots,
)
from db import get_database


# -----------------------------------------------------------
# Logging (same pattern as mood_analyzer.py)
# -----------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------
# Create Flask App
# -----------------------------------------------------------
def create_app() -> Flask:
    """
    Flask application factory.
    Loads configuration, connects to MongoDB, and registers routes.

    Returns:
        Configured Flask application instance.
    """
    load_dotenv()  # Load .env file

    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Get MongoDB connection string
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise RuntimeError("MONGODB_URI is not set in environment variables.")

    logger.info("Connecting to MongoDB...")
    db = get_database(mongodb_uri)
    app.config["DB"] = db
    logger.info("MongoDB connection established.")

    # -------------------------------------------------------
    # HEALTH CHECK (DO NOT REMOVE - tests depend on this!)
    # -------------------------------------------------------
    @app.route("/", methods=["GET"])
    def index() -> str:
        """
        Health check route.
        Returns plain text (required by automated tests).
        """
        return "Mood dashboard is running!"

    # -------------------------------------------------------
    # HTML FRONTEND DASHBOARD
    # -------------------------------------------------------
    @app.route("/dashboard", methods=["GET"])
    def dashboard_page() -> str:
        """
        Render the HTML dashboard for humans to view.
        """
        return render_template("dashboard.html")

    # -------------------------------------------------------
    # API: Create a new snapshot (POST)
    # -------------------------------------------------------
    @app.route("/api/snapshots", methods=["POST"])
    def api_create_snapshot():
        """
        Create a new mood snapshot entry and return its ID.

        Expected JSON:
            { "image_data": "<base64 string>" }
        """
        try:
            payload = app.request.get_json()
            if not payload or "image_data" not in payload:
                return jsonify({"error": "Missing image_data"}), 400

            snapshot_id = create_mood_snapshot(app.config["DB"], payload["image_data"])
            return jsonify({"id": str(snapshot_id)})

        except Exception as err:  # pragma: no cover
            logger.exception("Error creating snapshot: %s", err)
            return jsonify({"error": "failed to create snapshot"}), 500

    # -------------------------------------------------------
    # API: Get status of a snapshot (GET)
    # -------------------------------------------------------
    @app.route("/api/snapshots/<snapshot_id>", methods=["GET"])
    def api_get_snapshot(snapshot_id: str):
        """
        Return details about a specific snapshot.

        Args:
            snapshot_id: ID string from MongoDB.

        Returns:
            JSON snapshot view.
        """
        try:
            snapshot_view = get_snapshot_view(app.config["DB"], snapshot_id)
            if snapshot_view is None:
                return jsonify({"error": "not found"}), 404

            return jsonify(snapshot_view)

        except Exception as err:  # pragma: no cover
            logger.exception("Error fetching snapshot: %s", err)
            return jsonify({"error": "failed to fetch snapshot"}), 500

    # -------------------------------------------------------
    # API: List recent snapshots (GET)
    # -------------------------------------------------------
    @app.route("/api/snapshots", methods=["GET"])
    def api_list_snapshots():
        """
        Return up to the 20 most recent snapshots.

        Returns:
            JSON: { count: N, items: [...] }
        """
        try:
            snapshots: List[Dict[str, Any]] = list_recent_snapshots(app.config["DB"])
            return jsonify({"count": len(snapshots), "items": snapshots})

        except Exception as err:  # pragma: no cover
            logger.exception("Error listing snapshots: %s", err)
            return jsonify({"error": "failed to list snapshots"}), 500

    return app


# -----------------------------------------------------------
# Main entry point
# -----------------------------------------------------------
def main() -> None:
    """
    Main entry point for local development.
    """
    app = create_app()

    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port_str = os.getenv("FLASK_RUN_PORT", "5000")

    try:
        port = int(port_str)
    except ValueError:
        logger.warning("Invalid FLASK_RUN_PORT value '%s'. Using default 5000.", port_str)
        port = 5000

    logger.info("Starting Flask server on http://%s:%s", host, port)
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    main()
