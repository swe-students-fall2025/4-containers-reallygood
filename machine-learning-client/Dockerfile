FROM python:3.10-slim

WORKDIR /app


#Install system dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*


#Copy dependency files
COPY Pipfile Pipfile.lock ./


#Install Python dependencies
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --deploy


#Copy application code
COPY . .


#Run the application
CMD ["python", "mood_analyzer.py"]