FROM python:3.10-slim

# Create app directory
WORKDIR /app

# Install system dependencies (if you need any, add them here)
# For now, keep it minimal.

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

EXPOSE 5000

# Default command
CMD ["flask", "run"]
