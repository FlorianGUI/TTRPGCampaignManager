Feature: Signing in with a Discord account
  As a game master whose table already organises on Discord
  I want to sign in with the account my players know me by
  So that I do not need another password to run a campaign

  Scenario: Signing in with Discord for the first time gives me an account
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Discord
    Then I should be signed in
    And my account should be named "aragorn-elessar"
    And my address should already be confirmed

  Scenario: My account has no password to guess
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When I log in as "aragorn-elessar" with password "strider123"
    Then I should get an unauthorized error

  Scenario: Coming back gives me the same account
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When I sign in with Discord again
    Then I should be signed in
    And it should be the same account as before

  Scenario: Changing my Discord handle still reaches my account
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When Discord starts calling me "Strider"
    And I sign in with Discord again
    Then it should be the same account as before

  Scenario: Changing my Discord address still reaches my account
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When Discord starts using the address "strider@rangers.com" for me
    And I sign in with Discord again
    Then it should be the same account as before

  Scenario: A different Discord account is a different account here
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When someone else signs in with their own Discord account
    Then it should be a different account

  Scenario: The session behaves like any other
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When I refresh my session
    Then I should be able to ask who I am

  Scenario: I can sign out again
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When I log out
    And I refresh my session
    Then I should get an unauthorized error

  Scenario: Nothing secret travels in the URL I land on
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Discord
    Then the page I land on should carry no token

  Scenario: Discord vouching for an address I have confirmed links the two
    Given I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    And I confirm my address
    And Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Discord
    Then I should be signed in
    And my account should be named "aragorn"

  Scenario: My password still works after linking
    Given I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    And I confirm my address
    And Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When I log in as "aragorn" with password "strider123"
    Then I should be able to ask who I am

  Scenario: Discord cannot claim an address the account never confirmed
    Given I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    And Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Discord
    Then I should be sent back with the error "email-in-use"
    And I should not be signed in

  Scenario: An address Discord has not confirmed is refused
    Given Discord knows me as "Aragorn Elessar" with the unconfirmed address "aragorn@gondor.com"
    When I sign in with Discord
    Then I should be sent back with the error "unverified-email"
    And I should not be signed in

  Scenario: An address Discord has not confirmed cannot reach an existing account
    Given I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    And I confirm my address
    And Discord knows me as "Aragorn Elessar" with the unconfirmed address "aragorn@gondor.com"
    When I sign in with Discord
    Then I should be sent back with the error "unverified-email"
    And I should not be signed in

  Scenario: A Discord account with no address at all is refused
    Given Discord knows me as "Aragorn Elessar" with no address
    When I sign in with Discord
    Then I should be sent back with the error "no-email"
    And I should not be signed in

  Scenario: Changing my mind at Discord brings me back with nothing
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I refuse to authorise the app at Discord
    Then I should be sent back with the error "cancelled"
    And I should not be signed in

  Scenario: Discord being unreachable brings me back with nothing
    Given Discord is unreachable
    When I sign in with Discord
    Then I should be sent back with the error "provider-unavailable"
    And the page should know it was "discord"
    And I should not be signed in

  Scenario: A callback nobody started is rejected
    When a callback arrives with no state
    Then the callback should be rejected
    And I should not be signed in

  Scenario: A callback with the wrong state is rejected
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I have started signing in with Discord
    When the callback comes back with a state I did not send
    Then the callback should be rejected
    And I should not be signed in

  Scenario: A callback for a sign-in this browser never started is rejected
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I have started signing in with Discord
    And my browser loses its sign-in cookie
    When the callback comes back
    Then the callback should be rejected
    And I should not be signed in

  Scenario: A finished sign-in cannot be replayed
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    When the callback comes back a second time
    Then the callback should be rejected
