# System Design

## Overview

The Multi-Source Candidate Data Transformer is an ETL pipeline that combines candidate information from multiple structured and unstructured data sources into a single canonical profile.

The system performs extraction, parsing, normalization, deduplication, conflict resolution, provenance tracking, confidence scoring, validation, and JSON generation while remaining modular and configurable.

---

# Architecture

```
                 Input Sources
      ┌─────────┬─────────┬─────────┬─────────┐
      │   CSV   │  JSON   │   PDF   │  Notes  │
      └────┬────┴────┬────┴────┬────┴────┬────┘
           │         │         │         │
           ▼         ▼         ▼         ▼
                 Extractors
                      │
                      ▼
                  Parsers
                      │
                      ▼
                Field Mapper
                      │
                      ▼
                 Normalizers
                      │
                      ▼
              Candidate Builder
                      │
                      ▼
             Matcher & Merger
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 Confidence Scorer          Provenance Tracker
        │                           │
        └─────────────┬─────────────┘
                      ▼
                  Projector
                      │
                      ▼
                  Validator
                      │
                      ▼
                 JSON Writer
```

---

# Pipeline Workflow

The pipeline processes candidate information in ten sequential stages.

| Stage | Description |
|--------|-------------|
| Extract | Reads data from CSV, JSON, PDF, and TXT files |
| Parse | Converts raw content into structured field values |
| Map | Maps source-specific fields to canonical fields |
| Normalize | Standardizes emails, phones, dates, skills, and text |
| Merge | Identifies duplicate candidates and merges records |
| Confidence | Calculates an overall confidence score |
| Provenance | Tracks the origin of every extracted field |
| Project | Generates output according to configuration |
| Validate | Validates the projected output schema |
| Write | Writes JSON output to disk |

---

# Core Components

## Extract Layer

Responsible for reading input files.

Supported sources:

- CSV
- JSON
- PDF
- Text files

---

## Parse Layer

Converts extracted content into structured `FieldValue` objects while preserving metadata.

Each parser handles a specific source format independently.

---

## Field Mapping

Maps source-specific field names into a common canonical schema using `pipeline_config.json`.

This allows new sources to be added without modifying the pipeline logic.

---

## Normalization

Normalizes candidate information into consistent formats.

Examples include:

- Lowercase email addresses
- E.164 phone numbers
- Standardized dates
- Canonical skill names
- Clean text formatting

---

## Matching & Merging

Duplicate candidates are identified using the following priority:

1. Email
2. Phone
3. Full Name

When duplicate records are found:

- Scalar fields are resolved using configurable source priority.
- List fields are merged without duplicates.
- Provenance information is preserved.

---

# Canonical Data Model

Each extracted value is stored together with its metadata.

```
FieldValue
├── value
└── provenance
      ├── source
      ├── method
      └── confidence
```

Candidate records contain:

- Candidate ID
- Personal information
- Contact details
- Skills
- Experience
- Education
- Links
- Provenance
- Overall confidence score

---

# Confidence Scoring

Each canonical field contributes to an overall confidence score.

The score is computed using configurable field weights.

Missing fields contribute lower confidence, while high-quality data from reliable sources increases the final score.

---

# Configuration

The pipeline behavior is controlled through configuration files.

| File | Purpose |
|------|---------|
| pipeline_config.json | Field mapping and source priority |
| output_config.json | Output schema and formatting |
| skill_aliases.json | Skill normalization aliases |

No code changes are required to customize these behaviors.

---

# Project Structure

```
src/
│
├── confidence/
├── extract/
├── mapping/
├── merge/
├── models/
├── normalize/
├── parse/
├── projection/
├── provenance/
├── validation/
├── writer/
└── pipeline.py
```

---

# Scalability

The architecture is modular and designed for future extension.

Possible enhancements include:

- Parallel extraction
- Streaming processing
- Incremental candidate updates
- OCR support for scanned PDFs
- Additional data sources
- Distributed processing

---

# Future Improvements

- Support additional ATS providers
- GitHub profile integration
- LinkedIn integration
- Improved entity matching
- Configurable confidence profiles
- Streaming JSON output
- Schema validation for configuration files