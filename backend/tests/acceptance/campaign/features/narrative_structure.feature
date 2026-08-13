Feature: Narrative Structure
  As a game master
  I want acts and sequences to group my scenes, and to move things between them
  So that the shape of my campaign can change as the story does

  Background:
    Given I am logged in as a game master
    And I create a campaign named "The Drowning of Greyfen"
    And I create a second campaign named "Fen Wardens"
    And another game master runs a campaign named "Someone elses table"

  Scenario: Divide a campaign into acts
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create an act named "Act II — The War for the Fen" in my campaign
    When I list the acts in my campaign
    Then the acts should read "Act I — Water Rising, Act II — The War for the Fen"

  Scenario: A sequence goes inside an act
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    When I retrieve the sequence by its ID
    Then the sequence should be under that act

  Scenario: A sequence may skip the act and hang off the campaign
    Given I create a sequence named "Loose thread" in my campaign
    When I retrieve the sequence by its ID
    Then the sequence should be under no act

  Scenario: A scene may hang off a sequence
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    And I create a scene named "Arrival at dusk" under that sequence
    When I retrieve the scene by its ID
    Then the scene should be under that sequence

  Scenario: A scene may skip the sequence and hang off the act
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a scene named "Interlude — the road back" under that act
    When I retrieve the scene by its ID
    Then the scene should be under that act
    And the scene should be under no sequence

  Scenario: A scene may skip both and hang off the campaign
    Given I create a scene named "Session zero" in my campaign
    When I retrieve the scene by its ID
    Then the scene should be under no act
    And the scene should be under no sequence

  Scenario: A scene cannot hang off an act and a sequence at once
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    When I create a scene naming both that act and that sequence
    Then the request should be rejected as invalid

  Scenario: Positions count from the parent, not the campaign
    Given I create a scene named "Session zero" in my campaign
    And I create an act named "Act I — Water Rising" in my campaign
    And I create a scene named "Arrival at dusk" under that act
    When I retrieve the scene by its ID
    Then the scene should be first among its siblings

  Scenario: Move a scene from one act to another
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a scene named "The muster at Greyfen" under that act
    And I create an act named "Act II — The War for the Fen" in my campaign
    When I move the scene under the second act
    Then the scene should be under the second act

  Scenario: Take a scene out of its act and give it to the campaign
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a scene named "Interlude — the road back" under that act
    When I move the scene to the campaign
    Then the scene should be under no act

  Scenario: A scene cannot be filed under another campaigns act
    Given I create an act named "Act I — Water Rising" in my second campaign
    When I create a scene in my campaign under that act
    Then I should get a not found error

  Scenario: A scene cannot be moved under another campaigns act
    Given I create a scene named "The muster at Greyfen" in my campaign
    And I create an act named "Act I — Water Rising" in my second campaign
    When I move the scene under that act
    Then I should get a not found error

  Scenario: A sequence cannot be written under another campaigns act
    Given I create an act named "Act I — Water Rising" in my second campaign
    When I create a sequence in my campaign under that act
    Then I should get a not found error

  Scenario: Read the acts of a campaign I do not run
    When I list the acts in the other game masters campaign
    Then I should get a not found error

  Scenario: An act that does not exist cannot be a parent
    When I create a scene in my campaign under an act that does not exist
    Then I should get a not found error

  Scenario: Rename an act
    Given I create an act named "Act I" in my campaign
    When I rename the act to "Act I — Water Rising"
    And I retrieve the act by its ID
    Then I should see an act named "Act I — Water Rising"

  Scenario: Cut an empty act
    Given I create an act named "Act III — Low Water" in my campaign
    When I delete the act
    And I list the acts in my campaign
    Then the acts should be empty

  Scenario: Browse every sequence in the campaign, wherever it hangs
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    And I create a sequence named "Loose thread" in my campaign
    When I list the sequences in my campaign
    Then I should see 2 sequences

  Scenario: Move a sequence into an act
    Given I create a sequence named "Loose thread" in my campaign
    And I create an act named "Act I — Water Rising" in my campaign
    When I move the sequence under that act
    Then the sequence should be under that act

  Scenario: Take a sequence out of its act
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    When I move the sequence to the campaign
    Then the sequence should be under no act

  Scenario: Cut a sequence
    Given I create a sequence named "Loose thread" in my campaign
    When I delete the sequence
    And I list the sequences in my campaign
    Then I should see 0 sequences

  Scenario: Rewriting a sequence does not move it
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    When I rewrite the sequence
    And I retrieve the sequence by its ID
    Then the sequence should be under that act

  Scenario: Drop a scene above the one it used to follow
    Given I create a scene named "Arrival at dusk" in my campaign
    And I create a scene named "The sunken arch" in my campaign
    When I drop the second scene at the top
    And I list the scenes in my campaign
    Then the scenes should read "The sunken arch, Arrival at dusk"

  Scenario: Drop a scene between two others
    Given I create a scene named "Arrival at dusk" in my campaign
    And I create a scene named "The sunken arch" in my campaign
    And I create a scene named "The nesting pair" in my campaign
    When I drop the last scene after the first
    And I list the scenes in my campaign
    Then the scenes should read "Arrival at dusk, The nesting pair, The sunken arch"

  Scenario: Reorder the acts of a campaign
    Given I create an act named "Act I" in my campaign
    And I create an act named "Act II" in my campaign
    When I drop the second act at the top
    And I list the acts in my campaign
    Then the acts should read "Act II, Act I"

  Scenario: Drop a scene into another act and place it at once
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a scene named "The muster at Greyfen" under that act
    And I create an act named "Act II — The War for the Fen" in my campaign
    When I drop the scene into the second act
    Then the scene should be under the second act

  Scenario: An anchor from another act is refused
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a scene named "Interlude" under that act
    And I create a scene named "Session zero" in my campaign
    When I drop the campaigns scene after the one in the act
    Then I should get a not found error

  Scenario: Removing an act hands its scenes to the campaign
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a scene named "Interlude — the road back" under that act
    When I delete the act
    And I retrieve the scene by its ID
    Then the scene should be under no act

  Scenario: Removing a sequence hands its scenes to the act above it
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    And I create a scene named "Arrival at dusk" under that sequence
    When I delete the sequence
    And I retrieve the scene by its ID
    Then the scene should be under that act
    And the scene should be under no sequence

  Scenario: Closing a campaign takes the whole tree with it
    Given I create an act named "Act I — Water Rising" in my campaign
    And I create a sequence named "The Causeway" under that act
    And I create a scene named "Arrival at dusk" under that sequence
    When I delete my campaign
    And I list the acts in my campaign
    Then I should get a not found error
