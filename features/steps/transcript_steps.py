import json
import re
import os
import tempfile
from behave import given, when, then
from src.gemini_transcription_service.transcript_processor import TranscriptProcessor

@given('I have a structured JSON transcript from Gemini')
def step_impl(context):
    # Create sample JSON with speaker, timestamp, and text fields
    context.transcript_json = json.dumps([
        {"speaker": "Speaker 1", "timestamp": "00:05", "text": "Hello, how are you today?"},
        {"speaker": "Speaker 2", "timestamp": "00:12", "text": "I'm doing well, thank you for asking."},
        {"speaker": "Speaker 1", "timestamp": "00:18", "text": "That's great to hear. What are your plans?"},
        {"speaker": "Speaker 2", "timestamp": "00:25", "text": "I have a few meetings then I'll work on the project."}
    ])

@given('I have a structured JSON with some missing speaker and timestamp fields')
def step_impl(context):
    # Create JSON with some missing fields to test fallbacks
    context.transcript_json = json.dumps([
        {"speaker": "Speaker 1", "timestamp": "00:05", "text": "Hello, how are you today?"},
        {"text": "I'm doing well, thank you for asking."},
        {"speaker": "Speaker 1", "text": "That's great to hear."},
        {"timestamp": "00:25", "text": "I have a few meetings today."}
    ])

@given('I have a malformed JSON response')
def step_impl(context):
    # Invalid JSON to test error handling
    context.transcript_json = "{This is not valid JSON: 'missing quotes', unclosed brackets"

@given('I have a formatted transcript')
def step_impl(context):
    # Pre-formatted transcript for testing
    context.formatted_transcript = """[Speaker 1 00:05]: Hello, how are you today?
[Speaker 2 00:12]: I'm doing well, thank you for asking.
[Speaker 1 00:18]: That's great to hear. What are your plans?
[Speaker 2 00:25]: I have a few meetings then I'll work on the project."""
    
    # Create dummy audio file
    context.input_path = os.path.join(context.temp_path, "test_audio.wav")
    with open(context.input_path, 'wb') as f:
        f.write(b'dummy audio content')

@given('I have an empty transcript')
def step_impl(context):
    # Empty transcript for edge case testing
    context.transcript_json = ""

@given('I have a non-array JSON response')
def step_impl(context):
    # JSON that's valid but wrong format (not an array)
    context.transcript_json = json.dumps({
        "type": "non-array",
        "message": "This is not an array of transcript segments"
    })

@given('I have a structured JSON with unusual speaker names')
def step_impl(context):
    # Test handling of non-standard speaker names
    context.transcript_json = json.dumps([
        {"speaker": "CEO John", "timestamp": "00:05", "text": "Welcome to the meeting."},
        {"speaker": "Dr. Smith", "timestamp": "00:12", "text": "Thank you for inviting me."},
        {"speaker": "Customer 123", "timestamp": "00:18", "text": "I have a question about the product."},
        {"speaker": "Support@AI", "timestamp": "00:25", "text": "I can help with that question."}
    ])

@when('I process the transcript with the TranscriptProcessor')
def step_impl(context):
    # Process transcript using the processor
    processor = TranscriptProcessor()
    context.processor = processor
    context.processed_result = processor.process_response(context.transcript_json)

@then('I should get a correctly formatted diarized transcript')
def step_impl(context):
    # Verify result is not empty
    assert context.processed_result, "Empty result"
    
    # Check line count matches expected
    lines = context.processed_result.strip().split('\n')
    expected = len(json.loads(context.transcript_json))
    assert len(lines) == expected, f"Expected {expected} lines, got {len(lines)}"
    
    # Verify content is present
    assert "Hello, how are you today?" in context.processed_result
    assert "I'm doing well" in context.processed_result
    assert "That's great to hear" in context.processed_result
    assert "I have a few meetings" in context.processed_result

@then('each line should have the correct speaker and timestamp format')
def step_impl(context):
    # Check format of each line
    lines = context.processed_result.strip().split('\n')
    pattern = r'^\[([^\]]+) (\d{2}:\d{2})\]: (.+)$'
    
    for line in lines:
        match = re.match(pattern, line)
        assert match, f"Bad format: {line}"
        
        speaker, timestamp, text = match.groups()
        
        # Verify each component
        assert speaker, f"Empty speaker: {line}"
        assert re.match(r'^\d{2}:\d{2}$', timestamp), f"Bad timestamp: {timestamp}"
        assert text.strip(), "Empty text"

@then('I should get a formatted transcript with default values for missing fields')
def step_impl(context):
    # Check line count
    lines = context.processed_result.strip().split('\n')
    assert len(lines) == 4, f"Expected 4 lines, got {len(lines)}"

    # Verify default values are used
    assert "[Unknown Speaker" in context.processed_result
    assert "00:00" in context.processed_result
    
    # Verify content is present
    assert "I'm doing well" in context.processed_result
    assert "That's great to hear" in context.processed_result
    assert "I have a few meetings" in context.processed_result

@then('I should get an empty string as result')
def step_impl(context):
    # Check empty result for invalid input
    assert context.processed_result == "", "Should be empty for invalid input"

@then('I should get a correctly formatted transcript with the unusual names')
def step_impl(context):
    # Verify result is not empty
    assert context.processed_result, "Empty result"
    
    # Check unusual speaker names are preserved
    assert "[CEO John" in context.processed_result
    assert "[Dr. Smith" in context.processed_result
    assert "[Customer 123" in context.processed_result
    assert "[Support@AI" in context.processed_result
    
    # Verify content is present
    assert "Welcome to the meeting" in context.processed_result
    assert "Thank you for inviting me" in context.processed_result
    assert "I have a question about the product" in context.processed_result
    assert "I can help with that question" in context.processed_result

@then('the transcript should be saved to the specified location')
def step_impl(context):
    # Verify output path exists
    assert context.output_path, "No output path returned"
    assert os.path.exists(context.output_path), f"Output file doesn't exist at {context.output_path}"
    
    # Check file is in expected directory
    assert context.output_path.startswith(context.output_dir), f"File {context.output_path} not in expected directory {context.output_dir}"
    
    # Verify file content matches expected transcript
    with open(context.output_path, 'r') as f:
        content = f.read()
    
    assert content.strip() == context.formatted_transcript.strip(), "File content doesn't match expected transcript"
