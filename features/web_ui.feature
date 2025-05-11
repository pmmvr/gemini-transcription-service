Feature: Web UI Audio Transcription
  As a user
  I want to transcribe audio files using a web interface
  So that I can get transcriptions without using the command line

  @web
  Scenario: Upload and transcribe a valid audio file
    Given I access the web upload page
    When I upload a valid audio file
    Then I should see a success message
    And I should see the transcription result

  @web
  Scenario: Attempt to upload an invalid file type
    Given I access the web upload page
    When I upload a file with an invalid extension
    Then I should see an error message about file type
    And no web transcription should be created

  @web
  Scenario: Attempt to upload with no file
    Given I access the web upload page
    When I try to submit the form without selecting a file
    Then I should see an error message about missing file
    And no web transcription should be created
    
  @web
  Scenario: Audio file upload success
    Given I access the web upload page
    When I upload a valid audio file
    Then I should see a success message
    
  @web
  Scenario Outline: Uploading different audio formats
    Given I access the web upload page
    When I upload a valid audio file with format "<format>"
    Then I should see a success message
    
    Examples:
      | format |
      | wav    |
      | mp3    |
      | m4a    |
      
  @web
  Scenario: Web interface handles large files appropriately
    Given I access the web upload page
    When I upload a large audio file
    Then I should see a success message
    And the processing time should be reasonable
    
  @web
  Scenario: Web interface handles API errors gracefully
    Given I access the web upload page
    And the Gemini API is configured to return an error for web tests
    When I upload a valid audio file
    Then I should see an appropriate error message
    And I should be able to try again