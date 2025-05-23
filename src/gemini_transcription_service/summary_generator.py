import os
import logging
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .config import SAFETY_SETTINGS
from .transcription_logic import configure_generation
from .storage_handler import SummaryStorageHandler

# Load environment variables from .env file
load_dotenv(override=True)
logger = logging.getLogger(__name__)

class SummaryGenerator:
    def __init__(self, client=None):
        # Reuse client or create new one
        if client:
            self.client = client
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            self.client = genai.Client(api_key=api_key)

        # Model params
        self.model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash-preview-04-17")
        self.temperature = float(os.getenv("TEMPERATURE", "1.0"))
        self.max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "32768"))

    def generate_summary(self, transcript, speaker_mapping=None):
        if not transcript or not transcript.strip():
            logger.warning("Cannot generate summary: Empty transcript provided")
            return ""

        try:
            # Replace speaker IDs with names if provided
            processed_transcript = transcript
            if speaker_mapping and isinstance(speaker_mapping, dict):
                for speaker_id, real_name in speaker_mapping.items():
                    if real_name and f"[{speaker_id}]" in processed_transcript:
                         processed_transcript = processed_transcript.replace(f"[{speaker_id}]", f"[{real_name}]")
                    elif real_name and speaker_id in processed_transcript:
                        processed_transcript = processed_transcript.replace(speaker_id, real_name)

            # Prompt for meeting summary
            prompt = f"""Create a comprehensive meeting summary based on the transcript below.

            Follow these guidelines:
            1. Identify the key discussion points, decisions made, and action items
            2. Maintain a professional, objective tone
            3. Structure the summary with clear headings for main topics
            4. Include who was responsible for each action item when mentioned
            5. Keep the summary complete but avoid including unnecessary details

            Transcript:
            {processed_transcript}

            Format the summary with these sections:
            - Meeting Overview: A brief 1-2 sentence overview
            - Key Discussion Points: Bulleted list of main topics discussed
            - Decisions Made: Bulleted list of decisions
            - Action Items: Bulleted list of tasks with assignees
            - Follow-up: Recommendations for next steps
            """

            # Config
            gen_config = configure_generation(
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            gen_config.response_schema = None
            gen_config.response_mime_type = "text/plain"

            # API call
            response = self.client.models.generate_content(
                model=f"models/{self.model_name}",
                contents=prompt,
                config=gen_config
            )

            return response.text.strip() if hasattr(response, 'text') else ""

        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            return ""

    def regenerate_summary(self, original_transcript, previous_summary, feedback):
        if not all([original_transcript, previous_summary, feedback]):
            logger.warning("Cannot regenerate summary: Missing required inputs")
            return ""

        try:
            # Prompt for improved summary
            prompt = f"""Improve the meeting summary based on the provided feedback.

            Original Meeting Transcript:
            {original_transcript}

            Previous Summary:
            {previous_summary}

            User Feedback:
            {feedback}

            Create an improved summary that addresses the feedback while maintaining the same structure.
            """

            gen_config = configure_generation(
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            gen_config.response_schema = None
            gen_config.response_mime_type = "text/plain"

            response = self.client.models.generate_content(
                model=f"models/{self.model_name}",
                contents=prompt,
                config=gen_config
            )

            return response.text.strip() if hasattr(response, 'text') else ""

        except Exception as e:
            logger.error(f"Error regenerating summary: {e}", exc_info=True)
            return ""

    def save_summary_to_file(self, summary, input_path=None, output_dir=None):
        if not summary:
            logger.warning("No summary content to save")
            return None

        try:
            output_extension = ".txt"
            if input_path:
                name_part = os.path.splitext(os.path.basename(input_path))[0]
                base_output_name = f"{name_part}_summary"
            else:
                current_timestamp = time.strftime("%Y%m%d_%H%M%S")
                base_output_name = f"meeting_summary_{current_timestamp}"

            effective_output_dir = output_dir if output_dir is not None else os.getenv("SUMMARY_PATH", os.getenv("OUTPUT_DIR", "./summaries"))

            if effective_output_dir and effective_output_dir != ".":
                os.makedirs(effective_output_dir, exist_ok=True)
            
            current_output_path = os.path.join(effective_output_dir, f"{base_output_name}{output_extension}")
            final_output_path = current_output_path

            if input_path and os.path.exists(final_output_path):
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                final_output_path = os.path.join(effective_output_dir, f"{base_output_name}_{timestamp}{output_extension}")
            
            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            logger.info(f"Summary saved to {final_output_path}")

            store_summary = os.getenv("SUMMARY_STORAGE_ENABLED", "false").lower() in ["true", "1", "yes"]

            if store_summary:
                try:
                    handler = SummaryStorageHandler()
                    if handler.initialize():
                        gcs_uri = handler.upload_file(final_output_path)
                        if gcs_uri:
                            logger.info(f"Summary uploaded to GCS: {gcs_uri}")
                except Exception as e:
                    logger.warning(f"Failed to upload summary to GCS: {e}")

            return final_output_path
        except IOError as e:
            path_for_logging = "<unknown path>"
            if 'final_output_path' in locals() and final_output_path:
                path_for_logging = final_output_path
            elif 'current_output_path' in locals() and current_output_path:
                path_for_logging = current_output_path
            elif 'effective_output_dir' in locals() and 'base_output_name' in locals() and 'output_extension' in locals():
                path_for_logging = os.path.join(effective_output_dir, f"{base_output_name}{output_extension}")
            
            logger.error(f"Error saving summary to {path_for_logging}: {e}")
            return None
        except Exception as e:
             logger.error(f"Unexpected error saving summary: {e}", exc_info=True)
             return None