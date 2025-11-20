# Study Mood Tracker

[![Web App CI](https://github.com/swe-students-fall2025/4-containers-reallygood/actions/workflows/web-app-ci.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/4-containers-reallygood/actions/workflows/web-app-ci.yml)
[![ML Client CI](https://github.com/swe-students-fall2025/4-containers-reallygood/actions/workflows/ml-client-ci.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/4-containers-reallygood/actions/workflows/ml-client-ci.yml)
[![Lint Workflow](https://github.com/swe-students-fall2025/4-containers-reallygood/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/4-containers-reallygood/actions/workflows/lint.yml)

An AI-powered containerized application that tracks and analyzes students' emotions and focus levels during study sessions using webcam-based facial expression recognition.

## Team Members

- **Leo Qian** - [Leo Qian](https://github.com/Leo-codingMaster)
- **Gavin Guo** - [Gavin Guo](https://github.com/GavinGuoSZ)
- **Leo Li** - [Leo Li](https://github.com/LiShangcheng)

## Project Overview

This application uses machine learning to detect and analyze facial expressions in real-time, helping students understand their emotional states during study sessions. The system consists of three main components:

1. **Machine Learning Client**: Processes images using a pre-trained emotion recognition model (FER+)
2. **Web Application**: Provides an interactive dashboard for capturing images and viewing analysis results
3. **MongoDB Database**: Stores snapshots and analysis results

## Features

- **Image Upload**: Upload photos for emotion analysis
- **Live Webcam Capture**: Real-time emotion detection using your webcam
- **AI-Powered Analysis**: Detects 7 emotions (neutral, happiness, surprise, sadness, anger, disgust, fear)
- **Dashboard**: View current and historical mood analysis
- **Fully Containerized**: Easy deployment with Docker Compose

## Technology Stack

- **Backend**: Python 3.10, Flask
- **Machine Learning**: ONNX Runtime, OpenCV, FER+ emotion recognition model
- **Database**: MongoDB 7.0
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Containerization**: Docker, Docker Compose
- **Testing**: pytest, pytest-flask, pytest-cov
- **Code Quality**: pylint, black

## Prerequisites

- Docker Desktop (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- Git

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd containerized-app-exercise
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

The `.env` file should contain:

```env
# MongoDB Atlas connection string (or use local MongoDB)
MONGO_URI=mongodb://mongodb:27017/study_mood_tracker

# Database name
MONGO_DB_NAME=study_mood_tracker

# For Docker Compose compatibility
MONGODB_URI=${MONGO_URI}
```

**Note**: The default configuration uses the containerized MongoDB. If you want to use MongoDB Atlas, replace the `MONGO_URI` with your Atlas connection string.

### 3. Start the Application

```bash
docker-compose up --build
```

This command will:
- Build Docker images for the web app and ML client
- Start MongoDB container
- Start the machine learning client (background processing)
- Start the web application (accessible at http://localhost:5000)

### 4. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:5000/dashboard
```

## Usage Guide

### Analyzing Emotions

1. **Upload an Image**:
   - Click "Choose File" and select an image with a face
   - Click "Analyze" to upload
   - Wait a few seconds for the ML client to process
   - View results in the "Analysis Result" section

2. **Use Webcam**:
   - Click "Enable Camera" (allow browser access)
   - Click "Capture & Analyze"
   - Results appear automatically after processing

### Understanding Results

The system detects and reports:
- **Mood Category**: happy, neutral, unhappy, focused, or unknown
- **Emotion Probabilities**: Breakdown of all 7 emotions
- **Face Detection**: Whether a face was found in the image
- **Processing Status**: pending, done, or error

## Development

### Project Structure

```
.
├── docker-compose.yml           # Container orchestration
├── .env.example                 # Environment variables template
├── machine-learning-client/     # ML processing service
│   ├── Dockerfile
│   ├── Pipfile & Pipfile.lock
│   ├── mood_analyzer.py         # Main ML processing logic
│   ├── db.py                    # Database connection
│   └── test_mood_analyzer.py    # Unit tests
├── web-app/                     # Flask web application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                   # Flask routes
│   ├── db.py                    # Database connection
│   ├── db_service.py            # Database operations
│   ├── templates/               # HTML templates
│   ├── static/                  # CSS & JavaScript
│   └── tests/                   # Unit tests
└── .github/workflows/           # CI/CD workflows
    ├── lint.yml                 # Code quality checks
    └── ml-client-ci.yml         # ML client tests
```

### Running Tests

**Machine Learning Client:**
```bash
cd machine-learning-client
pipenv install --dev
pipenv run pytest --cov=. --cov-report=term-missing
```

**Web Application:**
```bash
cd web-app
pip install -r requirements.txt
pytest tests/
```

### Code Quality

The project uses `pylint` and `black` for code quality:

```bash
# Format code
cd machine-learning-client
pipenv run black .

# Lint code
pipenv run pylint **/*.py
```

### Running Individual Containers

**MongoDB only:**
```bash
docker-compose up mongodb
```

**Web app only (requires MongoDB):**
```bash
docker-compose up web-app
```

**ML client only (requires MongoDB):**
```bash
docker-compose up machine-learning-client
```

## API Documentation

### POST /api/snapshots
Create a new mood snapshot for analysis.

**Request Body:**
```json
{
  "image_data": "base64_encoded_image_string"
}
```

**Response:**
```json
{
  "id": "snapshot_id"
}
```

### GET /api/snapshots/:id
Retrieve a specific snapshot by ID.

**Response:**
```json
{
  "id": "snapshot_id",
  "status": "done",
  "processed": true,
  "mood": "happy",
  "face_detected": true,
  "emotions": {
    "neutral": 0.1,
    "happiness": 0.7,
    "surprise": 0.05,
    "sadness": 0.05,
    "anger": 0.05,
    "disgust": 0.025,
    "fear": 0.025
  },
  "created_at": "2024-01-01T12:00:00",
  "processed_at": "2024-01-01T12:00:02"
}
```

### GET /api/snapshots
List recent snapshots (last 20).

**Response:**
```json
{
  "count": 2,
  "items": [
    {
      "id": "snapshot_id",
      "status": "done",
      "mood": "happy",
      "face_detected": true,
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

## Troubleshooting

### MongoDB Connection Issues

If you see connection errors:
1. Ensure MongoDB container is running: `docker-compose ps`
2. Check MongoDB logs: `docker-compose logs mongodb`
3. Verify `.env` file configuration

### ML Client Not Processing

If images remain in "pending" status:
1. Check ML client logs: `docker-compose logs machine-learning-client`
2. Verify the client container is running: `docker-compose ps`
3. Ensure the emotion model downloaded successfully

### Port Already in Use

If port 5000 is already in use:
```bash
# Find and stop the process using port 5000
lsof -ti:5000 | xargs kill -9

# Or change the port in docker-compose.yml
```

### Camera Access Denied

The browser requires HTTPS for webcam access (except on localhost). If testing remotely:
1. Use `localhost` or `127.0.0.1`
2. Or set up HTTPS with a reverse proxy

## CI/CD

The project includes GitHub Actions workflows:

- **Lint Workflow** (`.github/workflows/lint.yml`): Runs `pylint` and `black` on every push/PR
- **ML Client CI** (`.github/workflows/ml-client-ci.yml`): Runs tests with 80%+ coverage requirement
