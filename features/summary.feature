Feature: Transcript Summarization
  As a user
  I want to generate a concise summary from a transcript
  So that I can quickly understand its content

  @summary
  Scenario: Summarize a valid transcript
    Given I have a valid transcript file
    And the summarization service is available
    When I request a summary of the transcript
    Then I should receive a non-empty summary string

  @summary
  Scenario: Attempt to summarize an empty transcript
    Given I have an empty transcript file
    And the summarization service is available
    When I request a summary of the transcript
    Then the summary should indicate that the content is insufficient or empty

  @summary
  Scenario: Attempt to summarize a non-existent transcript file
    Given I have a non-existent transcript file path
    And the summarization service is available
    When I request a summary using that path
    Then I should receive an error related to file not found

  @summary
  Scenario: Summarization service unavailable
    Given I have a valid transcript file
    And the summarization service is unavailable or returns an error
    When I request a summary of the transcript
    Then I should receive an error indicating service failure 