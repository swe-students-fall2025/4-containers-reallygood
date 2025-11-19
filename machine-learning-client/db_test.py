"""Manual test script for verifying the ML client's MongoDB connection."""

# machine-learning-client/db_manual_check.py
from datetime import datetime
from ml_db import get_collection


def main():
    """Insert a test document and print recent documents from the collection."""
    snapshots = get_collection("mood_snapshots")

    doc = {
        "test": True,
        "note": "inserted from db_test.py",
        "processed": False,
        "created_at": datetime.utcnow(),
    }

    result = snapshots.insert_one(doc)
    print("Inserted ID:", result.inserted_id)

    print("Latest docs in mood_snapshots:")
    for d in snapshots.find().sort("created_at", -1).limit(5):
        print(d)


if __name__ == "__main__":
    main()
