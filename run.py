import os
import logging
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import application
try:
    from gemini_transcription_service.webapp.app import app
except ImportError:
    logger.error("Failed to import app module. Check PYTHONPATH.")
    sys.exit(1)

if __name__ == "__main__":
    # Ensure uploads directory exists
    os.makedirs('uploads', exist_ok=True)

    # Get configuration from environment variables
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')

    # Log startup information
    logger.info(f"Starting web application on {host}:{port} (debug={debug})")

    # Run the application
    app.run(host=host, port=port, debug=debug)