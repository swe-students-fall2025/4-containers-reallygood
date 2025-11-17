"""
Mood Analyzer - Machine Learning Client
Analyzes mood data received from the web application and stores results in MongoDB
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List
import numpy as np
import cv2
import onnxruntime as ort
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MoodAnalyzer:
    """Analyzes facial expressions to determine mood/emotion"""

    # Emotion labels for the FER+ model
    EMOTIONS = ["neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear"]

    def __init__(self, mongodb_uri: str, model_path: str = "models/emotion-ferplus-8.onnx"):
        """
        Initialize the MoodAnalyzer

        Args:
            mongodb_uri: MongoDB connection string
            model_path: Path to the ONNX emotion recognition model
        """
        self.mongodb_uri = mongodb_uri
        self.model_path = model_path
        self.db = None
        self.session = None

        # Initialize MongoDB connection
        self._connect_to_mongodb()

        # Load ONNX model
        self._load_model()

        # Load face detection model
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def _connect_to_mongodb(self):
        """Establish connection to MongoDB"""
        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MongoDB (attempt {attempt + 1}/{max_retries})...")
                client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
                client.admin.command("ping")
                self.db = client.study_mood_tracker
                logger.info("Successfully connected to MongoDB")
                return
            except ConnectionFailure as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Exiting.")
                    raise

    def _load_model(self):
        """Load the ONNX emotion recognition model"""
        try:
            # Create models directory if it doesn't exist
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

            # Check if model exists, if not download it
            if not os.path.exists(self.model_path):
                logger.info("Model not found. Downloading emotion-ferplus-8 model...")
                self._download_model()

            # Load the ONNX model
            self.session = ort.InferenceSession(self.model_path)
            logger.info("ONNX model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise

    def _download_model(self):
        """Download the pre-trained emotion recognition model"""
        import urllib.request

        model_url = "https://github.com/onnx/models/raw/main/validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
        try:
            logger.info(f"Downloading model from {model_url}...")
            urllib.request.urlretrieve(model_url, self.model_path)
            logger.info("Model downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            raise

    def preprocess_face(self, face_img: np.ndarray) -> np.ndarray:
        """
        Preprocess face image for emotion recognition

        Args:
            face_img: Face image as numpy array

        Returns:
            Preprocessed image
        """
        # Resize to 64x64 (model input size)
        face_resized = cv2.resize(face_img, (64, 64))

        # Convert to grayscale if needed
        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized

        # Normalize pixel values
        face_normalized = face_gray.astype(np.float32) / 255.0

        # Add batch and channel dimensions
        face_input = np.expand_dims(np.expand_dims(face_normalized, axis=0), axis=0)

        return face_input

    def detect_faces(self, image: np.ndarray) -> List[tuple]:
        """
        Detect faces in an image

        Args:
            image: Input image as numpy array

        Returns:
            List of face coordinates (x, y, w, h)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        return faces

    def predict_emotion(self, face_img: np.ndarray) -> Dict[str, float]:
        """
        Predict emotion from face image

        Args:
            face_img: Face image as numpy array

        Returns:
            Dictionary of emotion probabilities
        """
        try:
            # Preprocess the face
            input_data = self.preprocess_face(face_img)

            # Run inference
            input_name = self.session.get_inputs()[0].name
            output_name = self.session.get_outputs()[0].name
            result = self.session.run([output_name], {input_name: input_data})

            # Get probabilities
            probabilities = result[0][0]

            # Create emotion dictionary
            emotion_dict = {
                emotion: float(prob) for emotion, prob in zip(self.EMOTIONS, probabilities)
            }

            return emotion_dict
        except Exception as e:
            logger.error(f"Error predicting emotion: {e}")
            return {}

    def categorize_mood(self, emotion_dict: Dict[str, float]) -> str:
        """
        Categorize overall mood based on emotions

        Args:
            emotion_dict: Dictionary of emotion probabilities

        Returns:
            Mood category: 'happy', 'neutral', 'unhappy', 'focused'
        """
        if not emotion_dict:
            return "unknown"

        # Get dominant emotion
        dominant_emotion = max(emotion_dict, key=emotion_dict.get)

        # Map emotions to mood categories
        if dominant_emotion in ["happiness"]:
            return "happy"
        elif dominant_emotion in ["sadness", "anger", "disgust", "fear"]:
            return "unhappy"
        elif dominant_emotion in ["surprise"]:
            return "focused"
        else:  # neutral
            return "neutral"

    def process_pending_images(self):
        """Process images pending analysis from the database"""
        try:
            # Find pending images
            pending = self.db.mood_snapshots.find({"processed": False}).limit(10)

            for snapshot in pending:
                try:
                    # Get image data
                    image_data = snapshot.get("image_data")
                    if not image_data:
                        continue

                    # Decode base64 image
                    import base64

                    img_bytes = base64.b64decode(image_data.split(",")[1])
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    # Detect faces
                    faces = self.detect_faces(image)

                    if len(faces) > 0:
                        # Use the first detected face
                        x, y, w, h = faces[0]
                        face_img = image[y : y + h, x : x + w]

                        # Predict emotion
                        emotions = self.predict_emotion(face_img)
                        mood = self.categorize_mood(emotions)

                        # Update database
                        self.db.mood_snapshots.update_one(
                            {"_id": snapshot["_id"]},
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
                            f"Processed snapshot {snapshot['_id']}: mood={mood}, "
                            f"emotions={emotions}"
                        )
                    else:
                        # No face detected
                        self.db.mood_snapshots.update_one(
                            {"_id": snapshot["_id"]},
                            {
                                "$set": {
                                    "processed": True,
                                    "face_detected": False,
                                    "processed_at": datetime.utcnow(),
                                }
                            },
                        )
                        logger.info(f"No face detected in snapshot {snapshot['_id']}")

                except Exception as e:
                    logger.error(f"Error processing snapshot {snapshot['_id']}: {e}")
                    # Mark as processed with error
                    self.db.mood_snapshots.update_one(
                        {"_id": snapshot["_id"]},
                        {
                            "$set": {
                                "processed": True,
                                "error": str(e),
                                "processed_at": datetime.utcnow(),
                            }
                        },
                    )

        except Exception as e:
            logger.error(f"Error in process_pending_images: {e}")

    def run(self):
        """Main loop to continuously process pending images"""
        logger.info("Starting MoodAnalyzer...")

        while True:
            try:
                self.process_pending_images()
                time.sleep(2)  # Check for new images every 2 seconds
            except KeyboardInterrupt:
                logger.info("Shutting down MoodAnalyzer...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)


def main():
    """Main entry point"""
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/study_mood_tracker")

    analyzer = MoodAnalyzer(mongodb_uri)
    analyzer.run()


if __name__ == "__main__":
    main()