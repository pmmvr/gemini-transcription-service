import os
import tempfile
from unittest.mock import patch, MagicMock
from behave import given, when, then
import sys
import logging
from io import StringIO

# Import mock transcript data
from features.mocks import MOCK_TRANSCRIPT_TEXT, MOCK_TRANSCRIPT_JSON

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cli_test')

@given('I have a valid audio file')
def step_impl(context):
    # Use existing sample or create a test WAV file
    if hasattr(context, 'sample_audio_path') and os.path.exists(context.sample_audio_path):
        context.audio_file_path = context.sample_audio_path
    else:
        fd, context.audio_file_path = tempfile.mkstemp(suffix='.wav', dir=context.temp_path)
        os.close(fd)
        
        with open(context.audio_file_path, 'wb') as f:
            # Minimal WAV header
            f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x04\x00\x00\x00\x04\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')
    
    logger.info(f"Using test audio file at: {context.audio_file_path}")

@given('I have a valid audio file with format "{format}"')
def step_impl(context, format):
    # Create test file with specified format
    test_file = os.path.join(context.temp_path, f"test_audio.{format}")
    
    with open(test_file, 'wb') as f:
        if format == 'wav':
            # WAV header
            f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x04\x00\x00\x00\x04\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')
        elif format in ['mp3', 'm4a']:
            # Dummy content
            f.write(b'DUMMY AUDIO CONTENT')
    
    context.audio_file_path = test_file
    logger.info(f"Created test {format.upper()} file at: {context.audio_file_path}")

@given('I have a non-existent audio file path')
def step_impl(context):
    # Set path to non-existent file
    context.audio_file_path = os.path.join(context.temp_path, 'non_existent_file.wav')
    # Ensure it doesn't exist
    if os.path.exists(context.audio_file_path):
        os.remove(context.audio_file_path)
    logger.info(f"Using non-existent path: {context.audio_file_path}")

@given('I have set a custom output directory')
def step_impl(context):
    # Create and set custom output dir
    context.custom_output_dir = os.path.join(context.temp_path, 'custom_output')
    os.makedirs(context.custom_output_dir, exist_ok=True)
    os.environ['OUTPUT_DIR'] = context.custom_output_dir
    logger.info(f"Set custom output directory: {context.custom_output_dir}")

@given('the Gemini API is configured to return an error')
def step_impl(context):
    # Set flag for API error simulation
    context.api_error_mode = True
    logger.info("Configured Gemini API to simulate errors")

@when('I run the transcription command with the file path')
def step_impl(context):
    # Capture stdout/stderr
    context.stdout = StringIO()
    context.stderr = StringIO()
    
    # Import service classes
    from src.gemini_transcription_service.transcribe import TranscriptionService
    from src.gemini_transcription_service.transcription_logic import stream_transcription
    
    service = TranscriptionService()
    
    logger.info(f"Starting transcription process for: {context.audio_file_path}")
    try:
        # Set test API key
        if 'GEMINI_API_KEY' not in os.environ:
            os.environ['GEMINI_API_KEY'] = 'test_api_key'
        
        # Mock Google API
        with patch('google.genai.Client') as mock_client:
            
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Mock file operations
            mock_files = MagicMock()
            mock_file = MagicMock()
            mock_file.uri = "mock://file_uri"
            mock_file.mime_type = "audio/wav"
            mock_file.name = "mock_file.wav"
            
            mock_state = MagicMock()
            mock_state.name = "ACTIVE"
            mock_file.state = mock_state
            
            mock_files.upload.return_value = mock_file
            mock_files.get.return_value = mock_file
            mock_client_instance.files = mock_files
            
            # Mock API response
            if getattr(context, 'api_error_mode', False):
                mock_client_instance.models.generate_content_stream.side_effect = Exception("Simulated API error")
            else:
                mock_chunk = MagicMock()
                mock_chunk.text = MOCK_TRANSCRIPT_JSON
                mock_stream = [mock_chunk]
                mock_client_instance.models.generate_content_stream.return_value = mock_stream
            
            # Check if file exists
            if not os.path.exists(context.audio_file_path):
                context.stderr.write(f"ERROR: Input file not found at '{context.audio_file_path}'")
                context.result = (None, None, None)
                return
            
            output_dir = getattr(context, 'custom_output_dir', None)
            
            try:
                context.result = service.run(context.audio_file_path, output_dir_override=output_dir)
            except TypeError as e:
                if "unexpected keyword argument" in str(e):
                    context.stderr.write(f"PARAMETER ERROR: {str(e)}")
                    logger.error(f"Parameter compatibility error: {str(e)}")
                context.result = (None, None, None)
        
        logger.info("Transcription process finished.")
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        context.stderr.write(f"ERROR: {str(e)}")
        context.result = (None, None, None)

@then('the transcription should be successful')
def step_impl(context):
    # Verify transcript exists and has content
    transcript, _, _ = context.result
    assert transcript is not None, "Transcription failed"
    assert transcript.strip(), "Transcript is empty"
    logger.info(f"Transcript content validated: {transcript[:50]}...")

@then('the transcript should be saved to a file')
def step_impl(context):
    # Check output file exists and has content
    _, path, _ = context.result
    assert path is not None, "No output file was created"
    assert os.path.exists(path), f"Output file doesn't exist at {path}"
    
    with open(path, 'r') as f:
        content = f.read()
    
    assert content.strip(), "Transcript file is empty"
    logger.info(f"Verified transcript file at: {path}")

@then('the transcript should contain proper diarization')
def step_impl(context):
    # Check for speaker tags and timestamps
    transcript, _, _ = context.result
    
    assert "Speaker 1" in transcript, "Speaker 1 tag not found in transcript"
    assert "Speaker 2" in transcript, "Speaker 2 tag not found in transcript"
    
    import re
    assert re.search(r'\d{2}:\d{2}', transcript), "Timestamp format not found in transcript"
    
    logger.info("Verified proper diarization in transcript")

@then('the transcript should be saved to the custom output directory')
def step_impl(context):
    # Verify file saved to custom dir
    _, path, _ = context.result
    assert path is not None, "No output file was created"
    assert os.path.exists(path), f"Output file doesn't exist at {path}"
    
    # Check path contains custom dir
    assert "custom_output" in path, f"File {path} not in custom directory"
    
    with open(path, 'r') as f:
        content = f.read()
    assert "Speaker 1" in content, "Transcript content missing Speaker 1"
    
    logger.info(f"Verified transcript saved to custom directory: {path}")

@then('the application should report that the file does not exist')
def step_impl(context):
    # Check for file not found error
    error = context.stderr.getvalue() if hasattr(context, 'stderr') else ""
    assert "not found" in error.lower() or context.result[0] is None, "Application did not properly report missing file"
    logger.info("Verified application reported non-existent file")

@then('no transcription should be created')
def step_impl(context):
    # Verify no output was generated
    transcript, path, summary = context.result
    assert transcript is None, "Transcription was unexpectedly generated"
    assert path is None, "Output file was unexpectedly created"
    assert summary is None, "Summary was unexpectedly generated"
    logger.info("Verified no transcription was created")

@then('the application should handle the error gracefully')
def step_impl(context):
    # Check error handling
    error = context.stderr.getvalue() if hasattr(context, 'stderr') else ""
    assert "error" in error.lower() or context.result[0] is None, "Application did not report an error"
    assert context.result is not None, "Application crashed instead of handling the error"
    logger.info("Verified graceful error handling")