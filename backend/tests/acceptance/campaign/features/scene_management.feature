Feature: Scene Management
  As a game master
  I want to write the scenes of my campaign and keep them in the order the story goes in
  So that my prep is organised the way I plan an evening rather than the way I typed it

  Background:
    Given I am logged in as a game master
    And I create a campaign named "The Drowning of Greyfen"
    And another game master runs a campaign named "Someone elses table"
    And that game master has a scene named "Session zero" in it

  Scenario: Write a scene and read it back
    Given I create a scene named "The parley at Stonegate" in my campaign
    When I retrieve the scene by its ID
    Then I should see a scene named "The parley at Stonegate"
    And the scene should be in my campaign

  Scenario: A campaign with scenes and no acts is a working campaign
    Given I create a scene named "Arrival at dusk" in my campaign
    And I create a scene named "The sunken arch" in my campaign
    When I list the scenes in my campaign
    Then I should see 2 scenes

  Scenario: A scene body keeps every character it was written with
    Given I create a scene named "The sunken arch" with a read-aloud body
    When I retrieve the scene by its ID
    Then the body should come back byte for byte

  Scenario: A new scene starts planned and unwritten
    Given I create a scene named "The muster at Greyfen" in my campaign
    When I retrieve the scene by its ID
    Then the scene should be planned
    And the body should be empty

  Scenario: Scenes come back in the order the story goes in
    Given I create a scene named "Arrival at dusk" in my campaign
    And I create a scene named "The sunken arch" in my campaign
    And I create a scene named "The nesting pair" in my campaign
    When I list the scenes in my campaign
    Then the scenes should read "Arrival at dusk, The sunken arch, The nesting pair"

  Scenario: Mark a scene as played
    Given I create a scene named "The parley at Stonegate" in my campaign
    When I mark the scene as played
    And I retrieve the scene by its ID
    Then the scene should be played

  Scenario: Rewriting a scene leaves it where it is in the story
    Given I create a scene named "Arrival at dusk" in my campaign
    And I create a scene named "The sunken arch" in my campaign
    When I rewrite the scene "The sunken arch"
    And I list the scenes in my campaign
    Then the scenes should read "Arrival at dusk, The sunken arch"

  Scenario: Cut a scene from the campaign
    Given I create a scene named "The rubbing" in my campaign
    When I delete the scene
    And I list the scenes in my campaign
    Then I should see 0 scenes

  Scenario: Read the prep of a campaign I do not run
    When I list the scenes in the other game masters campaign
    Then I should get a not found error

  Scenario: Reach a scene through a campaign that is not mine
    When I retrieve the other game masters scene through their campaign
    Then I should get a not found error

  Scenario: Reach another game masters scene through my own campaign
    When I retrieve the other game masters scene through my campaign
    Then I should get a not found error

  Scenario: Rewrite a scene I did not write
    When I rewrite the other game masters scene through my campaign
    Then I should get a not found error

  Scenario: Delete a scene I did not write
    When I delete the other game masters scene through my campaign
    Then I should get a not found error

  Scenario: Write a scene in a campaign that does not exist
    When I create a scene in a campaign that does not exist
    Then I should get a not found error

  Scenario: Closing a campaign takes its prep with it
    Given I create a scene named "Arrival at dusk" in my campaign
    When I delete my campaign
    And I list the scenes in my campaign
    Then I should get a not found error
