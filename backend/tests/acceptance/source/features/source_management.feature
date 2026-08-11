Feature: Source Management
  As a game master
  I want to record the books, magazines and notes my material comes from
  So that everything in my library is traceable to where it was published

  Background:
    Given I am logged in as a game master
    And another game master owns a source titled "Xanathars Guide"

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
    And I should not see "Xanathars Guide" in the list

  Scenario: Rename one of my sources
    Given I create a source titled "SRD 5.0"
    When I rename my source to "SRD 5.1"
    And I retrieve the source by its ID
    Then I should see a source titled "SRD 5.1"

  Scenario: The library puts what I last worked on first
    Given I create a source titled "SRD 5.1"
    And I create a source titled "Monster Manual"
    When I rename my source to "System Reference Document 5.1"
    And I list all sources
    Then "System Reference Document 5.1" should be first in the list

  Scenario: Read a source owned by another game master
    When I retrieve the other game masters source
    Then I should get a not found error

  Scenario: Rename a source owned by another game master
    When I rename the other game masters source to "Xanathars Guide to Nothing"
    Then I should get a not found error
    And the other game masters source should still be titled "Xanathars Guide"

  Scenario: Remove one of my sources
    Given I create a source titled "SRD 5.1"
    When I delete my source
    Then it should be gone from my library

  Scenario: A source I deleted is out of my library
    Given I create a source titled "SRD 5.1"
    And I create a source titled "Monster Manual"
    And I delete my source
    When I list all sources
    Then I should not see "SRD 5.1" in the list
    And I should see "Monster Manual" in the list

  Scenario: Delete a source owned by another game master
    When I delete the other game masters source
    Then I should get a not found error
    And the other game masters source should still be titled "Xanathars Guide"

  Scenario: Delete a source that does not exist
    When I delete a source with an unknown ID
    Then I should get a not found error

  Scenario: Request a source that does not exist
    When I request a source with an unknown ID
    Then I should get a not found error

  Scenario: Create a source with no title
    When I create a source without a title
    Then I should get a validation error

  Scenario: Browse sources without signing in
    When I list all sources without a token
    Then I should be told I am not authenticated