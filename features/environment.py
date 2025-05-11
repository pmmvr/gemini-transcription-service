"""Environment setup for Behave tests with dependency mocking."""
import os
import sys
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import mocks
from features.mocks import (
    mock_upload_file,
    mock_delete_uploaded_file,
    mock_stream_transcription,
    mock_gemini_client,
    mock_summary_generator,
    MOCK_TRANSCRIPT_TEXT,
    MOCK_TRANSCRIPT_JSON,
    MOCK_SUMMARY_TEXT
)

def before_all(context):
    """Set up the environment before any tests run."""
    # Temp dir for test files
    context.temp_dir = tempfile.TemporaryDirectory()
    context.temp_path = context.temp_dir.name
    
    # Fixtures dir for samples
    context.fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(context.fixtures_path, exist_ok=True)
    
    # Create sample audio
    context.sample_audio_path = os.path.join(context.fixtures_path, "sample.wav")
    with open(context.sample_audio_path, 'wb') as f:
        # Minimal WAV header
        f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x04\x00\x00\x00\x04\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')

def after_all(context):
    """Clean up after all tests have run."""
    # Cleanup temp dir
    context.temp_dir.cleanup()
    
    # Cleanup fixtures
    if hasattr(context, 'fixtures_path') and os.path.exists(context.fixtures_path):
        shutil.rmtree(context.fixtures_path)

def before_feature(context, feature):
    """Set up the environment for a specific feature."""
    # Store patchers
    context.patches = []
    
    # Mock Gemini API
    genai_patcher = patch('google.genai.Client')
    mock_genai = genai_patcher.start()
    context.patches.append(genai_patcher)
    
    # Configure mock client
    client = mock_gemini_client()
    mock_genai.return_value = client
    context.mock_genai_client = client
    
    # Block HTTP requests
    httpx_patcher = patch('httpx.Client.request')
    mock_httpx = httpx_patcher.start()
    mock_httpx.side_effect = Exception("HTTP requests are disabled in tests")
    context.patches.append(httpx_patcher)
    
    # Mock GCS
    storage_init_patcher = patch('src.gemini_transcription_service.storage_handler.StorageHandler.initialize')
    mock_storage_init = storage_init_patcher.start()
    mock_storage_init.return_value = False  # Disable storage
    context.patches.append(storage_init_patcher)
    
    # Mock GCS client
    gcs_client_patcher = patch('google.cloud.storage.Client')
    gcs_client_patcher.start()
    context.patches.append(gcs_client_patcher)
    
    # Mock storage functions
    upload_patcher = patch('src.gemini_transcription_service.storage_handler.upload_file', 
                        side_effect=mock_upload_file)
    delete_patcher = patch('src.gemini_transcription_service.storage_handler.delete_uploaded_file', 
                        side_effect=mock_delete_uploaded_file)
    
    # Mock upload method
    handler_upload_patcher = patch('src.gemini_transcription_service.storage_handler.StorageHandler.upload_file')
    mock_handler_upload = handler_upload_patcher.start()
    mock_handler_upload.return_value = "mock://storage/file.txt"
    
    context.patches.extend([upload_patcher, delete_patcher, handler_upload_patcher])
    upload_patcher.start()
    delete_patcher.start()
    
    # Mock transcription
    stream_patcher = patch('src.gemini_transcription_service.transcription_logic.stream_transcription', 
                         side_effect=mock_stream_transcription)
    context.patches.append(stream_patcher)
    stream_patcher.start()
    
    # Set env vars
    os.environ['GEMINI_API_KEY'] = 'test_api_key'
    os.environ['MODEL_NAME'] = 'gemini-2.5-flash-preview-04-17'
    
    # Feature-specific setup
    if 'cli' in feature.tags:
        setup_cli_mocks(context)
    elif 'web' in feature.tags:
        setup_web_mocks(context)
    elif 'processing' in feature.tags:
        # No extra mocks needed
        pass
    elif 'summary' in feature.tags:
        setup_summary_mocks(context)

def after_feature(context, feature):
    """Clean up after a feature has run."""
    # Stop patches
    if hasattr(context, 'patches') and context.patches:
        for patcher in context.patches:
            try:
                patcher.stop()
            except RuntimeError:
                # Skip already stopped
                pass
        context.patches = []

def setup_cli_mocks(context):
    """Set up CLI-specific mocks."""
    # Set output dir
    os.environ['OUTPUT_DIR'] = context.temp_path

def setup_web_mocks(context):
    """Set up web-specific mocks for true blackbox E2E testing."""
    try:
        # Add root to path
        root_dir = os.path.join(os.path.dirname(__file__), "..")
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        
        # Setup Flask app
        from src.gemini_transcription_service.webapp.app import app
        
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = context.temp_path
        app.config['SECRET_KEY'] = 'test_secret_key'
        
        # Test client
        context.client = app.test_client()
        
        # Only mock external deps for E2E
        
    except ImportError as e:
        print(f"Error importing Flask app: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Failed to initialize Flask app: {e}")

def setup_summary_mocks(context):
    """Set up summary-specific mocks."""
    # Set env vars
    os.environ['OUTPUT_DIR'] = context.temp_path
    os.environ['SUMMARY_MODEL_NAME'] = 'gemini-2.5-flash-preview-04-17'
    os.environ['SUMMARY_TEMPERATURE'] = '0.4'
    os.environ['SUMMARY_MAX_TOKENS'] = '4096'
    
    # Create test transcript
    transcript_path = os.path.join(context.temp_path, "test_transcript.txt")
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(MOCK_TRANSCRIPT_TEXT)
    context.transcript_path = transcript_path
    
    # Mock summary generator
    summary_generator_patcher = patch('src.gemini_transcription_service.summary_generator.SummaryGenerator')
    mock_summary_gen = summary_generator_patcher.start()
    mock_summary_gen.return_value = mock_summary_generator()
    context.patches.append(summary_generator_patcher)
    
    # Web UI setup
    try:
        from src.gemini_transcription_service.webapp.app import app
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = context.temp_path
        app.config['GENERATE_SUMMARY'] = True
        context.client = app.test_client()
    except ImportError:
        pass  # Skip if not testing web UI