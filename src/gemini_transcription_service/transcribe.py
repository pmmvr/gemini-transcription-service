import argparse
import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
import httpx
from gemini_transcription_service.storage_handler import upload_file, delete_uploaded_file
from gemini_transcription_service.transcription_logic import prepare_content, configure_generation, stream_transcription
from gemini_transcription_service.transcript_processor import TranscriptProcessor
from gemini_transcription_service.summary_generator import SummaryGenerator
from .exceptions import TranscriptionTimeoutError

# Ensure environment variables are loaded
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self):
        self.client = None
        self.uploaded_file = None

    def _initialize(self):
        # Init client
        logger.info("Loading application configuration...")
        logger.info("Initializing Gemini client...")
        http_options = types.HttpOptions(timeout=900000) # 15 minutes
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options=http_options
        )

    def _cleanup(self):
        try:
            # Clean temp resources
            if self.client and self.uploaded_file:
                logger.info(f"Cleaning up uploaded file: {self.uploaded_file.name}")
                delete_uploaded_file(self.client, self.uploaded_file)
            elif not self.client:
                logger.warning("Cleanup skipped: Client not initialized.")
            elif not self.uploaded_file:
                logger.info("Cleanup: No file needed deleting.")

            # Reset state
            self.uploaded_file = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Continue with cleanup even if there's an error


    def run(self, file_path: str, output_dir_override: str | None = None, store_audio: bool = None, generate_summary: bool = False, summary_path: str = None):
        formatted_transcript = None
        output_file_path = None
        summary_file_path = None

        if summary_path is None:
            summary_path = os.getenv("SUMMARY_PATH", "./summaries")

        api_error = False
        try:
            self._initialize()

            # Upload file
            self.uploaded_file = upload_file(self.client, file_path, store_audio)
            if not self.uploaded_file:
                logger.error(f"File upload failed for {file_path}. Aborting.")
                return None, None, None

            # Prep API request
            contents = prepare_content(self.uploaded_file)

            # Set params
            gen_config = configure_generation(
                temperature= float(os.getenv("TEMPERATURE", "1.0")),
                max_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "32768"))
            )

            logger.info(f"Starting transcription stream for: {file_path}")

            try:
                # Call API
                raw_response = stream_transcription(
                    client=self.client,
                    model= os.getenv("MODEL_NAME", "gemini-2.5-flash-preview-04-17"),
                    contents=contents,
                    config=gen_config,
                    file_path=file_path,
                )
            except (httpx.RemoteProtocolError, httpx.ReadTimeout) as http_timeout_err:
                logger.error(f"HTTP timeout/disconnect during transcription stream: {http_timeout_err}")
                api_error = True
                raise TranscriptionTimeoutError(
                    "Transcription timed out, recording might be too long and consider splitting it into smaller segments."
                ) from http_timeout_err
            except Exception as api_e:
                logger.error(f"API error during transcription: {api_e}")
                api_error = True
                raw_response = None

            # Process valid responses
            if raw_response and not api_error:
                logger.debug(f"Raw response content: {raw_response}")
                logger.info("Processing and saving transcript...")
                processor = TranscriptProcessor()
                formatted_transcript = processor.process_response(raw_response)

                # Get output location
                effective_output_dir = output_dir_override if output_dir_override is not None else os.getenv("OUTPUT_DIR", None)

                # Save transcript
                output_file_path = processor.save_transcript_to_file(
                    transcript=formatted_transcript,
                    input_path=file_path,
                    output_dir=effective_output_dir
                )

                # Generate summary if needed
                if generate_summary and formatted_transcript:
                    logger.info("Generating meeting summary...")
                    summary_generator = SummaryGenerator(client=self.client)
                    summary = summary_generator.generate_summary(formatted_transcript)

                    if summary:
                        # Save summary
                        effective_summary_dir = summary_path if summary_path else effective_output_dir
                        summary_file_path = summary_generator.save_summary_to_file(
                            summary=summary,
                            input_path=file_path,
                            output_dir=effective_summary_dir
                        )

                        if summary_file_path:
                            logger.info(f"Meeting summary saved to: {summary_file_path}")
                        else:
                            logger.error("Failed to save meeting summary")
                    else:
                        logger.error("Failed to generate meeting summary")
            else:
                error_reason = "API error occurred" if api_error else "empty response"
                logger.warning(f"Skipping processing and saving due to {error_reason}.")

        except TranscriptionTimeoutError:
            raise
        except Exception as e:
            logger.error(f"An error occurred during transcription for {file_path}: {e}", exc_info=True)
        finally:
            self._cleanup()

        # Return None on API errors
        if api_error:
            return None, None, None

        return formatted_transcript, output_file_path, summary_file_path
