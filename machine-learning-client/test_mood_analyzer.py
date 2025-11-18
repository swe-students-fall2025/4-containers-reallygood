"""
Tests for MoodAnalyzer
"""

from unittest.mock import patch, MagicMock  # 标准库先导入

import numpy as np  # 第三方库
import pytest  # 第三方库

from mood_analyzer import MoodAnalyzer  # 本地模块放最后


@pytest.fixture(name="mock_mongodb")
def mock_mongodb_fixture():
    """Mock MongoDB connection."""
    with patch("mood_analyzer.MongoClient") as mock:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.study_mood_tracker = mock_db
        mock.return_value = mock_client
        yield mock_db


@pytest.fixture(name="mock_onnx_session")
def mock_onnx_session_fixture():
    """Mock ONNX runtime session."""
    with patch("mood_analyzer.ort.InferenceSession") as mock:
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_output = MagicMock()
        mock_output.name = "output"
        mock_session.get_inputs.return_value = [mock_input]
        mock_session.get_outputs.return_value = [mock_output]
        # Mock prediction output
        mock_session.run.return_value = [
            np.array([[0.1, 0.6, 0.05, 0.1, 0.05, 0.05, 0.05]])
        ]
        mock.return_value = mock_session
        yield mock_session


@pytest.fixture(name="analyzer")
def analyzer_fixture(mock_mongodb, mock_onnx_session):
    """Create MoodAnalyzer instance with mocked dependencies."""
    # mock_mongodb 和 mock_onnx_session fixture 会在这里被使用，
    # 避免 unused-argument 的 warning
    _ = mock_mongodb
    _ = mock_onnx_session
    with patch("os.path.exists", return_value=True):
        analyzer = MoodAnalyzer("mongodb://test:27017/test")
        return analyzer


def test_categorize_mood_happy(analyzer):
    """Test mood categorization for happy emotion."""
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
    """Test mood categorization for unhappy emotions."""
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
    """Test mood categorization for neutral emotion."""
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
    """Test mood categorization for focused/surprised emotion."""
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
    """Test mood categorization with empty emotion dict."""
    mood = analyzer.categorize_mood({})
    assert mood == "unknown"


def test_preprocess_face(analyzer):
    """Test face preprocessing."""
    # Create a dummy face image
    face_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    # Preprocess
    processed = analyzer.preprocess_face(face_img)

    # Check shape (1, 1, 64, 64)
    assert processed.shape == (1, 1, 64, 64)

    # Check data type
    assert processed.dtype == np.float32

    # Check normalization (values between 0 and 1)
    assert processed.min() >= 0.0
    assert processed.max() <= 1.0


def test_detect_faces(analyzer):
    """Test face detection."""
    # Create a dummy image
    image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Mock cascade classifier
    with patch.object(analyzer.face_cascade, "detectMultiScale") as mock_detect:
        mock_detect.return_value = np.array([[100, 100, 200, 200]])

        faces = analyzer.detect_faces(image)

        assert len(faces) > 0
        mock_detect.assert_called_once()


def test_predict_emotion(analyzer, mock_onnx_session):
    """Test emotion prediction."""
    # Create a dummy face image
    face_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    # Predict emotion
    emotions = analyzer.predict_emotion(face_img)

    # Check that we got emotion probabilities
    assert isinstance(emotions, dict)
    assert len(emotions) == 7  # 7 emotion categories
    assert "happiness" in emotions
    assert all(0 <= prob <= 1 for prob in emotions.values())

    # Verify ONNX session was called
    mock_onnx_session.run.assert_called_once()
