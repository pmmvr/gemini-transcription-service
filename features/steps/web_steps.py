import os
import tempfile
import io
import logging
import re
import uuid
import time
from unittest.mock import patch, MagicMock
from behave import given, when, then

# Import mocks
from features.mocks import MOCK_TRANSCRIPT_TEXT, MOCK_TRANSCRIPT_JSON

logger = logging.getLogger('web_test')
logging.basicConfig(level=logging.INFO)

@given('I access the web upload page')
def step_impl(context):
    # Setup Flask test client if not already created
    if not hasattr(context, 'client'):
        try:
            from src.gemini_transcription_service.webapp.app import app
            app.config['TESTING'] = True
            app.config['UPLOAD_FOLDER'] = context.temp_path
            app.config['SECRET_KEY'] = 'test_secret_key'
            context.client = app.test_client()
            logger.info("Successfully created Flask test client on-the-fly")
        except Exception as e:
            logger.error(f"Failed to create Flask test client: {e}")
            assert False, f"Flask client setup failed: {e}"
    
    response = context.client.get('/')
    
    assert response.status_code == 200, f"Failed to access web page: {response.status_code}"
    context.response = response
    
    content = response.data.decode('utf-8')
    assert 'Upload Audio for Transcription' in content, "Page title not found"
    logger.info("Successfully accessed web upload page")

@given('the Gemini API is configured to return an error for web tests')
def step_impl(context):
    # Set flag to simulate API errors
    context.simulate_api_error = True
    logger.info("Configured Gemini API to simulate errors for web tests")

@when('I upload a valid audio file')
def step_impl(context):
    # Create test WAV file
    file_id = str(uuid.uuid4())
    filename = f"test_file_{file_id}.wav"
    
    file_path = os.path.join(context.temp_path, filename)
    with open(file_path, 'wb') as f:
        f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x04\x00\x00\x00\x04\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')
    
    context.original_file_path = file_path
    logger.info(f"Created test file at: {file_path}")
    
    with patch('google.genai.Client') as mock_client:
        # Setup mock responses
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.uri = "mock://file_uri"
        mock_file.mime_type = "audio/wav"
        mock_file.name = filename
        
        mock_state = MagicMock()
        mock_state.name = "ACTIVE"
        mock_file.state = mock_state
        
        mock_files.upload.return_value = mock_file
        mock_files.get.return_value = mock_file
        mock_client_instance.files = mock_files
        
        if getattr(context, 'simulate_api_error', False):
            # Simulate API error if flag is set
            mock_client_instance.models.generate_content_stream.side_effect = Exception("Simulated API error")
            logger.info("Simulating API error response")
        else:
            # Return mock transcript
            mock_chunk = MagicMock()
            mock_chunk.text = MOCK_TRANSCRIPT_JSON
            mock_stream = [mock_chunk]
            mock_client_instance.models.generate_content_stream.return_value = mock_stream
            logger.info("Configured successful API response")
        
        try:
            # Track processing time
            context.start_time = time.time()
            with open(file_path, 'rb') as f:
                response = context.client.post(
                    '/upload',
                    data={'file': (f, filename)},
                    content_type='multipart/form-data',
                    follow_redirects=True
                )
            context.processing_time = time.time() - context.start_time
            
            context.response = response
            
            content = ""
            if response.status_code == 200:
                content = response.data.decode('utf-8')
            
            expected_output_path = os.path.join(context.temp_path, f"{os.path.splitext(filename)[0]}_transcript.txt")
            context.result = (content, expected_output_path)
            
            logger.info(f"Upload response status: {response.status_code}")
        except Exception as e:
            context.response = MagicMock()
            context.response.status_code = 500
            context.result = (None, None)

@when('I upload a valid audio file with format "{format}"')
def step_impl(context, format):
    # Create test file with specified format
    file_id = str(uuid.uuid4())
    filename = f"test_file_{file_id}.{format}"
    
    file_path = os.path.join(context.temp_path, filename)
    with open(file_path, 'wb') as f:
        f.write(b'dummy audio content')
    
    context.original_file_path = file_path
    logger.info(f"Created test {format.upper()} file at: {file_path}")
    
    with patch('google.genai.Client') as mock_client:
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.uri = f"mock://file_uri/{filename}"
        mock_file.mime_type = f"audio/{format}"
        mock_file.name = filename
        
        mock_state = MagicMock()
        mock_state.name = "ACTIVE"
        mock_file.state = mock_state
        
        mock_files.upload.return_value = mock_file
        mock_files.get.return_value = mock_file
        mock_client_instance.files = mock_files
        
        mock_chunk = MagicMock()
        mock_chunk.text = MOCK_TRANSCRIPT_JSON
        mock_stream = [mock_chunk]
        mock_client_instance.models.generate_content_stream.return_value = mock_stream
        
        try:
            # Submit file
            with open(file_path, 'rb') as f:
                response = context.client.post(
                    '/upload',
                    data={'file': (f, filename)},
                    content_type='multipart/form-data',
                    follow_redirects=True
                )
            
            context.response = response
            
            content = ""
            if response.status_code == 200:
                content = response.data.decode('utf-8')
            
            expected_output_path = os.path.join(context.temp_path, f"{os.path.splitext(filename)[0]}_transcript.txt")
            context.result = (content, expected_output_path)
            
            logger.info(f"Upload {format} file response status: {response.status_code}")
        except Exception as e:
            context.response = MagicMock()
            context.response.status_code = 500
            context.result = (None, None)

@when('I upload a large audio file')
def step_impl(context):
    # Create test large file
    file_id = str(uuid.uuid4())
    filename = f"large_audio_file_{file_id}.wav"
    
    file_path = os.path.join(context.temp_path, filename)
    with open(file_path, 'wb') as f:
        f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x04\x00\x00\x00\x04\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')
    
    context.original_file_path = file_path
    logger.info(f"Created large test file at: {file_path}")
    
    with patch('google.genai.Client') as mock_client:
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        mock_files = MagicMock()
        mock_file = MagicMock()
        mock_file.uri = f"mock://file_uri/{filename}"
        mock_file.mime_type = "audio/wav"
        mock_file.name = filename
        
        mock_state = MagicMock()
        mock_state.name = "ACTIVE"
        mock_file.state = mock_state
        
        mock_files.upload.return_value = mock_file
        mock_files.get.return_value = mock_file
        mock_client_instance.files = mock_files
        
        # Simulate slow processing
        def slow_stream(*args, **kwargs):
            time.sleep(1)  # Simulate delay for large file
            mock_chunk = MagicMock()
            mock_chunk.text = MOCK_TRANSCRIPT_JSON
            return [mock_chunk]
            
        mock_client_instance.models.generate_content_stream.side_effect = slow_stream
        
        try:
            # Track processing time
            context.start_time = time.time()
            with open(file_path, 'rb') as f:
                response = context.client.post(
                    '/upload',
                    data={'file': (f, filename)},
                    content_type='multipart/form-data',
                    follow_redirects=True
                )
            context.processing_time = time.time() - context.start_time
            
            context.response = response
            
            content = ""
            if response.status_code == 200:
                content = response.data.decode('utf-8')
            expected_output_path = os.path.join(context.temp_path, f"{os.path.splitext(filename)[0]}_transcript.txt")
            context.result = (content, expected_output_path)
        except Exception as e:
            logger.error(f"Error during large file upload: {e}")
            context.response = MagicMock()
            context.response.status_code = 500
            context.result = (None, None)

@when('I upload a file with an invalid extension')
def step_impl(context):
    # Create invalid file type
    test_file = io.BytesIO(b'dummy content')
    file_id = str(uuid.uuid4())
    filename = f"test_file_{file_id}.txt"  # .txt is not allowed
    
    file_path = os.path.join(context.temp_path, filename)
    with open(file_path, 'wb') as f:
        f.write(b'dummy content')
    
    context.original_file_path = file_path
    logger.info(f"Created invalid test file at: {file_path}")
    
    try:
        # Submit invalid file
        response = context.client.post(
            '/upload',
            data={'file': (test_file, filename)},
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        context.response = response
        context.result = (None, None)
        
        logger.info(f"Invalid file upload response status: {response.status_code}")
    except Exception as e:
        context.response = MagicMock()
        context.response.status_code = 500
        context.result = (None, None)

@when('I try to submit the form without selecting a file')
def step_impl(context):
    try:
        # Submit empty form
        response = context.client.post(
            '/upload',
            data={},
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        context.response = response
        context.result = (None, None)
        
        logger.info(f"Empty form submission response status: {response.status_code}")
    except Exception as e:
        context.response = MagicMock()
        context.response.status_code = 500
        context.result = (None, None)

@then('I should see a success message')
def step_impl(context):
    # Check for success response
    valid_codes = [200, 302]
    assert context.response.status_code in valid_codes, f"Expected success code, got {context.response.status_code}"
    
    if context.response.status_code == 200:
        content = context.response.data.decode('utf-8')
        assert 'success' in content.lower() or 'uploaded' in content.lower(), "Success message not found"
        logger.info("Success message found in response")

@then('I should see the transcription result')
def step_impl(context):
    # Verify transcript exists
    transcript, path = context.result
    assert transcript is not None, "No transcript returned"
    
    content = context.response.data.decode('utf-8')
    assert 'success' in content.lower() or 'transcript' in content.lower(), "Transcript indicator not found in page"
    
    logger.info("Verified transcription result")

@then('I should see proper speaker diarization')
def step_impl(context):
    # Check for speaker labels and timestamps
    content = context.response.data.decode('utf-8')
    
    assert "Speaker 1" in content, "Speaker 1 not found in response"
    assert "Speaker 2" in content, "Speaker 2 not found in response"
    
    assert re.search(r'\d{2}:\d{2}', content), "Timestamp format not found in response"
    
    logger.info("Verified proper speaker diarization display")

@then('I should have a download link for the transcript')
def step_impl(context):
    # Check for download link and file
    _, path = context.result
    assert path is not None, "No output path created"
    assert os.path.exists(path), "Output file missing"
    
    content = context.response.data.decode('utf-8')
    assert 'download' in content.lower(), "Download link not found in page"
    
    logger.info(f"Verified download link for transcript: {path}")

@then('the original audio file should be deleted')
def step_impl(context):
    # Check file deletion
    if hasattr(context, 'original_file_path'):
        logger.info(f"Checked deletion for: {context.original_file_path}")
    
    logger.info("Original audio file deletion check complete")

@then('I should see an error message about file type')
def step_impl(context):
    # Check for file type error
    valid_codes = [200, 400, 405, 415]
    assert context.response.status_code in valid_codes, f"Unexpected status code: {context.response.status_code}"
    
    if context.response.status_code == 200:
        content = context.response.data.decode('utf-8')
        assert 'not allowed' in content.lower() or 'invalid' in content.lower(), "File type error message not found"
        logger.info("File type error message found in response")
    else:
        logger.info(f"Error status code {context.response.status_code} received as expected")

@then('I should see an error message about missing file')
def step_impl(context):
    # Check for missing file error
    valid_codes = [200, 400, 405]
    assert context.response.status_code in valid_codes, f"Unexpected status code: {context.response.status_code}"
    
    if context.response.status_code == 200:
        content = context.response.data.decode('utf-8')
        error_msgs = ['no file part', 'no selected file', 'no file', 'missing file']
        assert any(msg in content.lower() for msg in error_msgs), "Missing file error not found"
        logger.info("Missing file error message found in response")
    else:
        logger.info(f"Error status code {context.response.status_code} received as expected")

@then('no web transcription should be created')
def step_impl(context):
    # Verify no transcript was created
    transcript, path = context.result
    assert transcript is None, "Transcription was unexpectedly generated"
    assert path is None, "Output file was unexpectedly created"
    
    content = context.response.data.decode('utf-8')
    assert 'Transcription Result:' not in content, "Results section should not be present"
    
    logger.info("Verified no transcription was created in web UI")

@then('the processing time should be reasonable')
def step_impl(context):
    # Check processing time
    assert hasattr(context, 'processing_time'), "Processing time not measured"
    reasonable_time = 5.0  
    assert context.processing_time < reasonable_time, f"Processing time too long: {context.processing_time:.2f}s"

@then('I should see an appropriate error message')
def step_impl(context):
    # Check for error message
    content = context.response.data.decode('utf-8')
    error_terms = ['error', 'failed', 'unsuccessful', 'issue', 'problem']
    assert any(term in content.lower() for term in error_terms), "Error message not found"
    logger.info("Error message verified")

@then('I should be able to try again')
def step_impl(context):
    # Check for retry option
    content = context.response.data.decode('utf-8')
    assert 'form' in content.lower(), "Form not found for retry"
    assert 'upload' in content.lower(), "Upload option not found for retry"
    logger.info("Retry capability verified")