"""Mocks for external dependencies in tests."""
import os
import json
from unittest.mock import MagicMock

# Sample transcript JSON
MOCK_TRANSCRIPT_JSON = json.dumps([
    {"speaker": "Speaker 1", "timestamp": "00:05", "text": "Hello, how are you today?"},
    {"speaker": "Speaker 2", "timestamp": "00:12", "text": "I'm doing well, thank you for asking."},
    {"speaker": "Speaker 1", "timestamp": "00:18", "text": "That's great to hear. What are your plans?"},
    {"speaker": "Speaker 2", "timestamp": "00:25", "text": "I have a few meetings then I'll work on the project."}
])

# Formatted transcript
MOCK_TRANSCRIPT_TEXT = """[Speaker 1 00:05]: Hello, how are you today?
[Speaker 2 00:12]: I'm doing well, thank you for asking.
[Speaker 1 00:18]: That's great to hear. What are your plans?
[Speaker 2 00:25]: I have a few meetings then I'll work on the project."""

# Sample summary
MOCK_SUMMARY_TEXT = """# Meeting Overview
Brief discussion about well-being and project planning.

## Key Discussion Points
* Personal well-being
* Project planning and schedule
* Upcoming meetings

## Decisions Made
* Proceed with the project as planned

## Action Items
* Speaker 2 to work on the project after meetings

## Follow-up
* Review project progress in the next meeting
"""

class MockResponse:
    """Mock response for Gemini transcription."""
    def __init__(self, text=MOCK_TRANSCRIPT_JSON):
        self.text = text
    
    def __str__(self):
        return self.text

class MockStreamResponse:
    """Mock streaming response from Gemini API."""
    def __init__(self, text=MOCK_TRANSCRIPT_JSON):
        self.text = text
    
    def __iter__(self):
        """Make the object iterable to simulate streaming."""
        return iter([self])

def mock_transcription_service():
    """Create a mock TranscriptionService with controlled behavior."""
    mock_service = MagicMock()
    
    # Create output file
    output_file = os.path.join(os.path.dirname(__file__), "temp", "mock_transcript.txt")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(MOCK_TRANSCRIPT_TEXT)
    
    # Set return values
    summary_file = os.path.join(os.path.dirname(output_file), "mock_summary.txt")
    mock_service.run.return_value = (MOCK_TRANSCRIPT_TEXT, output_file, summary_file)
    
    return mock_service

def mock_summary_generator():
    """Create a mock SummaryGenerator with controlled behavior."""
    mock_generator = MagicMock()
    
    # Mock methods
    mock_generator.generate_summary.return_value = MOCK_SUMMARY_TEXT
    
    improved_summary = "# Improved " + MOCK_SUMMARY_TEXT
    mock_generator.regenerate_summary.return_value = improved_summary
    
    def mock_save_summary(summary, input_path=None, output_dir=None):
        if not summary:
            return None
            
        if input_path:
            name_base = os.path.basename(input_path).split('.')[0]
            output_name = f"{name_base}_summary.txt"
        else:
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            output_name = f"meeting_summary_{timestamp}.txt"
            
        # Set output path
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_name)
        else:
            temp_dir = os.path.join(os.path.dirname(__file__), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            output_path = os.path.join(temp_dir, output_name)
            
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary)
            
        return output_path
    
    mock_generator.save_summary_to_file.side_effect = mock_save_summary
    
    return mock_generator

def mock_upload_file(client, file_path, store_audio=False):
    """Mock the file upload function."""
    # Check file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"[MOCK] Uploading file: {file_path} (MOCK - NO ACTUAL UPLOAD)")
    
    # Create mock file
    mock_file = MagicMock()
    mock_file.name = os.path.basename(file_path)
    mock_file.uri = f"mock://files/{os.path.basename(file_path)}"
    mock_file.mime_type = "audio/wav"
    
    state = MagicMock()
    state.name = "ACTIVE"
    mock_file.state = state
    
    return mock_file

def mock_delete_uploaded_file(client, file):
    """Mock the file deletion function."""
    return True

def mock_stream_transcription(client, model, contents, config, file_path, model_name=None):
    """Mock the streaming transcription function with both parameter styles."""
    # Error scenario
    if getattr(mock_stream_transcription, "return_error", False):
        return ""
    
    # Check file exists
    if not os.path.exists(file_path) and not file_path.startswith('/nonexistent'):
        return ""
    
    return MOCK_TRANSCRIPT_JSON

# Error flag
mock_stream_transcription.return_error = False

def mock_summary_response():
    """Create a mock response for summary generation."""
    mock_response = MagicMock()
    mock_response.text = MOCK_SUMMARY_TEXT
    return mock_response

def mock_gemini_client():
    """Create a complete mock of the Gemini API client."""
    mock_client = MagicMock()
    
    # Mock models
    mock_models = MagicMock()
    mock_stream = MockStreamResponse()
    mock_models.generate_content_stream.return_value = mock_stream
    
    # Mock summary generation
    mock_response = mock_summary_response()
    mock_models.generate_content.return_value = mock_response
    
    mock_client.models = mock_models
    
    # Mock file operations
    mock_client.upload_file = MagicMock(side_effect=lambda path: mock_upload_file(mock_client, path))
    mock_client.delete_file = MagicMock(return_value=True)
    
    # Mock files property
    mock_files = MagicMock()
    mock_file = MagicMock()
    
    mock_state = MagicMock()
    mock_state.name = "ACTIVE"
    mock_file.state = mock_state
    
    mock_file.name = "mock_file.wav"
    mock_file.uri = "mock://file_uri"
    mock_file.mime_type = "audio/wav"
    
    mock_files.upload.return_value = mock_file
    mock_files.get.return_value = mock_file
    mock_files.delete.return_value = None
    
    mock_client.files = mock_files
    
    return mock_client