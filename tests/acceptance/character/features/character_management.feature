Feature: Character Management
  As a player
  I want to manage my D&D characters
  So that I can keep track of all my characters

  Background:
    Given I am logged in as a player

  Scenario: Create and retrieve a character
    Given I create a character named "Aragorn" with class "Ranger"
    When I retrieve the character by its ID
    Then I should see a character named "Aragorn" with class "Ranger" and level 1

  Scenario: Browse all my characters
    Given I create a character named "Aragorn" with class "Ranger"
    And I create a character named "Legolas" with class "Archer"
    And I create a character named "Gimli" with class "Fighter"
    When I list all characters
    Then I should see "Aragorn" in the list
    And I should see "Legolas" in the list
    And I should see "Gimli" in the list

  Scenario: Request a character that does not exist
    When I request a character with an unknown ID
    Then I should get a not found error

  Scenario: Create a character with a missing field
    When I create a character without a class
    Then I should get a validation error