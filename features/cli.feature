Feature: CLI Audio Transcription
  As a user
  I want to transcribe audio files using the command line
  So that I can automate transcription of audio files

  @cli
  Scenario: Transcribe a valid audio file
    Given I have a valid audio file
    When I run the transcription command with the file path
    Then the transcription should be successful
    And the transcript should be saved to a file
    And the transcript should contain proper diarization

  @cli
  Scenario: Attempt to transcribe a non-existent file
    Given I have a non-existent audio file path
    When I run the transcription command with the file path
    Then the application should report that the file does not exist
    And no transcription should be created

  @cli
  Scenario: Transcribe an audio file with custom output directory
    Given I have a valid audio file
    And I have set a custom output directory
    When I run the transcription command with the file path
    Then the transcription should be successful
    And the transcript should be saved to the custom output directory

  @cli
  Scenario Outline: Transcribe with different audio formats
    Given I have a valid audio file with format "<format>"
    When I run the transcription command with the file path
    Then the transcription should be successful
    And the transcript should be saved to a file
    
    Examples:
      | format |
      | wav    |
      | mp3    |
      | m4a    |

  @cli
  Scenario: Transcription service handles API errors gracefully
    Given I have a valid audio file
    And the Gemini API is configured to return an error
    When I run the transcription command with the file path
    Then the application should handle the error gracefully
    And no transcription should be created
    
  @cli
  Scenario: End-to-end test with mocked API
    Given I have a valid audio file
    When I run the transcription command with the file path
    Then the transcription should be successful
    And the transcript should be saved to a file