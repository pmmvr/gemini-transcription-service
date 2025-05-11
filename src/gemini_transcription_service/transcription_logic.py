from google import genai
from google.genai import types
import os
import json
import logging

from .config import SAFETY_SETTINGS

logger = logging.getLogger(__name__)

def prepare_content(file: types.File) -> list[types.Content]:
    # Prepare audio file and prompt for transcription
    audio = types.Part.from_uri(
        file_uri=file.uri,
        mime_type=file.mime_type,
    )
    prompt = """Generate a detailed diarized transcript for this audio file. Identify each speaker (e.g., Speaker 1, Speaker 2). Group consecutive speech from the same speaker together."""
    text = types.Part.from_text(text=prompt)
    return [
        types.Content(
            role="user",
            parts=[audio, text]
        ),
    ]

def configure_generation(temperature: float, max_tokens: int) -> types.GenerateContentConfig:
    # JSON schema for structured response
    schema = {
        "type": "ARRAY",
        "description": "A diarized transcript containing speech segments with speaker identification and transcribed text.",
        "items": {
            "type": "OBJECT",
            "properties": {
                "timestamp": {"type": "STRING", "description": "Start time (mm:ss format)"},
                "speaker": {"type": "STRING", "description": "Speaker identifier"},
                "text": {"type": "STRING", "description": "Transcribed text"}
            },
            "required": ["speaker", "text"]
        }
    }

    # Config params
    return types.GenerateContentConfig(
        temperature=temperature,
        top_p=0.95,
        seed=0,
        max_output_tokens=max_tokens,
        response_modalities=["TEXT"],
        safety_settings=SAFETY_SETTINGS,
        response_mime_type="application/json",
        response_schema=schema,
    )

def stream_transcription(client, model, contents, config, file_path):
    # Handle streaming response
    output = ""

    # Test error path if env var set
    if os.getenv('FORCE_API_ERROR', 'false').lower() in ['true', '1', 'yes']:
        logger.error("Forced API error for testing")
        raise Exception("Forced API error for testing")

    try:
        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )
        for chunk in stream:
                output += chunk.text
        return output
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        # Propagate error to caller
        raise