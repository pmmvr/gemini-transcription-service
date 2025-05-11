import argparse
import os
import logging
from dotenv import load_dotenv
from src.gemini_transcription_service.transcribe import TranscriptionService

# Load environment variables from .env file
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transcribe an audio file using Gemini.')
    parser.add_argument('file_path', type=str, help='Path to the local audio file to transcribe.')
    parser.add_argument('--summary', action='store_true', help='Generate a summary of the transcription.')
    parser.add_argument('--summary-path', type=str, help='Custom path to save the summary file.')
    args = parser.parse_args()

    service = None
    try:
        logger.info(f"Starting transcription process for: {args.file_path}")

        if not os.path.exists(args.file_path):
            logger.error(f"Input file not found at '{args.file_path}'")
        else:
            service = TranscriptionService()

            # Use environment default unless --summary is specified
            generate_summary = args.summary or os.getenv("GENERATE_SUMMARY", "false").lower() in ['true', '1', 'yes']

            service.run(
                file_path=args.file_path,
                generate_summary=generate_summary,
                summary_path=args.summary_path
            )

        logger.info("Transcription process finished.")
    except KeyboardInterrupt:
        logger.info("\nTranscription process interrupted by user. Cleaning up...")
        # If service was initialized, make sure cleanup happens
        if service and hasattr(service, '_cleanup'):
            service._cleanup()
        logger.info("Gracefully shut down.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        # If service was initialized, make sure cleanup happens
        if service and hasattr(service, '_cleanup'):
            service._cleanup()
        logger.info("Cleaned up after error.") 