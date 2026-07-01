"""Unit tests for transformer.validation.validator -- behaviour, not just imports."""

from transformer.validation.validator import ValidationResult, Validator


class TestValidationResult:
    def test_is_valid_true_when_no_errors(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []

    def test_is_valid_false_when_errors_present(self):
        result = ValidationResult(is_valid=False, errors=["field X missing"])
        assert result.is_valid is False
        assert len(result.errors) == 1


class TestValidatorDefaultSchema:
    def test_valid_minimal_profile_passes(self):
        validator = Validator()
        profile = {
            "candidate_id": "cand_abc123",
            "full_name": "Jane Doe",
            "emails": ["jane@example.com"],
            "phones": ["+14155552671"],
        }
        result = validator.validate(profile, config=None)
        assert result.is_valid is True
        assert result.errors == []

    def test_missing_candidate_id_fails(self):
        validator = Validator()
        result = validator.validate({"full_name": "Jane Doe"}, config=None)
        assert result.is_valid is False
        assert any("candidate_id" in e for e in result.errors)

    def test_empty_candidate_id_fails(self):
        validator = Validator()
        result = validator.validate({"candidate_id": ""}, config=None)
        assert result.is_valid is False

    def test_emails_as_non_list_fails(self):
        validator = Validator()
        profile = {"candidate_id": "cand_1", "emails": "jane@example.com"}
        result = validator.validate(profile, config=None)
        assert result.is_valid is False
        assert any("emails" in e for e in result.errors)

    def test_phones_as_non_list_fails(self):
        validator = Validator()
        profile = {"candidate_id": "cand_1", "phones": "+14155552671"}
        result = validator.validate(profile, config=None)
        assert result.is_valid is False
        assert any("phones" in e for e in result.errors)

    def test_skill_without_name_field_fails(self):
        validator = Validator()
        profile = {
            "candidate_id": "cand_1",
            "skills": [{"confidence": 0.9}],
        }
        result = validator.validate(profile, config=None)
        assert result.is_valid is False
        assert any("skills[0]" in e for e in result.errors)

    def test_overall_confidence_outside_range_fails(self):
        validator = Validator()
        profile = {"candidate_id": "cand_1", "overall_confidence": 1.5}
        result = validator.validate(profile, config=None)
        assert result.is_valid is False
        assert any("overall_confidence" in e for e in result.errors)

    def test_overall_confidence_at_boundaries_passes(self):
        validator = Validator()
        for boundary in (0.0, 1.0):
            profile = {"candidate_id": "cand_1", "overall_confidence": boundary}
            result = validator.validate(profile, config=None)
            assert result.is_valid is True, f"boundary {boundary} should pass"


class TestValidatorCustomSchema:
    def _cfg(self, fields):
        return {"fields": fields}

    def test_required_field_present_passes(self):
        validator = Validator()
        cfg = self._cfg([{"path": "full_name", "type": "string", "required": True}])
        result = validator.validate({"full_name": "Jane Doe"}, config=cfg)
        assert result.is_valid is True

    def test_required_field_absent_fails(self):
        validator = Validator()
        cfg = self._cfg([{"path": "full_name", "type": "string", "required": True}])
        result = validator.validate({}, config=cfg)
        assert result.is_valid is False
        assert any("full_name" in e for e in result.errors)

    def test_optional_field_absent_passes(self):
        validator = Validator()
        cfg = self._cfg([{"path": "headline", "type": "string", "required": False}])
        result = validator.validate({}, config=cfg)
        assert result.is_valid is True

    def test_wrong_type_fails(self):
        validator = Validator()
        cfg = self._cfg([{"path": "years_experience", "type": "number"}])
        result = validator.validate({"years_experience": "six"}, config=cfg)
        assert result.is_valid is False
        assert any("years_experience" in e for e in result.errors)

    def test_null_value_passes_for_any_type(self):
        """None is a valid outcome of on_missing='null', not a type error."""
        validator = Validator()
        cfg = self._cfg([{"path": "headline", "type": "string"}])
        result = validator.validate({"headline": None}, config=cfg)
        assert result.is_valid is True

    def test_string_list_type_check(self):
        validator = Validator()
        cfg = self._cfg([{"path": "skill_names", "type": "string[]"}])
        good = validator.validate({"skill_names": ["Python", "Go"]}, config=cfg)
        bad = validator.validate({"skill_names": "Python"}, config=cfg)
        assert good.is_valid is True
        assert bad.is_valid is False

    def test_number_type_rejects_bool(self):
        """Booleans are a subtype of int in Python -- the validator must
        still reject them as not-a-number per the type spec."""
        validator = Validator()
        cfg = self._cfg([{"path": "years_experience", "type": "number"}])
        result = validator.validate({"years_experience": True}, config=cfg)
        assert result.is_valid is False

    def test_multiple_errors_all_reported(self):
        validator = Validator()
        cfg = self._cfg([
            {"path": "full_name", "type": "string", "required": True},
            {"path": "primary_email", "type": "string", "required": True},
        ])
        result = validator.validate({}, config=cfg)
        assert not result.is_valid
        assert len(result.errors) == 2