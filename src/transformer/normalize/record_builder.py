"""
Record builder.

This is where Mapping's output (canonical field name -> raw ParsedValues)
becomes the Normalize stage's output (a CandidateRecord of properly
normalized, provenance-wrapped FieldValues). It is the one place that
knows which normalizer applies to which canonical field -- every other
normalizer module stays generic and reusable, and every other stage
(merge, confidence, provenance) only ever sees fully-built CandidateRecords.

Per the "robust" constraint, a value that fails to normalize (e.g. an
unparseable email) is dropped rather than kept as garbage or invented;
the field simply ends up absent for that source, which the Merger and
Confidence stages already treat correctly as "unknown".
"""

from typing import Dict, List, Optional

from transformer.models.canonical import (
    CandidateRecord,
    EducationEntry,
    ExperienceEntry,
    FieldValue,
)
from transformer.models.provenance import Provenance
from transformer.normalize.date_normalizer import normalize_date, normalize_year
from transformer.normalize.email_normalizer import normalize_email
from transformer.normalize.phone_normalizer import normalize_phone
from transformer.normalize.skill_normalizer import SkillNormalizer
from transformer.normalize.text_normalizer import clean_text, title_case_name
from transformer.parse.base import ParsedValue

_SCALAR_TEXT_FIELDS = {
    "full_name": title_case_name,
    "headline": clean_text,
    "location_city": clean_text,
    "location_region": clean_text,
    "location_country": clean_text,
    "links_linkedin": clean_text,
    "links_github": clean_text,
    "links_portfolio": clean_text,
}


def _dict_get_first(item: dict, *keys: str) -> Optional[str]:
    for key in keys:
        value = item.get(key)
        if value:
            return str(value)
    return None


class RecordBuilder:
    """Builds one normalized, per-source CandidateRecord from mapped fields."""

    def __init__(self, skill_normalizer: SkillNormalizer):
        self._skill_normalizer = skill_normalizer

    def build(
        self, source_name: str, mapped: Dict[str, List[ParsedValue]]
    ) -> CandidateRecord:
        record = CandidateRecord(source=source_name)

        for field_name, parsed_values in mapped.items():
            if field_name in _SCALAR_TEXT_FIELDS:
                self._set_scalar_text(
                    record, field_name, parsed_values, source_name,
                    _SCALAR_TEXT_FIELDS[field_name],
                )
            elif field_name == "years_experience":
                self._set_years_experience(record, parsed_values, source_name)
            elif field_name == "emails":
                record.emails.extend(
                    self._build_list(parsed_values, source_name, "emails", normalize_email)
                )
            elif field_name == "phones":
                record.phones.extend(
                    self._build_list(parsed_values, source_name, "phones", normalize_phone)
                )
            elif field_name == "links_other":
                record.links_other.extend(
                    self._build_list(parsed_values, source_name, "links_other", clean_text)
                )
            elif field_name == "skills":
                record.skills.extend(self._build_skills(parsed_values, source_name))
            elif field_name == "experience":
                record.experience.extend(
                    self._build_experience_structured(parsed_values, source_name)
                )
            elif field_name == "experience_text":
                record.experience.extend(
                    self._build_experience_from_text(parsed_values, source_name)
                )
            elif field_name == "experience_company_hint":
                record.experience.extend(
                    self._build_experience_company_hint(parsed_values, source_name)
                )
            elif field_name == "education":
                record.education.extend(
                    self._build_education_structured(parsed_values, source_name)
                )
            # "education_text": free-text education sections are not
            # structured into discrete entries -- a noted, deliberate
            # descope (see DESIGN.md), so it is silently skipped here
            # rather than producing a half-populated EducationEntry.

        return record

    def _set_scalar_text(self, record, field_name, parsed_values, source_name, normalize_fn):
        if not parsed_values:
            return
        raw = parsed_values[0]
        normalized = normalize_fn(str(raw.value))
        if normalized is None:
            return
        setattr(
            record,
            field_name,
            FieldValue(
                value=normalized,
                provenance=Provenance(
                    field=field_name, source=source_name,
                    method=raw.method, confidence=raw.confidence,
                ),
            ),
        )

    def _set_years_experience(self, record, parsed_values, source_name):
        if not parsed_values:
            return
        raw = parsed_values[0]
        try:
            years = float(raw.value)
        except (TypeError, ValueError):
            return
        record.years_experience = FieldValue(
            value=years,
            provenance=Provenance(
                field="years_experience", source=source_name,
                method=raw.method, confidence=raw.confidence,
            ),
        )

    def _build_list(self, parsed_values, source_name, field_name, normalize_fn):
        results = []
        for raw in parsed_values:
            normalized = normalize_fn(str(raw.value))
            if normalized is None:
                continue
            results.append(
                FieldValue(
                    value=normalized,
                    provenance=Provenance(
                        field=field_name, source=source_name,
                        method=raw.method, confidence=raw.confidence,
                    ),
                )
            )
        return results

    def _build_skills(self, parsed_values, source_name):
        results = []
        for raw in parsed_values:
            items = raw.value if isinstance(raw.value, list) else [raw.value]
            for item in items:
                normalized = self._skill_normalizer.normalize(str(item))
                if normalized is None:
                    continue
                results.append(
                    FieldValue(
                        value=normalized,
                        provenance=Provenance(
                            field="skills", source=source_name,
                            method=raw.method, confidence=raw.confidence,
                        ),
                    )
                )
        return results

    def _build_experience_structured(self, parsed_values, source_name):
        results = []
        for raw in parsed_values:
            items = raw.value if isinstance(raw.value, list) else [raw.value]
            for item in items:
                if not isinstance(item, dict):
                    continue
                company = clean_text(_dict_get_first(item, "company", "employer"))
                title = clean_text(_dict_get_first(item, "title", "position", "role"))
                start_raw = _dict_get_first(item, "start", "start_date")
                end_raw = _dict_get_first(item, "end", "end_date")
                summary = clean_text(_dict_get_first(item, "summary", "description"))
                entry = ExperienceEntry(
                    company=company,
                    title=title,
                    start=normalize_date(start_raw) if start_raw else None,
                    end=normalize_date(end_raw) if end_raw else None,
                    summary=summary,
                )
                if any([entry.company, entry.title, entry.start, entry.end, entry.summary]):
                    results.append(
                        FieldValue(
                            value=entry,
                            provenance=Provenance(
                                field="experience", source=source_name,
                                method=raw.method, confidence=raw.confidence,
                            ),
                        )
                    )
        return results

    def _build_experience_from_text(self, parsed_values, source_name):
        results = []
        for raw in parsed_values:
            text = clean_text(str(raw.value))
            if not text:
                continue
            entry = ExperienceEntry(summary=text)
            results.append(
                FieldValue(
                    value=entry,
                    provenance=Provenance(
                        field="experience", source=source_name,
                        method=raw.method, confidence=raw.confidence,
                    ),
                )
            )
        return results

    def _build_experience_company_hint(self, parsed_values, source_name):
        results = []
        for raw in parsed_values:
            company = clean_text(str(raw.value))
            if not company:
                continue
            entry = ExperienceEntry(company=company)
            results.append(
                FieldValue(
                    value=entry,
                    provenance=Provenance(
                        field="experience", source=source_name,
                        method=raw.method, confidence=raw.confidence,
                    ),
                )
            )
        return results

    def _build_education_structured(self, parsed_values, source_name):
        results = []
        for raw in parsed_values:
            items = raw.value if isinstance(raw.value, list) else [raw.value]
            for item in items:
                if not isinstance(item, dict):
                    continue
                institution = clean_text(_dict_get_first(item, "institution", "school"))
                degree = clean_text(_dict_get_first(item, "degree"))
                field_of_study = clean_text(_dict_get_first(item, "field", "major"))
                end_year_raw = _dict_get_first(item, "end_year", "year", "graduation_year")
                entry = EducationEntry(
                    institution=institution,
                    degree=degree,
                    field=field_of_study,
                    end_year=normalize_year(end_year_raw) if end_year_raw else None,
                )
                if any([entry.institution, entry.degree, entry.field, entry.end_year]):
                    results.append(
                        FieldValue(
                            value=entry,
                            provenance=Provenance(
                                field="education", source=source_name,
                                method=raw.method, confidence=raw.confidence,
                            ),
                        )
                    )
        return results