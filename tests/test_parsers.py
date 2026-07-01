from transformer.parse.csv_parser import CsvParser
from transformer.parse.json_parser import JsonParser
from transformer.parse.notes_parser import NotesParser
from transformer.parse.resume_parser import ResumeParser


def test_csv_parser_extracts_rows_with_high_confidence():
    raw = [{"name": "Jane Doe", "email": "jane@example.com", "phone": ""}]
    records = CsvParser().parse(raw)
    assert len(records) == 1
    assert records[0]["name"].value == "Jane Doe"
    assert records[0]["name"].method == "direct_field"
    assert records[0]["name"].confidence >= 0.9
    # Blank phone column must not produce a key at all.
    assert "phone" not in records[0]


def test_csv_parser_skips_fully_blank_rows():
    raw = [{"name": "", "email": "", "phone": ""}]
    assert CsvParser().parse(raw) == []


def test_json_parser_flattens_nested_dicts():
    raw = [{"candidate": {"full_name": "Jane Doe"}, "contact": {"email": "jane@example.com"}}]
    records = JsonParser().parse(raw)
    assert len(records) == 1
    assert records[0]["candidate.full_name"].value == "Jane Doe"
    assert records[0]["contact.email"].value == "jane@example.com"


def test_json_parser_keeps_lists_intact_not_flattened():
    raw = [{"skills": ["Python", "Go"]}]
    records = JsonParser().parse(raw)
    assert records[0]["skills"].value == ["Python", "Go"]


def test_json_parser_drops_empty_and_none_values():
    raw = [{"name": "Jane", "middle_name": None, "nickname": ""}]
    records = JsonParser().parse(raw)
    assert "middle_name" not in records[0]
    assert "nickname" not in records[0]


def test_notes_parser_extracts_email_phone_name_and_company():
    text = (
        "Candidate: Jane Doe\n"
        "Spoke with Jane Doe (jane@example.com, 415-555-0182) about the role. "
        "Currently at Globex working on payments. ~6 years experience."
    )
    records = NotesParser().parse(text)
    assert len(records) == 1
    record = records[0]
    assert record["email"].value == "jane@example.com"
    assert "555-0182" in record["phone"].value
    assert record["full_name"].value == "Jane Doe"
    assert record["current_company"].value == "Globex"
    assert record["years_experience"].value == "6"


def test_notes_parser_returns_empty_for_blank_input():
    assert NotesParser().parse("") == []
    assert NotesParser().parse(None) == []


def test_resume_parser_extracts_name_and_sections():
    text = (
        "Jane Doe\n"
        "jane@example.com | 415-555-0182\n"
        "Skills\n"
        "Python, Go, Kubernetes\n"
        "Experience\n"
        "Globex Inc - Senior Engineer\n"
        "Education\n"
        "UC Berkeley - B.S. CS, 2017\n"
    )
    records = ResumeParser().parse(text)
    assert len(records) == 1
    record = records[0]
    assert record["full_name"].value == "Jane Doe"
    assert record["email"].value == "jane@example.com"
    assert "Python" in record["skills"].value
    assert "Globex Inc - Senior Engineer" in record["experience_text"].value
    assert "UC Berkeley" in record["education_text"].value


def test_resume_parser_handles_empty_text():
    assert ResumeParser().parse("") == []