# machine-learning-client/db_manual_check.py
from datetime import datetime
from db import get_collection


def main():
    trains = get_collection("Trains")

    doc = {
        "test": True,
        "note": "inserted from db_manual_check.py",
        "created_at": datetime.utcnow(),
    }

    result = trains.insert_one(doc)
    print("Inserted ID:", result.inserted_id)

    print("Latest docs in Trains:")
    for d in trains.find().sort("created_at", -1).limit(5):
        print(d)


if __name__ == "__main__":
    main()
