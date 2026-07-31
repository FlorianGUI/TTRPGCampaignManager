Feature: Character Management
  As a player
  I want to manage my D&D characters
  So that I can keep track of all my characters

  Background:
    Given I am logged in as a player
    And another player owns a character named "Boromir"
    And that player also runs a campaign named "Someone elses table"

  Scenario: Create and retrieve a character
    Given I create a character named "Aragorn" with class "Ranger"
    When I retrieve the character by its ID
    Then I should see a character named "Aragorn" with class "Ranger" and level 1
    And the character should be owned by me

  Scenario: Browse all my characters
    Given I create a character named "Aragorn" with class "Ranger"
    And I create a character named "Legolas" with class "Archer"
    And I create a character named "Gimli" with class "Fighter"
    When I list all characters
    Then I should see "Aragorn" in the list
    And I should see "Legolas" in the list
    And I should see "Gimli" in the list
    And I should not see "Boromir" in the list

  Scenario: Level up one of my characters
    Given I create a character named "Aragorn" with class "Ranger"
    When I rename my character to "Strider" at level 5
    And I retrieve the character by its ID
    Then I should see a character named "Strider" with class "Ranger" and level 5

  Scenario: Read a character owned by another player
    When I retrieve the other players character
    Then I should get a not found error

  Scenario: Edit a character owned by another player
    When I rename the other players character to "Stolen"
    Then I should get a not found error
    And the other players character should still be named "Boromir"

  Scenario: Bring my character to a campaign I run
    Given I create a campaign named "The Hollow Beneath Greyfen"
    And I create a character named "Aragorn" with class "Ranger" in that campaign
    When I retrieve the character by its ID
    Then the character should be at my campaign

  Scenario: Take my character back off the table
    Given I create a campaign named "The Hollow Beneath Greyfen"
    And I create a character named "Aragorn" with class "Ranger" in that campaign
    When I rename my character to "Aragorn" at level 1
    And I retrieve the character by its ID
    Then the character should be at no campaign

  Scenario: Put a character in a campaign I do not run
    When I create a character named "Aragorn" with class "Ranger" in the other players campaign
    Then I should get a not found error

  Scenario: Move one of my characters to a campaign I do not run
    Given I create a character named "Aragorn" with class "Ranger"
    When I move my character to the other players campaign
    Then I should get a not found error
    And my character should still be at no campaign

  Scenario: Request a character that does not exist
    When I request a character with an unknown ID
    Then I should get a not found error

  Scenario: Create a character with a missing field
    When I create a character without a class
    Then I should get a validation error

  Scenario: Browse characters without signing in
    When I list all characters without a token
    Then I should be told I am not authenticated