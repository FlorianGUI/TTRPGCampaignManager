class NotAvailable(Exception):
    """What was asked for is not there, or is not the caller's to see.

    Deliberately one exception for both. The whole point of the 404-not-403 decision in
    #12 is that a caller cannot tell an id that was never used from one that belongs to
    someone else, and two exception types would be two ways to answer differently by
    accident. Contexts subclass this only to change the wording.

    No imports on purpose: the domain raises these, so this file must stay as free of
    frameworks as the entities that use it.
    """

    detail = "Not found"
