Feature: Character Management
  As a game master
  I want to keep the characters at my table alongside the campaign they play in
  So that a sheet is never adrift from the game it belongs to

  Background:
    Given I am logged in as a game master
    And I create a campaign named "The Hollow Beneath Greyfen"
    And another game master runs a campaign named "Someone elses table"
    And that game master has a character named "Boromir" at it

  Scenario: Create and retrieve a character
    Given I create a character named "Aragorn" at my campaign
    When I retrieve the character by its ID
    Then I should see a character named "Aragorn"
    And the character should be owned by me
    And the character should be at my campaign

  Scenario: Give a character a description
    Given I create a character named "Aragorn" described as "A ranger of the North"
    When I retrieve the character by its ID
    Then I should see the description "A ranger of the North"

  Scenario: Browse the characters at my table
    Given I create a character named "Aragorn" at my campaign
    And I create a character named "Legolas" at my campaign
    When I list the characters at my campaign
    Then I should see "Aragorn" in the list
    And I should see "Legolas" in the list

  Scenario: Rename one of my characters
    Given I create a character named "Aragorn" at my campaign
    When I rename my character to "Strider"
    And I retrieve the character by its ID
    Then I should see a character named "Strider"

  Scenario: Browse the characters at a table I do not run
    When I list the characters at the other game masters campaign
    Then I should get a not found error

  Scenario: Add a character to a table I do not run
    When I create a character named "Aragorn" at the other game masters campaign
    Then I should get a not found error

  Scenario: Rename a character that does not exist
    When I rename a character with an unknown ID
    Then I should get a not found error

  Scenario: Read a character at a table I do not run
    When I retrieve the other game masters character
    Then I should get a not found error

  Scenario: Edit a character at a table I do not run
    When I rename the other game masters character to "Stolen"
    Then I should get a not found error
    And the other game masters character should still be named "Boromir"

  Scenario: Read a character through a campaign it is not at
    Given I create a character named "Aragorn" at my campaign
    And I create a second campaign named "Fen Wardens"
    When I retrieve that character through my other campaign
    Then I should get a not found error

  Scenario: Remove one of my characters
    Given I create a character named "Aragorn" at my campaign
    When I delete my character
    Then it should be gone from my table

  Scenario: Removing a character leaves the rest of my table alone
    Given I create a character named "Aragorn" at my campaign
    And I create a character named "Legolas" at my campaign
    And I delete my character
    When I list the characters at my campaign
    Then I should see "Legolas" in the list

  Scenario: Delete a character at a table I do not run
    When I delete the other game masters character
    Then I should get a not found error
    And the other game masters character should still be named "Boromir"

  Scenario: Delete a character through a campaign it is not at
    Given I create a character named "Aragorn" at my campaign
    And I create a second campaign named "Fen Wardens"
    When I delete that character through my other campaign
    Then I should get a not found error
    And my character should still be named "Aragorn"

  Scenario: Delete a character that does not exist
    When I delete a character with an unknown ID
    Then I should get a not found error

  Scenario: Request a character that does not exist
    When I request a character with an unknown ID
    Then I should get a not found error

  Scenario: Request a campaign that does not exist
    When I list the characters at an unknown campaign
    Then I should get a not found error

  Scenario: Create a character with no name
    When I create a character without a name
    Then I should get a validation error

  Scenario: Browse characters without signing in
    When I list the characters at my campaign without a token
    Then I should be told I am not authenticated