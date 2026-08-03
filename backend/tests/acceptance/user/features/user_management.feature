Feature: User Management
  As a player
  I want to register and log in
  So that I can access my account

  Scenario: Register a new user
    When I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    Then my account is created and I receive an access token

  Scenario: Registering signs me in, with no second step
    Given I register as "arwen" with email "arwen@rivendell.com" and password "evenstar1"
    When I request my profile
    Then I should see a user named "arwen" with email "arwen@rivendell.com"

  Scenario: Register with a username that is already taken
    Given I register as "legolas" with email "legolas@woodland.com" and password "greenleaf1"
    When I register as "legolas" with email "other@woodland.com" and password "otherpass"
    Then I should get a conflict error
    And I should not receive an access token

  Scenario: Log in with correct credentials
    Given I register as "gimli" with email "gimli@erebor.com" and password "axeandbeard"
    When I log in as "gimli" with password "axeandbeard"
    Then I should receive an access token

  Scenario: Log in with incorrect credentials
    Given I register as "boromir" with email "boromir@gondor.com" and password "onedoesnotsimply"
    When I log in as "boromir" with password "wrongpass"
    Then I should get an unauthorized error

  Scenario: Access my profile with a valid token
    Given I register as "frodo" with email "frodo@shire.com" and password "thering123"
    And I log in as "frodo" with password "thering123"
    When I request my profile
    Then I should see a user named "frodo" with email "frodo@shire.com"

  Scenario: Access my profile without a token
    When I request my profile without a token
    Then I should get an unauthorized error

  Scenario: Stay signed in once the access token has run out
    Given I register as "eowyn" with email "eowyn@rohan.com" and password "shieldmaiden1"
    And I log in as "eowyn" with password "shieldmaiden1"
    When I refresh my session
    And I request my profile
    Then I should see a user named "eowyn" with email "eowyn@rohan.com"

  Scenario: Refreshing hands back a new access token
    Given I register as "eomer" with email "eomer@rohan.com" and password "firefoot123"
    When I refresh my session
    Then I should receive an access token

  Scenario: Refreshing with no refresh cookie
    When I refresh my session
    Then I should get an unauthorized error

  Scenario: The refresh token is not something a script can read
    When I register as "theoden" with email "theoden@rohan.com" and password "snowmane123"
    Then the refresh cookie is httpOnly, secure, same-site and scoped to /users

  Scenario: Refreshing replaces the refresh token it was given
    Given I register as "hama" with email "hama@rohan.com" and password "doorward123"
    When I refresh my session
    Then I should hold a different refresh token

  Scenario: A refresh token cannot be spent twice
    Given I register as "grima" with email "grima@rohan.com" and password "wormtongue1"
    And someone takes a copy of my refresh cookie
    And I refresh my session
    When the copy is presented
    Then I should get an unauthorized error

  Scenario: A replayed refresh token takes the whole session down with it
    Given I register as "saruman" with email "saruman@isengard.com" and password "manycolours"
    And someone takes a copy of my refresh cookie
    And I refresh my session
    When the copy is presented
    Then my session can no longer be refreshed
