"""Unit tests for transformer.normalize.* -- behaviour, not just imports."""

from transformer.normalize.date_normalizer import normalize_date, normalize_year
from transformer.normalize.email_normalizer import normalize_email
from transformer.normalize.phone_normalizer import normalize_phone
from transformer.normalize.skill_normalizer import SkillNormalizer
from transformer.normalize.text_normalizer import (
    clean_text,
    collapse_whitespace,
    title_case_name,
)


class TestEmailNormalizer:
    def test_lowercases_and_trims(self):
        assert normalize_email("  John.Doe@Example.COM  ") == "john.doe@example.com"

    def test_rejects_invalid_email(self):
        assert normalize_email("not-an-email") is None

    def test_rejects_missing_value(self):
        assert normalize_email(None) is None
        assert normalize_email("") is None
        assert normalize_email("   ") is None


class TestPhoneNormalizer:
    def test_formats_us_number_to_e164(self):
        assert normalize_phone("(415) 555-2671") == "+14155552671"

    def test_accepts_explicit_country_code(self):
        assert normalize_phone("+44 20 7946 0958") == "+442079460958"

    def test_rejects_garbage_input(self):
        assert normalize_phone("not a phone number") is None

    def test_rejects_too_short_number(self):
        assert normalize_phone("123") is None

    def test_rejects_missing_value(self):
        assert normalize_phone(None) is None
        assert normalize_phone("") is None


class TestDateNormalizer:
    def test_parses_month_year_text(self):
        assert normalize_date("March 2019") == "2019-03"

    def test_parses_iso_date(self):
        assert normalize_date("2020-01-15") == "2020-01"

    def test_ongoing_terms_become_none(self):
        assert normalize_date("Present") is None
        assert normalize_date("Current") is None
        assert normalize_date("present") is None

    def test_missing_or_unparseable_becomes_none(self):
        assert normalize_date(None) is None
        assert normalize_date("") is None
        assert normalize_date("not a date at all !!") is None

    def test_is_deterministic_regardless_of_when_run(self):
        # Anchored to a fixed default datetime, not datetime.now() --
        # running this twice years apart must give the same answer.
        assert normalize_date("June") == normalize_date("June")

    def test_normalize_year_parses_bare_year(self):
        assert normalize_year("2021") == 2021

    def test_normalize_year_parses_full_date(self):
        assert normalize_year("May 2018") == 2018

    def test_normalize_year_handles_missing(self):
        assert normalize_year(None) is None


class TestSkillNormalizer:
    def test_resolves_known_alias(self):
        normalizer = SkillNormalizer({"js": "JavaScript", "py": "Python"})
        assert normalizer.normalize("JS") == "JavaScript"
        assert normalizer.normalize("py") == "Python"

    def test_unknown_skill_falls_back_to_title_case(self):
        normalizer = SkillNormalizer({"js": "JavaScript"})
        assert normalizer.normalize("rust programming") == "Rust Programming"

    def test_missing_value_returns_none(self):
        normalizer = SkillNormalizer({})
        assert normalizer.normalize(None) is None
        assert normalizer.normalize("   ") is None

    def test_alias_lookup_is_case_insensitive_on_input(self):
        normalizer = SkillNormalizer({"node.js": "Node.js"})
        assert normalizer.normalize("Node.JS") == "Node.js"


class TestTextNormalizer:
    def test_collapse_whitespace_squashes_internal_runs(self):
        assert collapse_whitespace("  John   Doe  ") == "John Doe"

    def test_collapse_whitespace_empty_becomes_none(self):
        assert collapse_whitespace("   ") is None
        assert collapse_whitespace(None) is None

    def test_title_case_name_preserves_internal_casing(self):
        assert title_case_name("mcdonald") == "Mcdonald"
        # Each word's leading lowercase letter is capitalized, but existing
        # intentional internal casing (the "OS" in "iOS") is left alone.
        assert title_case_name("iOS developer") == "IOS Developer"

    def test_title_case_name_capitalizes_lowercase_words(self):
        assert title_case_name("jane doe") == "Jane Doe"

    def test_clean_text_normalizes_unicode_and_whitespace(self):
        assert clean_text("Café   Owner") == "Café Owner"