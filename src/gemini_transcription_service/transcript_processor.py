import os
import json
import logging
from gemini_transcription_service.storage_handler import GCSHandler

logger = logging.getLogger(__name__)

class TranscriptProcessor:
    def __init__(self):
        # Init GCS handler
        self.gcs_handler = GCSHandler()
        self.TRANSCRIPT_STORAGE_ENABLED = self.gcs_handler.initialize()

    def format_transcript(self, data):
        # Format JSON to text
        lines = []
        for entry in data:
            speaker = entry.get("speaker", "Unknown Speaker")
            timestamp = entry.get("timestamp", "00:00")
            text = entry.get("text", "").strip()
            if text:
                lines.append(f"[{speaker} {timestamp}]: {text}")
        return "\n".join(lines)

    def save_transcript_to_file(self, transcript, input_path, output_dir):
        # Save locally and to GCS
        if not transcript:
            logger.warning("No content to save")
            return None

        try:
            name, _ = os.path.splitext(os.path.basename(input_path))
            output_name = f"{name}_transcript.txt"

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_name)
            else:
                output_path = output_name

            # Local save
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            logger.info(f"Saved to {output_path}")
            
            # GCS upload
            if self.TRANSCRIPT_STORAGE_ENABLED:
                try:
                    gcs_uri = self.gcs_handler.upload_file(output_path)
                    if gcs_uri:
                        logger.info(f"Uploaded to GCS: {gcs_uri}")
                except Exception as e:
                    logger.error(f"GCS upload failed: {e}")
            
            return output_path

        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            return None

    def process_response(self, response):
        # Parse API response
        if not response or not response.strip():
            return ""
        

        try:
            preview = response[:100].replace("\n", " ")
            if len(response) > 100:
                preview += "..."
                
            if response.strip().startswith(("[", "{")):
                data = json.loads(response)
                if isinstance(data, list):
                    result = self.format_transcript(data)
                    logger.info("Transcript processed successfully")
                    return result
                else:
                    logger.error(f"Not a list type: {type(data).__name__}")
            else:
                logger.error(f"Not valid JSON: {preview}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON error: {e}")
        except Exception as e:
            logger.error(f"Process error: {e}")
            
        return ""