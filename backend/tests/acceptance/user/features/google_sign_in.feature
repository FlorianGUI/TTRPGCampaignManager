Feature: Signing in with a Google account
  As someone who would rather not keep another password
  I want to sign in with the Google account I already have
  So that getting into my campaigns is one click

  Scenario: Signing in with Google for the first time gives me an account
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Google
    Then I should be signed in
    And my account should be named "aragorn-elessar"
    And my address should already be confirmed

  Scenario: Coming back gives me the same account
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Google
    When I sign in with Google again
    Then I should be signed in
    And it should be the same account as before

  Scenario: Changing my Google address still reaches my account
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Google
    When Google starts using the address "strider@rangers.com" for me
    And I sign in with Google again
    Then it should be the same account as before

  Scenario: The session behaves like any other
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Google
    When I refresh my session
    Then I should be able to ask who I am

  Scenario: A password login against a Google-only account fails cleanly
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Google
    When I log in as "aragorn-elessar" with password "strider123"
    Then I should get an unauthorized error

  Scenario: Nothing secret travels in the URL I land on
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Google
    Then the page I land on should carry no token

  Scenario: Google and Discord reach one account
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Discord
    And Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Google
    Then I should be signed in
    And it should be the same account as before

  Scenario: Google vouching for an address I have confirmed links the two
    Given I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    And I confirm my address
    And Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Google
    Then I should be signed in
    And my account should be named "aragorn"

  Scenario: Google cannot claim an address the account never confirmed
    Given I register as "aragorn" with email "aragorn@gondor.com" and password "strider123"
    And Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I sign in with Google
    Then I should be sent back with the error "email-in-use"
    And I should not be signed in

  Scenario: An address Google has not confirmed is refused
    Given Google knows me as "Aragorn Elessar" with the unconfirmed address "aragorn@gondor.com"
    When I sign in with Google
    Then I should be sent back with the error "unverified-email"
    And I should not be signed in

  Scenario: An id_token that does not verify brings me back with nothing
    Given Google answers with an id_token that does not verify
    When I sign in with Google
    Then I should be sent back with the error "provider-unavailable"
    And the page should know it was "google"
    And I should not be signed in

  Scenario: Changing my mind at Google brings me back with nothing
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    When I refuse to authorise the app at Google
    Then I should be sent back with the error "cancelled"
    And I should not be signed in

  Scenario: A Google callback with the wrong state is rejected
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I have started signing in with Google
    When the Google callback comes back with a state I did not send
    Then the callback should be rejected
    And I should not be signed in

  Scenario: A finished Google sign-in cannot be replayed
    Given Google knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I sign in with Google
    When the Google callback comes back a second time
    Then the callback should be rejected

  Scenario: A sign-in started at Discord cannot be finished at Google's callback
    Given Discord knows me as "Aragorn Elessar" with the confirmed address "aragorn@gondor.com"
    And I have started signing in with Discord
    When that sign-in comes back to the Google callback instead
    Then the callback should be rejected
    And I should not be signed in
