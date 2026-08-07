Feature: Confirming an email address
  As someone who has just signed up
  I want to prove the address I gave is mine
  So that my account can safely be linked to a provider sign-in later

  Scenario: Registering sends me a link
    When I register as "eowyn" with email "eowyn@rohan.com" and password "shieldmaiden1"
    Then I should receive an email at "eowyn@rohan.com"
    And it should contain a verification link

  Scenario: Following the link confirms my address
    Given I register as "faramir" with email "faramir@gondor.com" and password "ithilien1234"
    When I follow the verification link
    Then my address should be confirmed

  Scenario: A link only works once
    Given I register as "imrahil" with email "imrahil@dolamroth.com" and password "swanknight1"
    And I follow the verification link
    When I follow the verification link again
    Then I should be told the link is no longer valid

  Scenario: A link nobody issued is refused
    When I follow a verification link I made up
    Then I should be told the link is no longer valid

  Scenario: I can use the app before confirming
    Given I register as "bergil" with email "bergil@gondor.com" and password "youngguard12"
    When I ask who I am
    Then I should be told my own username

  Scenario: I can ask for another link
    Given I register as "ioreth" with email "ioreth@gondor.com" and password "houseshealing"
    And enough time has passed to ask again
    When I ask for another verification link
    Then I should receive a second email at "ioreth@gondor.com"

  Scenario: Asking again too soon is refused
    Given I register as "damrod" with email "damrod@gondor.com" and password "rangerofsouth"
    When I ask for another verification link
    Then I should be told to wait

  Scenario: Asking too many times in one session is refused
    Given I register as "anborn" with email "anborn@gondor.com" and password "rangerofnorth"
    When I ask for another verification link 3 times
    And I ask for another verification link
    Then I should be told to wait

  Scenario: Asking for another link without a session cookie is refused
    Given I register as "hirgon" with email "hirgon@gondor.com" and password "erranderrand"
    And my browser loses its refresh cookie
    When I ask for another verification link
    Then I should be told to sign in again

  Scenario: Asking for another link with a cookie from no session is refused
    Given I register as "golasgil" with email "golasgil@lamedon.com" and password "hillmenlord1"
    When I ask for another verification link with a made-up cookie
    Then I should be told to sign in again
