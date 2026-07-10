Feature: User Management
  As a player
  I want to register and log in
  So that I can access my account

  Scenario: Register a new user
    When I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    Then I should see a user named "aragorn" with email "aragorn@gondor.com"

  Scenario: Register with a username that is already taken
    Given I register as "legolas" with email "legolas@woodland.com" and password "greenleaf1"
    When I register as "legolas" with email "other@woodland.com" and password "otherpass"
    Then I should get a conflict error

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