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

  Scenario: Close down one of my campaigns
    Given I create a campaign named "Greyfen"
    When I delete my campaign
    Then it should be gone from my campaigns

  Scenario: Closing a campaign takes the characters at it with it
    Given I create a campaign named "Greyfen"
    And I have a character named "Aragorn" at that campaign
    When I delete my campaign
    Then that character should be gone too

  Scenario: Closing a campaign leaves the characters at my other tables alone
    Given I create a campaign named "Greyfen"
    And I create a campaign named "Fen Wardens"
    And I have a character named "Legolas" at my other campaign
    When I delete my campaign
    Then that other character should still be there

  Scenario: Delete a campaign owned by another game master
    When I delete the other game masters campaign
    Then I should get a not found error
    And the other game masters campaign should still be named "Someone elses table"

  Scenario: Delete a campaign that does not exist
    When I delete a campaign with an unknown ID
    Then I should get a not found error

  Scenario: Request a campaign that does not exist
    When I request a campaign with an unknown ID
    Then I should get a not found error

  Scenario: Create a campaign with no name
    When I create a campaign without a name
    Then I should get a validation error

  Scenario: Create a campaign named at more length than a name can hold
    When I create a campaign with a name of 201 characters
    Then I should get a validation error

  Scenario: Create a campaign described at more length than a description can hold
    When I create a campaign with a description of 1001 characters
    Then I should get a validation error

  Scenario: Rename a campaign to more than a name can hold
    Given I create a campaign named "Greyfen"
    When I rename my campaign to a name of 201 characters
    Then I should get a validation error
    And my campaign should still be named "Greyfen"

  Scenario: Name a campaign right up to the limit
    When I create a campaign with a name of 200 characters
    Then the campaign should be created

  Scenario: Browse campaigns without signing in
    When I list all campaigns without a token
    Then I should be told I am not authenticated