Feature: Transcript Processing
  As a user
  I want to transform structured Gemini API output
  Into a diarized human-readable transcript format

  @processing
  Scenario: Process structured JSON transcript with multiple speakers
    Given I have a structured JSON transcript from Gemini
    When I process the transcript with the TranscriptProcessor
    Then I should get a correctly formatted diarized transcript
    And each line should have the correct speaker and timestamp format

  @processing
  Scenario: Process structured JSON with missing fields
    Given I have a structured JSON with some missing speaker and timestamp fields
    When I process the transcript with the TranscriptProcessor
    Then I should get a formatted transcript with default values for missing fields

  @processing
  Scenario: Process malformed JSON input
    Given I have a malformed JSON response
    When I process the transcript with the TranscriptProcessor
    Then I should get an empty string as result

  @processing
  Scenario: Process empty transcript
    Given I have an empty transcript
    When I process the transcript with the TranscriptProcessor
    Then I should get an empty string as result

  @processing
  Scenario: Process non-array JSON
    Given I have a non-array JSON response
    When I process the transcript with the TranscriptProcessor
    Then I should get an empty string as result
    
  @processing
  Scenario: Process well-formed transcript with unusual speakers
    Given I have a structured JSON with unusual speaker names
    When I process the transcript with the TranscriptProcessor
    Then I should get a correctly formatted transcript with the unusual names