"""
Tests for MoodAnalyzer.
"""

from unittest.mock import patch, MagicMock

import base64
import cv2
import numpy as np
import pytest

from mood_analyzer import MoodAnalyzer


@pytest.fixture(name="mock_mongodb")
def mock_mongodb_fixture():
    """Return a mocked MongoDB database object."""
    with patch("mood_analyzer.MongoClient") as mock:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.study_mood_tracker = mock_db
        mock.return_value = mock_client
        yield mock_db


@pytest.fixture(name="mock_onnx_session")
def mock_onnx_session_fixture():
    """Return a mocked ONNX runtime session."""
    with patch("mood_analyzer.ort.InferenceSession") as mock:
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_output = MagicMock()
        mock_output.name = "output"
        mock_session.get_inputs.return_value = [mock_input]
        mock_session.get_outputs.return_value = [mock_output]
        mock_session.run.return_value = [
            np.array([[0.1, 0.6, 0.05, 0.1, 0.05, 0.05, 0.05]])
        ]
        mock.return_value = mock_session
        yield mock_session


@pytest.fixture(name="analyzer")
def analyzer_fixture(mock_mongodb, mock_onnx_session):
    """Create a MoodAnalyzer instance with mocked MongoDB and ONNX session."""
    _ = mock_mongodb
    _ = mock_onnx_session
    with patch("os.path.exists", return_value=True):
        return MoodAnalyzer("mongodb://test:27017/test")


# ---------- simple behavior tests ----------


def test_categorize_mood_happy(analyzer):
    """Categorize mood as happy when happiness dominates."""
    emotion_dict = {
        "neutral": 0.1,
        "happiness": 0.7,
        "surprise": 0.05,
        "sadness": 0.05,
        "anger": 0.05,
        "disgust": 0.025,
        "fear": 0.025,
    }
    mood = analyzer.categorize_mood(emotion_dict)
    assert mood == "happy"


def test_categorize_mood_unhappy(analyzer):
    """Categorize mood as unhappy when negative emotions dominate."""
    emotion_dict = {
        "neutral": 0.1,
        "happiness": 0.05,
        "surprise": 0.05,
        "sadness": 0.6,
        "anger": 0.1,
        "disgust": 0.05,
        "fear": 0.05,
    }
    mood = analyzer.categorize_mood(emotion_dict)
    assert mood == "unhappy"


def test_categorize_mood_neutral(analyzer):
    """Categorize mood as neutral when neutral dominates."""
    emotion_dict = {
        "neutral": 0.7,
        "happiness": 0.05,
        "surprise": 0.05,
        "sadness": 0.05,
        "anger": 0.05,
        "disgust": 0.05,
        "fear": 0.05,
    }
    mood = analyzer.categorize_mood(emotion_dict)
    assert mood == "neutral"


def test_categorize_mood_focused(analyzer):
    """Categorize mood as focused when surprise dominates."""
    emotion_dict = {
        "neutral": 0.1,
        "happiness": 0.05,
        "surprise": 0.7,
        "sadness": 0.05,
        "anger": 0.05,
        "disgust": 0.025,
        "fear": 0.025,
    }
    mood = analyzer.categorize_mood(emotion_dict)
    assert mood == "focused"


def test_categorize_mood_empty(analyzer):
    """Return unknown when emotion dictionary is empty."""
    mood = analyzer.categorize_mood({})
    assert mood == "unknown"


def test_preprocess_face(analyzer):
    """Preprocess a random face image to the expected shape and range."""
    face_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    processed = analyzer.preprocess_face(face_img)

    assert processed.shape == (1, 1, 64, 64)
    assert processed.dtype == np.float32
    assert processed.min() >= 0.0
    assert processed.max() <= 1.0


def test_detect_faces(analyzer):
    """Ensure detect_faces calls the cascade and returns a non-empty list."""
    image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    mock_cascade = MagicMock()
    mock_cascade.detectMultiScale.return_value = np.array([[100, 100, 200, 200]])
    analyzer.face_cascade = mock_cascade

    faces = analyzer.detect_faces(image)

    assert len(faces) > 0
    mock_cascade.detectMultiScale.assert_called_once()


def test_predict_emotion(analyzer, mock_onnx_session):
    """Predict emotion and ensure probabilities are well-formed."""
    face_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    emotions = analyzer.predict_emotion(face_img)

    assert isinstance(emotions, dict)
    assert len(emotions) == 7
    assert "happiness" in emotions
    assert all(0 <= prob <= 1 for prob in emotions.values())
    mock_onnx_session.run.assert_called_once()


# ---------- helper method and branch tests ----------


def test_load_model_downloads_when_missing():
    """Call _download_model when the model file does not exist."""
    with patch("mood_analyzer.MongoClient") as mock_client, patch(
        "mood_analyzer.ort.InferenceSession"
    ) as mock_session, patch("os.path.exists", return_value=False), patch.object(
        MoodAnalyzer,
        "_download_model",
    ) as mock_download, patch.object(
        MoodAnalyzer,
        "_ensure_cascade_file",
        return_value="/tmp/cascade.xml",
    ), patch("cv2.CascadeClassifier"):
        mock_db = MagicMock()
        mock_client.return_value.study_mood_tracker = mock_db
        mock_session.return_value = MagicMock()

        MoodAnalyzer("mongodb://test:27017/test")
        mock_download.assert_called_once()


def test_decode_image_valid(analyzer):
    """Decode a valid base64 image string to an OpenCV image."""
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    success, buf = cv2.imencode(".png", img)  # pylint: disable=no-member
    assert success
    img_bytes = buf.tobytes()
    b64_str = "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")

    decoded = analyzer._decode_image(b64_str)  # pylint: disable=protected-access
    assert decoded is not None
    assert decoded.shape[0] > 0 and decoded.shape[1] > 0


def test_update_snapshot_with_face_updates_db(analyzer):
    """Update snapshot with face_detected, emotions and mood."""
    emotions = {"happiness": 0.8}
    mood = "happy"

    analyzer._update_snapshot_with_face(  # pylint: disable=protected-access
        "snap1",
        emotions,
        mood,
    )

    analyzer.db.mood_snapshots.update_one.assert_called_once()
    args, _ = analyzer.db.mood_snapshots.update_one.call_args
    assert args[0] == {"_id": "snap1"}
    update_doc = args[1]
    assert update_doc["$set"]["face_detected"] is True
    assert update_doc["$set"]["emotions"] == emotions
    assert update_doc["$set"]["mood"] == mood
    assert update_doc["$set"]["processed"] is True


def test_update_snapshot_no_face_updates_db(analyzer):
    """Update snapshot when no face is detected."""
    analyzer._update_snapshot_no_face("snap2")  # pylint: disable=protected-access

    analyzer.db.mood_snapshots.update_one.assert_called_once()
    args, _ = analyzer.db.mood_snapshots.update_one.call_args
    assert args[0] == {"_id": "snap2"}
    update_doc = args[1]
    assert update_doc["$set"]["face_detected"] is False
    assert update_doc["$set"]["processed"] is True


def test_mark_snapshot_error_updates_db(analyzer):
    """Update snapshot with error information."""
    analyzer._mark_snapshot_error(  # pylint: disable=protected-access
        "snap3",
        "boom",
    )

    analyzer.db.mood_snapshots.update_one.assert_called_once()
    args, _ = analyzer.db.mood_snapshots.update_one.call_args
    assert args[0] == {"_id": "snap3"}
    update_doc = args[1]
    assert update_doc["$set"]["error"] == "boom"
    assert update_doc["$set"]["processed"] is True


class FakeCursor:
    """Minimal cursor-like object with limit() and iteration."""

    def __init__(self, docs):
        """Store the list of documents."""
        self._docs = docs

    def limit(self, _):
        """Return self to support chained limit()."""
        return self

    def __iter__(self):
        """Return an iterator over stored documents."""
        return iter(self._docs)


def test_process_pending_images_no_image_data(analyzer):
    """Skip snapshot when image_data is missing."""
    snapshot = {"_id": "snap-no-image", "processed": False}
    cursor = FakeCursor([snapshot])
    analyzer.db.mood_snapshots.find.return_value = cursor

    analyzer.process_pending_images()

    analyzer.db.mood_snapshots.update_one.assert_not_called()


def test_process_pending_images_decode_error(analyzer):
    """Mark snapshot error when image decoding fails."""
    snapshot = {
        "_id": "snap-decode-fail",
        "processed": False,
        "image_data": "data:image/png;base64,xxx",
    }
    cursor = FakeCursor([snapshot])
    analyzer.db.mood_snapshots.find.return_value = cursor

    with patch.object(analyzer, "_decode_image", return_value=None), patch.object(
        analyzer,
        "_mark_snapshot_error",
    ) as mock_mark:
        analyzer.process_pending_images()
        mock_mark.assert_called_once()
        args, _ = mock_mark.call_args
        assert args[0] == "snap-decode-fail"


def test_process_pending_images_with_face(analyzer):
    """Process snapshot when a face is detected."""
    snapshot = {
        "_id": "snap-face",
        "processed": False,
        "image_data": "data:image/png;base64,xxx",
    }
    cursor = FakeCursor([snapshot])
    analyzer.db.mood_snapshots.find.return_value = cursor

    fake_image = np.zeros((100, 100, 3), dtype=np.uint8)
    with patch.object(
        analyzer,
        "_decode_image",
        return_value=fake_image,
    ), patch.object(
        analyzer,
        "detect_faces",
        return_value=[(0, 0, 50, 50)],
    ), patch.object(
        analyzer,
        "predict_emotion",
        return_value={"happiness": 1.0},
    ) as mock_predict, patch.object(
        analyzer,
        "categorize_mood",
        return_value="happy",
    ) as mock_cat, patch.object(
        analyzer,
        "_update_snapshot_with_face",
    ) as mock_update:
        analyzer.process_pending_images()

        mock_predict.assert_called_once()
        mock_cat.assert_called_once_with({"happiness": 1.0})
        mock_update.assert_called_once()
        args, _ = mock_update.call_args
        assert args[0] == "snap-face"
        assert args[1] == {"happiness": 1.0}
        assert args[2] == "happy"


def test_process_pending_images_no_face(analyzer):
    """Update snapshot when no face is detected in the image."""
    snapshot = {
        "_id": "snap-no-face",
        "processed": False,
        "image_data": "data:image/png;base64,xxx",
    }
    cursor = FakeCursor([snapshot])
    analyzer.db.mood_snapshots.find.return_value = cursor

    fake_image = np.zeros((100, 100, 3), dtype=np.uint8)
    with patch.object(
        analyzer,
        "_decode_image",
        return_value=fake_image,
    ), patch.object(
        analyzer,
        "detect_faces",
        return_value=[],
    ), patch.object(
        analyzer,
        "_update_snapshot_no_face",
    ) as mock_no_face:
        analyzer.process_pending_images()
        mock_no_face.assert_called_once_with("snap-no-face")


def test_process_pending_images_exception(analyzer):
    """Mark snapshot error when processing raises an exception."""
    snapshot = {
        "_id": "snap-exception",
        "processed": False,
        "image_data": "data:image/png;base64,xxx",
    }
    cursor = FakeCursor([snapshot])
    analyzer.db.mood_snapshots.find.return_value = cursor

    with patch.object(
        analyzer,
        "_decode_image",
        side_effect=ValueError("bad"),
    ), patch.object(
        analyzer,
        "_mark_snapshot_error",
    ) as mock_mark:
        analyzer.process_pending_images()
        mock_mark.assert_called_once()
        args, _ = mock_mark.call_args
        assert args[0] == "snap-exception"
        assert "bad" in args[1]


def test_run_handles_keyboard_interrupt(analyzer):
    """Exit the main loop cleanly on KeyboardInterrupt."""
    with patch.object(
        analyzer,
        "process_pending_images",
        side_effect=KeyboardInterrupt,
    ), patch("mood_analyzer.time.sleep") as mock_sleep:
        analyzer.run()
        mock_sleep.assert_not_called()
