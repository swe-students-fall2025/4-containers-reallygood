# web-app/db_service.py
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from db import get_collection


def create_mood_snapshot(image_data: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Insert a snapshot to be proceed: 
    - image_data: base64 string
    - processed: False
    - created_at: current time
    
    Return id
    """
    col = get_collection("mood_snapshots")

    doc: Dict[str, Any] = {
        "image_data": image_data,
        "processed": False,
        "created_at": datetime.utcnow(),
    }
    if metadata:
        doc.update(metadata)

    result = col.insert_one(doc)
    return str(result.inserted_id)


def get_snapshot_by_id_raw(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """
    Get original data by id
    """
    col = get_collection("mood_snapshots")

    try:
        oid = ObjectId(snapshot_id)
    except Exception:
        return None

    doc = col.find_one({"_id": oid})
    return doc


def get_snapshot_view(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """
    Parse Data
    Result: 
      - id
      - status: "pending" / "done" / "error"
      - processed (bool)
      - created_at / processed_at (ISO 字符串)
      - mood / emotions / face_detected / error
    """
    doc = get_snapshot_by_id_raw(snapshot_id)
    if not doc:
        return None

    view: Dict[str, Any] = {}

    view["id"] = str(doc["_id"])

    processed = bool(doc.get("processed", False))
    view["processed"] = processed

    created_at = doc.get("created_at")
    if isinstance(created_at, datetime):
        view["created_at"] = created_at.isoformat()

    processed_at = doc.get("processed_at")
    if isinstance(processed_at, datetime):
        view["processed_at"] = processed_at.isoformat()

    if "mood" in doc:
        view["mood"] = doc["mood"]

    if "emotions" in doc:
        view["emotions"] = doc["emotions"]

    if "face_detected" in doc:
        view["face_detected"] = doc["face_detected"]

    error = doc.get("error")
    if error is not None:
        view["error"] = error

    if not processed:
        status = "pending"
    else:
        if error is not None:
            status = "error"
        else:
            status = "done"

    view["status"] = status

    return view
