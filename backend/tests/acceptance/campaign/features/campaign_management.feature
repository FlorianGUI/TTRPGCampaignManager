Feature: Campaign Management
  As a game master
  I want to run campaigns of my own
  So that I have a table to hang my material and my players' characters off

  Background:
    Given I am logged in as a game master
    And another game master owns a campaign named "Someone elses table"

  Scenario: Create and retrieve a campaign
    Given I create a campaign named "The Hollow Beneath Greyfen"
    When I retrieve the campaign by its ID
    Then I should see a campaign named "The Hollow Beneath Greyfen"
    And the campaign should be owned by me

  Scenario: Browse all my campaigns
    Given I create a campaign named "The Hollow Beneath Greyfen"
    And I create a campaign named "Fen Wardens"
    When I list all campaigns
    Then I should see "The Hollow Beneath Greyfen" in the campaign list
    And I should see "Fen Wardens" in the campaign list
    And I should not see "Someone elses table" in the campaign list

  Scenario: Rename one of my campaigns
    Given I create a campaign named "Greyfen"
    When I rename my campaign to "The Hollow Beneath Greyfen"
    And I retrieve the campaign by its ID
    Then I should see a campaign named "The Hollow Beneath Greyfen"

  Scenario: Read a campaign owned by another game master
    When I retrieve the other game masters campaign
    Then I should get a not found error

  Scenario: Rename a campaign owned by another game master
    When I rename the other game masters campaign to "Mine now"
    Then I should get a not found error
    And the other game masters campaign should still be named "Someone elses table"

  Scenario: Request a campaign that does not exist
    When I request a campaign with an unknown ID
    Then I should get a not found error

  Scenario: Create a campaign with no name
    When I create a campaign without a name
    Then I should get a validation error

  Scenario: Browse campaigns without signing in
    When I list all campaigns without a token
    Then I should be told I am not authenticated