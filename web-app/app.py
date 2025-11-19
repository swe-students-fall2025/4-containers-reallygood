"""
Web Dashboard - Flask Application

Provides a user interface and JSON API for viewing mood analysis results
produced by the ML client.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from db_service import (
    create_mood_snapshot,
    get_snapshot_view,
)
from db import get_collection, get_db


# -----------------------------
# Logging Setup
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------
# Flask App Factory
# -----------------------------
def create_app() -> Flask:
    """
    Create and configure the Flask web application.
    """
    load_dotenv()
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Ensure MongoDB URI exists
    if os.getenv("MONGODB_URI") is None:
        raise RuntimeError("MONGODB_URI not set in environment variables.")

    # Save DB handle into app config
    app.config["DB"] = get_db()

    # -------------------------
    # Health Check (for tests)
    # -------------------------
    @app.route("/", methods=["GET"])
    def index() -> str:
        return "Mood dashboard is running!"

    # -------------------------
    # Frontend HTML Dashboard
    # -------------------------
    @app.route("/dashboard", methods=["GET"])
    def dashboard_page() -> str:
        return render_template("dashboard.html")

    # -------------------------
    # API: Create a Snapshot
    # -------------------------
    @app.route("/api/snapshots", methods=["POST"])
    def api_create_snapshot():
        data = request.get_json()
        if not data or "image_data" not in data:
            return jsonify({"error": "missing image_data"}), 400

        snapshot_id = create_mood_snapshot(data["image_data"])
        return jsonify({"id": snapshot_id})

    # -------------------------
    # API: Get Snapshot by ID
    # -------------------------
    @app.route("/api/snapshots/<snapshot_id>", methods=["GET"])
    def api_get_snapshot(snapshot_id: str):
        snapshot_view = get_snapshot_view(snapshot_id)
        if snapshot_view is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(snapshot_view)

    # -------------------------
    # API: List Recent Snapshots
    # -------------------------
    @app.route("/api/snapshots", methods=["GET"])
    def api_list_snapshots():
        """
        Returns the 20 most recent snapshots.
        Matches the behavior expected in test_api_snapshots_empty.
        """
        col = get_collection("mood_snapshots")  # <--- THIS MATCHES YOUR TEST MOCK
        cursor = col.find().sort("created_at", -1).limit(20)

        items: List[Dict[str, Any]] = []
        for doc in cursor:
            item = {
                "id": str(doc.get("_id")),
                "processed": bool(doc.get("processed", False)),
                "mood": doc.get("mood"),
                "face_detected": doc.get("face_detected"),
                "created_at": doc.get("created_at"),
            }

            # Create synthetic status for table display
            if not item["processed"]:
                item["status"] = "pending"
            else:
                item["status"] = "done"

            items.append(item)

        return jsonify({"count": len(items), "items": items})

    return app


# -----------------------------
# Main Entry Point
# -----------------------------
def main():
    app = create_app()
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5001"))

    logger.info("Starting server on %s:%s", host, port)
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    main()
