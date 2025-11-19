"""End-to-end test helper for creating and polling mood snapshots."""
# web-app/test_face_snapshot.py

import base64
import mimetypes
import time

import requests

API_BASE = "http://127.0.0.1:5000"


def encode_image_to_data_url(path: str) -> str:
    """Encode a local image file as a base64 data URL."""
    mime, _ = mimetypes.guess_type(path)
    if mime is None:
        mime = "image/jpeg"

    with open(path, "rb") as f:
        img_bytes = f.read()

    b64_str = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64_str}"


def main():
    """Create a snapshot and poll its processing status."""
    image_path = "/Users/gavinguo/Desktop/WechatIMG427.jpg"
    data_url = encode_image_to_data_url(image_path)
    print("Encoded image length:", len(data_url))

    resp = requests.post(
        f"{API_BASE}/api/snapshots",
        json={"image_data": data_url},
        timeout=5,
    )
    resp.raise_for_status()
    snapshot_id = resp.json()["id"]
    print("Created snapshot:", snapshot_id)

    for attempt in range(10):
        time.sleep(2)
        r = requests.get(
            f"{API_BASE}/api/snapshots/{snapshot_id}",
            timeout=5,
        )
        r.raise_for_status()
        doc = r.json()
        print(
            f"[Attempt {attempt+1}] status={doc.get('status')}, processed={doc.get('processed')}"
        )
        print(doc)

        if doc.get("status") != "pending":
            break

    else:
        print("Still pending after 10 attempts.")


if __name__ == "__main__":
    main()
