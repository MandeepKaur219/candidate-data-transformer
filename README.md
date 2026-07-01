# Multi-Source Candidate Data Transformer

A Python-based ETL pipeline that extracts candidate information from multiple structured and unstructured sources, merges duplicate records into a unified candidate profile, tracks field provenance, calculates confidence scores, and exports the final result as configurable JSON.

---

## Features

- Extracts candidate data from:
  - CSV
  - JSON
  - PDF resumes
  - Recruiter notes (.txt)

- Normalizes:
  - Emails
  - Phone numbers
  - Dates
  - Skills
  - Text formatting

- Deduplicates candidate records

- Merges information using configurable source priority

- Tracks provenance for every field

- Calculates overall confidence score

- Supports configurable output schema

- Includes automated unit tests

---

## Project Structure

```text
candidate-data-transformer/
│
├── cli/
├── config/
├── data/
├── output/
├── src/
├── tests/
├── DESIGN.md
├── README.md
└── requirements.txt
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/MandeepKaur219/candidate-data-transformer.git
cd candidate-data-transformer
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Project

Run the pipeline with all supported input sources:

```bash
python cli\main.py ^
  --csv data\samples\recruiter_export.csv ^
  --json data\samples\ats_blob.json ^
  --pdf data\samples\resume_jane_doe.pdf ^
  --notes data\samples\recruiter_notes.txt ^
  --output output\profiles_default.json ^
  --output-config config\output_config.json ^
  --custom-output output\profiles_custom.json
```

Or, as a single-line command:

```bash
python cli\main.py --csv data\samples\recruiter_export.csv --json data\samples\ats_blob.json --pdf data\samples\resume_jane_doe.pdf --notes data\samples\recruiter_notes.txt --output output\profiles_default.json --output-config config\output_config.json --custom-output output\profiles_custom.json
```

### Generated Outputs

After successful execution, the pipeline generates:

- `output/profiles_default.json` — Complete canonical candidate profiles.
- `output/profiles_custom.json` — Profiles formatted according to `config/output_config.json`.

---

## Configuration

The project supports configuration through JSON files.

- `pipeline_config.json` – source priority and field mapping
- `output_config.json` – output field selection and formatting
- `skill_aliases.json` – skill normalization aliases

No code changes are required to modify these behaviors.

---

## Output

The generated JSON contains:

- Candidate ID
- Personal details
- Contact information
- Skills
- Experience
- Education
- Links
- Provenance
- Overall confidence score

Output files are written to the `output/` directory.

---

## Running Tests

Run all tests

```bash
pytest tests/ -v
```

Run a specific test file

```bash
pytest tests/test_merger.py -v
```

Generate coverage report

```bash
pytest --cov=src/transformer --cov-report=term-missing
```

---

## Future Improvements

- Support additional data sources
- Parallel processing for large datasets
- OCR support for scanned PDF resumes
- Streaming output for large candidate collections
- Additional configurable confidence strategies

---

## Technologies Used

- Python 3.10+
- pdfplumber
- pytest
- JSON
- CSV

---

## License

This project is intended for educational and learning purposes.