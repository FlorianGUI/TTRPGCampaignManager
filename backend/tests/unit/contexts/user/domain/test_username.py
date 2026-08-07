from app.contexts.user.domain.username import MAX_LENGTH, derive, variant


class TestDerive:
    def test_lowercases_and_joins_words(self):
        assert derive("Aragorn Elessar") == "aragorn-elessar"

    def test_drops_characters_the_column_should_not_hold(self):
        assert derive("Ara🗡gorn!") == "ara-gorn"

    def test_collapses_runs_left_behind_by_dropping(self):
        """Otherwise "Aragorn   Elessar" becomes "aragorn---elessar", which is nobody's
        idea of their own name."""
        assert derive("Aragorn   Elessar") == "aragorn-elessar"

    def test_trims_separators_from_the_ends(self):
        assert derive("  !Aragorn!  ") == "aragorn"

    def test_never_returns_nothing(self):
        """A display name made entirely of characters we drop still has to produce an
        account. Failing here would mean a provider sign-in that cannot complete because
        of someone's choice of emoji."""
        assert derive("🗡🛡") == "adventurer"
        assert derive("") == "adventurer"

    def test_fits_the_column(self):
        assert len(derive("a" * 200)) == MAX_LENGTH


class TestVariant:
    def test_the_first_attempt_is_the_base_itself(self):
        assert variant("aragorn", 0) == "aragorn"

    def test_later_attempts_are_counted_not_random(self):
        """A person reads their own username; "aragorn-2" is explicable and
        "aragorn-f3a9" is not."""
        assert variant("aragorn", 1) == "aragorn-2"
        assert variant("aragorn", 2) == "aragorn-3"

    def test_a_suffixed_variant_still_fits_the_column(self):
        assert len(variant("a" * MAX_LENGTH, 9)) == MAX_LENGTH

    def test_truncates_the_base_rather_than_the_suffix(self):
        """Dropping digits instead would produce a name that collides again — the one
        thing this must not do."""
        assert variant("a" * MAX_LENGTH, 9).endswith("-10")
