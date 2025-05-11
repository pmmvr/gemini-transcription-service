import os
import multiprocessing
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bind address
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"

# Worker processes - for CPU-intensive tasks like transcription,
# using too many workers can cause memory issues and contention
workers = int(os.getenv('GUNICORN_WORKERS', 2))
worker_class = 'sync'  # 'gevent' or 'eventlet' for async workers

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = 'info'

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 50  # Prevent all workers from restarting simultaneously

# Timeout settings
timeout = 120  # For long transcriptions
keepalive = 5

# Server settings
daemon = False  # Set to True to run in background