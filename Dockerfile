FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY pyproject.toml .
COPY main.py .
COPY run.py .
COPY gunicorn_config.py .
COPY src/ src/

# Create directories
RUN mkdir -p uploads transcripts summaries static

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir gunicorn

EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn_config.py", "run:app"]