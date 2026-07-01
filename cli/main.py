#!/usr/bin/env python3
"""
CLI entrypoint for the Multi-Source Candidate Data Transformer.

A thin input/output surface only, per the assignment's "lower priority"
note on the UI/CLI -- all engine logic lives in transformer.pipeline and
the stage modules it orchestrates. This file's only job is: parse
arguments, load JSON configs from disk, hand paths to the Pipeline, and
report what was written.

Usage:
    python cli/main.py \\
        --csv data/samples/recruiter_export.csv \\
        --json data/samples/ats_blob.json \\
        --pdf data/samples/resume_john_doe.pdf \\
        --notes data/samples/recruiter_notes.txt \\
        --output output/profiles_default.json \\
        --output-config config/output_config.json \\
        --custom-output output/profiles_custom.json
"""

import argparse
import json
import os
import sys

# Allow running as `python cli/main.py` without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from transformer.pipeline import Pipeline  # noqa: E402

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)


def _default_path(*parts: str) -> str:
    return os.path.join(_PROJECT_ROOT, *parts)


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Multi-Source Candidate Data Transformer (Eightfold assignment)."
    )
    parser.add_argument("--csv", help="Path to recruiter CSV export.")
    parser.add_argument("--json", help="Path to ATS JSON blob.")
    parser.add_argument("--pdf", nargs="*", default=[], help="Path(s) to resume PDF(s).")
    parser.add_argument(
        "--notes", nargs="*", default=[], help="Path(s) to recruiter notes .txt file(s)."
    )
    parser.add_argument(
        "--pipeline-config",
        default=_default_path("config", "pipeline_config.json"),
        help="Path to pipeline_config.json (source priority + field maps).",
    )
    parser.add_argument(
        "--skill-aliases",
        default=_default_path("config", "skill_aliases.json"),
        help="Path to skill_aliases.json.",
    )
    parser.add_argument(
        "--output",
        default=_default_path("output", "profiles_default.json"),
        help="Where to write the default-schema output JSON.",
    )
    parser.add_argument(
        "--output-config",
        help="Optional path to a custom output_config.json (configurable projection).",
    )
    parser.add_argument(
        "--custom-output",
        default=_default_path("output", "profiles_custom.json"),
        help="Where to write the custom-config output JSON (only used with --output-config).",
    )
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    inputs = {}
    if args.csv:
        inputs["recruiter_csv"] = args.csv
    if args.json:
        inputs["ats_json"] = args.json
    if args.pdf:
        inputs["resume_pdf"] = args.pdf
    if args.notes:
        inputs["recruiter_notes"] = args.notes

    if not inputs:
        print("No input sources given. Provide at least one of --csv/--json/--pdf/--notes.")
        return 1

    pipeline_config = _load_json(args.pipeline_config)
    skill_aliases = _load_json(args.skill_aliases)
    pipeline = Pipeline(pipeline_config, skill_aliases)

    default_profiles = pipeline.run(inputs, output_config=None, output_path=args.output)
    print(f"Default schema: wrote {len(default_profiles)} candidate(s) to {args.output}")

    if args.output_config:
        output_config = _load_json(args.output_config)
        custom_profiles = pipeline.run(
            inputs, output_config=output_config, output_path=args.custom_output
        )
        print(
            f"Custom config:  wrote {len(custom_profiles)} candidate(s) to {args.custom_output}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())