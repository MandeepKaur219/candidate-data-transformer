"""Phone normalization.

Normalizes phone numbers to E.164 format (e.g. "+14155552671"), per the
default output schema's "E.164 format" note. Uses Google's `phonenumbers`
library rather than regex digit-stripping, since correctly distinguishing
a valid number from noise (and handling international formats) is exactly
the kind of problem that library already solves well.
"""

from typing import Optional

import phonenumbers

# Sample inputs in this assignment are unlikely to include country codes
# (recruiter CSVs / notes typically write local numbers). A default region
# is required by the `phonenumbers` library to parse such numbers; "US" is
# used as a documented assumption, not a hidden hardcode -- it is the one
# region-dependent default in normalization and is called out in the
# README/DESIGN docs as a noted assumption.
_DEFAULT_REGION = "US"


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """
    Returns the E.164-formatted phone number, or None if `raw` is missing
    or cannot be parsed into a valid number.
    """
    if not raw or not raw.strip():
        return None
    try:
        parsed = phonenumbers.parse(raw.strip(), _DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)