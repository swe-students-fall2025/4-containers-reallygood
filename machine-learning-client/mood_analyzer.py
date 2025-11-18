"""
Mood Analyzer - Machine Learning Client
Analyzes mood data received from the web application and stores results in MongoDB.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

import base64
import urllib.request

import numpy as np
import cv2
import onnxruntime as ort
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MoodAnalyzer:
    """Analyzes facial expressions to determine mood/emotion."""

    # Emotion labels for the FER+ model
    EMOTIONS = [
        "neutral",
        "happiness",
        "surprise",
        "sadness",
        "anger",
        "disgust",
        "fear",
    ]

    def __init__(
        self, mongodb_uri: str, model_path: str = "models/emotion-ferplus-8.onnx"
    ):
        """
        Initialize the MoodAnalyzer.

        Args:
            mongodb_uri: MongoDB connection string.
            model_path: Path to the ONNX emotion recognition model.
        """
        self.mongodb_uri = mongodb_uri
        self.model_path = model_path
        self.db = None
        self.session = None

        # Initialize MongoDB connection
        self._connect_to_mongodb()

        # Load ONNX model
        self._load_model()

        # Build path to Haar cascade file without using cv2.data
        cv2_base_dir = os.path.dirname(cv2.__file__)
        cascade_path = os.path.join(
            cv2_base_dir,
            "data",
            "haarcascades",
            "haarcascade_frontalface_default.xml",
        )

        # Load face detection model
        self.face_cascade = cv2.CascadeClassifier(  # pylint: disable=no-member
            cascade_path
        )

    def _connect_to_mongodb(self) -> None:
        """Establish connection to MongoDB."""
        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                logger.info(
                    "Connecting to MongoDB (attempt %d/%d)...",
                    attempt + 1,
                    max_retries,
                )
                client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
                client.admin.command("ping")
                self.db = client.study_mood_tracker
                logger.info("Successfully connected to MongoDB")
                return
            except ConnectionFailure as err:
                logger.error("Failed to connect to MongoDB: %s", err)
                if attempt < max_retries - 1:
                    logger.info("Retrying in %d seconds...", retry_delay)
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Exiting.")
                    raise

    def _load_model(self) -> None:
        """Load the ONNX emotion recognition model."""
        # Create models directory if it doesn't exist
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        # Check if model exists, if not download it
        if not os.path.exists(self.model_path):
            logger.info("Model not found. Downloading emotion-ferplus-8 model...")
            self._download_model()

        # Load the ONNX model
        self.session = ort.InferenceSession(self.model_path)
        logger.info("ONNX model loaded successfully")

    def _download_model(self) -> None:
        """Download the pre-trained emotion recognition model."""
        model_url = (
            "https://github.com/onnx/models/raw/main/validated/vision/"
            "body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
        )
        logger.info("Downloading model from %s...", model_url)
        urllib.request.urlretrieve(model_url, self.model_path)
        logger.info("Model downloaded successfully")

    def preprocess_face(self, face_img: np.ndarray) -> np.ndarray:
        """
        Preprocess face image for emotion recognition.

        Args:
            face_img: Face image as numpy array.

        Returns:
            Preprocessed image as numpy array of shape (1, 1, 64, 64).
        """
        # Resize to 64x64 (model input size)
        face_resized = cv2.resize(face_img, (64, 64))  # pylint: disable=no-member

        # Convert to grayscale if needed
        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(  # pylint: disable=no-member
                face_resized,
                cv2.COLOR_BGR2GRAY,  # pylint: disable=no-member
            )
        else:
            face_gray = face_resized

        # Normalize pixel values
        face_normalized = face_gray.astype(np.float32) / 255.0

        # Add batch and channel dimensions
        face_input = np.expand_dims(np.expand_dims(face_normalized, axis=0), axis=0)

        return face_input

    def detect_faces(self, image: np.ndarray) -> List[tuple]:
        """
        Detect faces in an image.

        Args:
            image: Input image as numpy array (BGR).

        Returns:
            List of face coordinates (x, y, w, h).
        """
        gray = cv2.cvtColor(  # pylint: disable=no-member
            image,
            cv2.COLOR_BGR2GRAY,  # pylint: disable=no-member
        )
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
        )
        return list(faces)

    def predict_emotion(self, face_img: np.ndarray) -> Dict[str, float]:
        """
        Predict emotion from face image.

        Args:
            face_img: Face image as numpy array.

        Returns:
            Dictionary of emotion probabilities.
        """
        # Preprocess the face
        input_data = self.preprocess_face(face_img)

        # Run inference
        input_name = self.session.get_inputs()[0].name  # type: ignore[union-attr]
        output_name = self.session.get_outputs()[0].name  # type: ignore[union-attr]
        result = self.session.run(  # type: ignore[union-attr]
            [output_name],
            {input_name: input_data},
        )

        # Get probabilities
        probabilities = result[0][0]

        # Create emotion dictionary
        emotion_dict = {
            emotion: float(prob) for emotion, prob in zip(self.EMOTIONS, probabilities)
        }

        return emotion_dict

    def categorize_mood(self, emotion_dict: Dict[str, float]) -> str:
        """
        Categorize overall mood based on emotions.

        Args:
            emotion_dict: Dictionary of emotion probabilities.

        Returns:
            Mood category: 'happy', 'neutral', 'unhappy', 'focused', or 'unknown'.
        """
        if not emotion_dict:
            return "unknown"

        # Get dominant emotion
        dominant_emotion = max(emotion_dict, key=emotion_dict.get)

        # Map emotions to mood categories
        if dominant_emotion in ["happiness"]:
            return "happy"
        if dominant_emotion in ["sadness", "anger", "disgust", "fear"]:
            return "unhappy"
        if dominant_emotion in ["surprise"]:
            return "focused"
        # neutral
        return "neutral"

    # ---------- helper methods for snapshot processing ----------

    def _decode_image(self, image_data: str) -> Optional[np.ndarray]:
        """Decode base64 image string to OpenCV BGR image."""
        img_bytes = base64.b64decode(image_data.split(",")[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(  # pylint: disable=no-member
            nparr,
            cv2.IMREAD_COLOR,  # pylint: disable=no-member
        )
        return image

    def _update_snapshot_with_face(
        self,
        snapshot_id,
        emotions: Dict[str, float],
        mood: str,
    ) -> None:
        """Update database when a face is detected and mood is computed."""
        self.db.mood_snapshots.update_one(
            {"_id": snapshot_id},
            {
                "$set": {
                    "processed": True,
                    "face_detected": True,
                    "emotions": emotions,
                    "mood": mood,
                    "processed_at": datetime.utcnow(),
                }
            },
        )
        logger.info(
            "Processed snapshot %s: mood=%s, emotions=%s",
            snapshot_id,
            mood,
            emotions,
        )

    def _update_snapshot_no_face(self, snapshot_id) -> None:
        """Update database when no face is detected."""
        self.db.mood_snapshots.update_one(
            {"_id": snapshot_id},
            {
                "$set": {
                    "processed": True,
                    "face_detected": False,
                    "processed_at": datetime.utcnow(),
                }
            },
        )
        logger.info("No face detected in snapshot %s", snapshot_id)

    def _mark_snapshot_error(self, snapshot_id, error_msg: str) -> None:
        """Mark snapshot as processed with error."""
        self.db.mood_snapshots.update_one(
            {"_id": snapshot_id},
            {
                "$set": {
                    "processed": True,
                    "error": error_msg,
                    "processed_at": datetime.utcnow(),
                }
            },
        )
        logger.error("Error processing snapshot %s: %s", snapshot_id, error_msg)

    # ---------- main image processing loop ----------

    def process_pending_images(self) -> None:
        """Process images pending analysis from the database."""
        pending = self.db.mood_snapshots.find({"processed": False}).limit(10)

        for snapshot in pending:
            snapshot_id = snapshot["_id"]
            image_data = snapshot.get("image_data")
            if not image_data:
                logger.info(
                    "Snapshot %s has no image_data, skipping",
                    snapshot_id,
                )
                continue

            try:
                image = self._decode_image(image_data)
                if image is None:
                    self._mark_snapshot_error(snapshot_id, "Failed to decode image")
                    continue

                faces = self.detect_faces(image)

                if not faces:
                    self._update_snapshot_no_face(snapshot_id)
                    continue

                # Use the first detected face
                x, y, w, h = faces[0]
                face_img = image[y : y + h, x : x + w]

                emotions = self.predict_emotion(face_img)
                mood = self.categorize_mood(emotions)

                self._update_snapshot_with_face(snapshot_id, emotions, mood)

            except (ValueError, TypeError, RuntimeError, ConnectionFailure) as err:
                self._mark_snapshot_error(snapshot_id, str(err))

    def run(self) -> None:
        """Main loop to continuously process pending images."""
        logger.info("Starting MoodAnalyzer...")

        while True:
            try:
                self.process_pending_images()
                time.sleep(2)  # Check for new images every 2 seconds
            except KeyboardInterrupt:
                logger.info("Shutting down MoodAnalyzer...")
                break
            except (RuntimeError, ConnectionFailure, ValueError, TypeError) as err:
                logger.error("Error in main loop: %s", err)
                time.sleep(5)


def main() -> None:
    """Main entry point."""
    mongodb_uri = os.getenv(
        "MONGODB_URI",
        "mongodb://localhost:27017/study_mood_tracker",
    )

    analyzer = MoodAnalyzer(mongodb_uri)
    analyzer.run()


if __name__ == "__main__":
    main()
