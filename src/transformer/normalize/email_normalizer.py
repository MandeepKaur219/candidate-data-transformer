"""Email normalization.

Normalizes an email to a consistent, validated form: lowercase, trimmed,
with the domain syntactically checked. Uses `email_validator` rather than
a hand-rolled regex, per the "use proper libraries whenever appropriate"
requirement -- email syntax (especially the local part and IDN domains)
has enough edge cases that reinventing it is a liability.
"""

from typing import Optional

from email_validator import EmailNotValidError, validate_email


def normalize_email(raw: Optional[str]) -> Optional[str]:
    """
    Returns a normalized, lowercase email string, or None if `raw` is
    missing or not a syntactically valid email.

    Deliberately does NOT perform DNS/deliverability checks (check_deliverability
    is left off) -- this pipeline normalizes structure, it does not verify
    that a mailbox exists, which would make the pipeline non-deterministic
    and network-dependent.
    """
    if not raw or not raw.strip():
        return None
    try:
        result = validate_email(raw.strip(), check_deliverability=False)
    except EmailNotValidError:
        return None
    return result.normalized.lower()