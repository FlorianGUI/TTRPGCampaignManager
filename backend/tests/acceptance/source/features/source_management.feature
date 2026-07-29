Feature: Source Management
  As a game master
  I want to record the books, magazines and notes my material comes from
  So that everything in my library is traceable to where it was published

  Background:
    Given I am logged in as a game master

  Scenario: Create and retrieve a source
    Given I create a source titled "SRD 5.1"
    When I retrieve the source by its ID
    Then I should see a source titled "SRD 5.1"
    And the source should be owned by me

  Scenario: Browse all my sources
    Given I create a source titled "SRD 5.1"
    And I create a source titled "Fen Wardens notes"
    And I create a source titled "Dragon Magazine issue 4"
    When I list all sources
    Then I should see "SRD 5.1" in the list
    And I should see "Fen Wardens notes" in the list
    And I should see "Dragon Magazine issue 4" in the list

  Scenario: Request a source that does not exist
    When I request a source with an unknown ID
    Then I should get a not found error

  Scenario: Create a source with no title
    When I create a source without a title
    Then I should get a validation error

  Scenario: Browse sources without signing in
    When I list all sources without a token
    Then I should be told I am not authenticated