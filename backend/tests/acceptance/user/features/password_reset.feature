Feature: Resetting a forgotten password
  As someone who cannot remember their password
  I want to set a new one from my inbox
  So that I am not locked out of my campaigns

  Scenario: Asking with my username sends me a link
    Given I register as "hurin" with email "hurin@dorlomin.com" and password "steadfast123"
    When I ask to reset the password for "hurin"
    Then I should receive an email at "hurin@dorlomin.com"
    And it should contain a reset link

  Scenario: Asking with my email address works just as well
    Given I register as "huor" with email "huor@dorlomin.com" and password "brotherof123"
    When I ask to reset the password for "huor@dorlomin.com"
    Then I should receive an email at "huor@dorlomin.com"

  Scenario: Asking about an account that does not exist tells me nothing
    When I ask to reset the password for "no-such-person"
    Then I should be told nothing either way
    And no email should be sent

  Scenario: An unknown account answers exactly as a known one does
    Given I register as "morwen" with email "morwen@dorlomin.com" and password "eledhwen123"
    When I ask to reset the password for "morwen"
    And I ask to reset the password for "no-such-person"
    Then both answers should be identical

  Scenario: Following the link lets me choose a new password
    Given I register as "turin" with email "turin@dorlomin.com" and password "oldpassword1"
    And I ask to reset the password for "turin"
    When I follow the reset link and choose "a-brand-new-password"
    Then I should be able to log in as "turin" with "a-brand-new-password"

  Scenario: The old password stops working
    Given I register as "nienor" with email "nienor@dorlomin.com" and password "oldpassword1"
    And I ask to reset the password for "nienor"
    When I follow the reset link and choose "a-brand-new-password"
    Then I should not be able to log in as "nienor" with "oldpassword1"

  Scenario: Resetting ends the session I already had
    Given I register as "glaurung" with email "glaurung@angband.com" and password "oldpassword1"
    And I ask to reset the password for "glaurung"
    When I follow the reset link and choose "a-brand-new-password"
    And I refresh my session
    Then I should get an unauthorized error

  Scenario: A reset link only works once
    Given I register as "brandir" with email "brandir@brethil.com" and password "oldpassword1"
    And I ask to reset the password for "brandir"
    And I follow the reset link and choose "a-brand-new-password"
    When I follow the reset link again and choose "another-password"
    Then I should be told the reset link is no longer valid

  Scenario: A link nobody issued is refused
    When I follow a reset link I made up
    Then I should be told the reset link is no longer valid
