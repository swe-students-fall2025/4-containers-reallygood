"""Flask API for creating and retrieving mood snapshot documents."""
from flask import Flask, jsonify, request
from db_service import create_mood_snapshot, get_snapshot_view

app = Flask(__name__)


@app.route("/api/snapshots", methods=["POST"])
def api_create_snapshot():
    """Create a new snapshot from the uploaded image data."""
    data = request.get_json() or {}
    image_data = data.get("image_data")

    if not image_data:
        return jsonify({"error": "image_data is required"}), 400

    snapshot_id = create_mood_snapshot(image_data)
    return jsonify({"id": snapshot_id}), 201


@app.route("/api/snapshots/<snapshot_id>", methods=["GET"])
def api_get_snapshot(snapshot_id: str):
    """Return the current processing status and result for a snapshot."""
    view = get_snapshot_view(snapshot_id)
    if not view:
        return jsonify({"error": "snapshot not found"}), 404

    return jsonify(view), 200
