from behave import given, when, then
import os
import tempfile

class MockSummarizationService:
    def __init__(self, available=True):
        self.available = available
        self.error_mode = False

    def summarize(self, transcript_text):
        # Handle various error cases and return mock summary
        if not self.available:
            raise ConnectionError("Summarization service unavailable")
        if self.error_mode:
            raise Exception("Simulated service error")
        if not transcript_text or transcript_text.strip() == "EMPTY":
            return "Insufficient content for summary."
        if transcript_text.strip() == "ERROR_TRIGGER":
             raise ValueError("Simulated error during summarization")
        return f"This is a summary of: {transcript_text[:50]}..."

    def set_error_mode(self, error_mode):
        self.error_mode = error_mode

@given('I have a valid transcript file')
def step_impl_valid_transcript_file(context):
    # Create temp dir and file with valid content
    context.temp_dir = tempfile.mkdtemp()
    context.transcript_file_path = os.path.join(context.temp_dir, "valid_transcript.txt")
    with open(context.transcript_file_path, "w") as f:
        f.write("This is the full text of the transcript that needs to be summarized. It is a long text.")
    context.transcript_content = "This is the full text of the transcript that needs to be summarized. It is a long text."

@given('I have an empty transcript file')
def step_impl_empty_transcript_file(context):
    # Create temp dir and file with empty content
    context.temp_dir = tempfile.mkdtemp()
    context.transcript_file_path = os.path.join(context.temp_dir, "empty_transcript.txt")
    with open(context.transcript_file_path, "w") as f:
        f.write("EMPTY")
    context.transcript_content = "EMPTY"

@given('I have a non-existent transcript file path')
def step_impl_non_existent_file(context):
    # Set path to non-existent file
    context.temp_dir = tempfile.mkdtemp()
    context.transcript_file_path = os.path.join(context.temp_dir, "non_existent_transcript.txt")
    context.transcript_content = None

@given('the summarization service is available')
def step_impl_service_available(context):
    # Init mock service in available state
    context.summarization_service = MockSummarizationService(available=True)

@given('the summarization service is unavailable or returns an error')
def step_impl_service_unavailable(context):
    # Init mock service in unavailable state
    context.summarization_service = MockSummarizationService(available=False)
    # To test specific error on request:
    # context.summarization_service = MockSummarizationService(available=True)
    # context.summarization_service.set_error_mode(True)


@when('I request a summary of the transcript')
def step_impl_request_summary(context):
    try:
        # Read transcript and request summary
        if hasattr(context, 'transcript_file_path') and os.path.exists(context.transcript_file_path):
            with open(context.transcript_file_path, "r") as f:
                transcript_text = f.read()
        elif context.transcript_content is not None:
            transcript_text = context.transcript_content
        else:
            raise FileNotFoundError(f"File not found: {context.transcript_file_path}")

        context.summary_result = context.summarization_service.summarize(transcript_text)
    except FileNotFoundError as e:
        context.error_message = str(e)
        context.summary_result = None
    except ConnectionError as e:
        context.error_message = str(e)
        context.summary_result = None
    except Exception as e:
        context.error_message = str(e)
        context.summary_result = None

@when('I request a summary using that path')
def step_impl_request_summary_non_existent(context):
    try:
        # Check file exists before attempting to read
        if not os.path.exists(context.transcript_file_path):
             raise FileNotFoundError(f"File not found: {context.transcript_file_path}")
        with open(context.transcript_file_path, "r") as f:
            transcript_text = f.read()
        context.summary_result = context.summarization_service.summarize(transcript_text)

    except FileNotFoundError as e:
        context.error_message = str(e)
        context.summary_result = None
    except Exception as e:
        context.error_message = str(e)
        context.summary_result = None


@then('I should receive a non-empty summary string')
def step_impl_receive_non_empty_summary(context):
    # Verify summary is valid
    assert context.summary_result is not None, "Summary result is None"
    assert isinstance(context.summary_result, str), "Summary is not a string"
    assert len(context.summary_result.strip()) > 0, "Summary string is empty"
    assert "Insufficient content" not in context.summary_result

@then('the summary should indicate that the content is insufficient or empty')
def step_impl_summary_indicates_insufficient(context):
    # Verify empty content message
    assert context.summary_result is not None, "Summary result is None"
    assert "Insufficient content for summary." in context.summary_result

@then('I should receive an error related to file not found')
def step_impl_receive_file_not_found_error(context):
    # Verify file not found error
    assert hasattr(context, 'error_message') and context.error_message is not None, "No error message was captured"
    assert "File not found" in context.error_message or "No such file or directory" in context.error_message

@then('I should receive an error indicating service failure')
def step_impl_receive_service_failure_error(context):
    # Verify service failure error
    assert hasattr(context, 'error_message') and context.error_message is not None, "No error message was captured for service failure"
    assert "Summarization service unavailable" in context.error_message or "Simulated service error" in context.error_message

def after_scenario(context, scenario):
    # Cleanup temp files
    if hasattr(context, 'temp_dir') and os.path.exists(context.temp_dir):
        import shutil
        shutil.rmtree(context.temp_dir) 