"""
NAP normalizers for phone numbers, addresses, and business names.
International-aware phone normalization (no country bias).
Component-based address parsing for structured comparison.
Conservative business name cleaning.
"""

import re
from typing import Optional
from nap_checker.models import AddressComponents


# ─── Phone Normalization ───────────────────────────────────────────────

def normalize_phone(raw: str, country_hint: str = "") -> str:
    """
    Normalize a phone number to a pure digit string.

    Rules:
    1. Strip all non-digit characters except leading +
    2. If starts with +, strip the + → digits with country code
    3. If starts with 00, strip leading 00 → international dialing prefix
    4. Do NOT blindly prepend any country code to bare local numbers
    5. If country_hint is provided, apply appropriate country dialing code to local numbers

    Examples:
        "+91 98765 43210"   → "919876543210"
        "+919876543210"     → "919876543210"
        "+1 (212) 555-1234" → "12125551234"
        "+44 20 1234 5678"  → "442012345678"
        "98765-43210"       → "9876543210" (no country prepended without context)
        "(212) 555-1234"    → "2125551234" (no +1 prepended without context)
    """
    if not raw or not raw.strip():
        return ""

    cleaned = raw.strip()

    # Detect leading + before stripping
    has_plus = cleaned.startswith("+")

    # Strip everything except digits
    digits = re.sub(r"[^\d]", "", cleaned)

    if not digits:
        return ""

    # If had a leading +, the digits include the country code already
    if has_plus:
        return digits

    # If starts with 00 (international dialing prefix), strip it
    if digits.startswith("00") and len(digits) > 4:
        return digits[2:]

    # Apply country hint for local numbers
    if country_hint:
        hint = country_hint.strip().upper()
        code = _COUNTRY_CODES.get(hint, "")
        if code and not digits.startswith(code):
            # Strip leading 0 for local numbers (common in India, UK, etc.)
            if digits.startswith("0"):
                digits = digits[1:]
            return code + digits

    # No country context — return digits as-is (conservative)
    # Strip leading 0 only if it looks like a trunk prefix (not part of the number)
    if digits.startswith("0") and len(digits) > 10:
        digits = digits[1:]

    return digits


# Common country dialing codes
_COUNTRY_CODES = {
    "IN": "91",
    "INDIA": "91",
    "US": "1",
    "USA": "1",
    "UNITED STATES": "1",
    "CA": "1",
    "CANADA": "1",
    "GB": "44",
    "UK": "44",
    "UNITED KINGDOM": "44",
    "AU": "61",
    "AUSTRALIA": "61",
    "DE": "49",
    "GERMANY": "49",
    "FR": "33",
    "FRANCE": "33",
    "JP": "81",
    "JAPAN": "81",
    "SG": "65",
    "SINGAPORE": "65",
    "AE": "971",
    "UAE": "971",
}


# ─── Address Normalization ─────────────────────────────────────────────

# Common abbreviation expansions (word-boundary-aware).
# We match the abbreviation with an optional trailing dot, consuming
# it when present.  The lookbehind (?<=\b) ensures a word start, and
# the lookahead (?=[\s,;.\-]|$) ensures we don't match in the middle
# of a word.
_ADDRESS_ABBREVIATIONS = [
    (r"\bst\.(?=[\s,;)\-]|$)", "street"),
    (r"\bst\b(?!\.)", "street"),
    (r"\brd\.(?=[\s,;)\-]|$)", "road"),
    (r"\brd\b(?!\.)", "road"),
    (r"\bave\.(?=[\s,;)\-]|$)", "avenue"),
    (r"\bave\b(?!\.)", "avenue"),
    (r"\bapt\.(?=[\s,;)\-]|$)", "apartment"),
    (r"\bapt\b(?!\.)", "apartment"),
    (r"\bblvd\.(?=[\s,;)\-]|$)", "boulevard"),
    (r"\bblvd\b(?!\.)", "boulevard"),
    (r"\bhwy\.(?=[\s,;)\-]|$)", "highway"),
    (r"\bhwy\b(?!\.)", "highway"),
    (r"\bdr\.(?=[\s,;)\-]|$)", "drive"),
    (r"\bdr\b(?!\.)", "drive"),
    (r"\bste\.(?=[\s,;)\-]|$)", "suite"),
    (r"\bste\b(?!\.)", "suite"),
    (r"\bbldg\.(?=[\s,;)\-]|$)", "building"),
    (r"\bbldg\b(?!\.)", "building"),
    (r"\bfl\.(?=[\s,;)\-]|$)", "floor"),
    (r"\bfl\b(?!\.)", "floor"),
    (r"\bno\.(?=[\s,;)\-]|$)", "number"),
    (r"\bno\b(?!\.)", "number"),
    (r"\bpvt\.(?=[\s,;)\-]|$)", "private"),
    (r"\bpvt\b(?!\.)", "private"),
    (r"\blt\.(?=[\s,;)\-]|$)", "limited"),
    (r"\blt\b(?!\.)", "limited"),
    (r"\bgrd\.(?=[\s,;)\-]|$)", "ground"),
    (r"\bgrd\b(?!\.)", "ground"),
    (r"\bnr\.(?=[\s,;)\-]|$)", "near"),
    (r"\bnr\b(?!\.)", "near"),
    (r"\bopp\.(?=[\s,;)\-]|$)", "opposite"),
    (r"\bopp\b(?!\.)", "opposite"),
    (r"\bdist\.(?=[\s,;)\-]|$)", "district"),
    (r"\bdist\b(?!\.)", "district"),
    (r"\bextn\.(?=[\s,;)\-]|$)", "extension"),
    (r"\bextn\b(?!\.)", "extension"),
    (r"\bext\.(?=[\s,;)\-]|$)", "extension"),
    (r"\bext\b(?!\.)", "extension"),
]


def normalize_address(raw: str) -> str:
    """
    Normalize an address string for comparison:
    - Lowercase
    - Collapse whitespace
    - Expand common abbreviations
    - Strip trailing punctuation
    """
    if not raw or not raw.strip():
        return ""

    text = raw.strip().lower()

    # Expand abbreviations
    for pattern, replacement in _ADDRESS_ABBREVIATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Normalize whitespace and punctuation
    text = re.sub(r"[,;]+", ", ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip().rstrip(".,;:")

    return text


def parse_address_components(raw: str) -> AddressComponents:
    """
    Parse an address string into structural components for comparison.
    Extracts postal code, and attempts to identify city/region/street.
    """
    if not raw or not raw.strip():
        return AddressComponents()

    normalized = normalize_address(raw)

    # Extract postal/PIN/ZIP code
    postal_code = ""
    # Indian PIN: 6 digits, US ZIP: 5 digits or 5+4
    pin_match = re.search(r"\b(\d{6})\b", normalized)
    if pin_match:
        postal_code = pin_match.group(1)
    else:
        zip_match = re.search(r"\b(\d{5}(?:-\d{4})?)\b", normalized)
        if zip_match:
            postal_code = zip_match.group(1)

    # Try to split address by commas for component extraction
    parts = [p.strip() for p in normalized.split(",") if p.strip()]

    street = ""
    locality = ""
    region = ""
    country = ""

    if len(parts) >= 4:
        # Likely: street, city, state, postal/country
        street = parts[0]
        locality = parts[1]
        region = parts[2]
        # Last part might be postal code, country, or both
        remaining = parts[3:]
        for part in remaining:
            clean = re.sub(r"\d+", "", part).strip()
            if clean and not postal_code:
                country = clean
            elif clean:
                country = clean
    elif len(parts) == 3:
        street = parts[0]
        locality = parts[1]
        # Third could be state, postal, or state+postal
        third = parts[2]
        third_no_digits = re.sub(r"\d+", "", third).strip()
        if third_no_digits:
            region = third_no_digits
    elif len(parts) == 2:
        street = parts[0]
        locality = parts[1]
    elif len(parts) == 1:
        street = parts[0]

    # Clean postal code from other fields
    if postal_code:
        for fld in [street, locality, region, country]:
            if postal_code in fld:
                # Already extracted
                pass

    return AddressComponents(
        street=street.strip(),
        locality=locality.strip(),
        region=region.strip(),
        postal_code=postal_code,
        country=country.strip(),
        raw_normalized=normalized,
    )


# ─── Name Normalization ───────────────────────────────────────────────

_LEGAL_SUFFIXES = [
    r"\bprivate\s+limited\b",
    r"\bpvt\.?\s*ltd\.?\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\bllc\.?\b",
    r"\bllp\.?\b",
    r"\binc\.?\b",
    r"\bincorporated\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bco\.?\b",
    r"\b&\s*co\.?\b",
    r"\band\s+co\.?\b",
    r"\bplc\.?\b",
    r"\bgmbh\.?\b",
    r"\bpte\.?\s*ltd\.?\b",
]


def normalize_name(raw: str) -> str:
    """
    Normalize a business name for comparison:
    - Lowercase
    - Strip common legal suffixes (LLC, Inc., Pvt. Ltd., etc.)
    - Collapse whitespace
    - Strip leading/trailing punctuation
    """
    if not raw or not raw.strip():
        return ""

    text = raw.strip().lower()

    # Strip legal suffixes
    for pattern in _LEGAL_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing punctuation
    text = text.strip().strip(".,;:-|/\\()[]{}\"'")
    text = text.strip()

    return text


def extract_title_brand(title: str) -> str:
    """
    Extract the brand/business-name segment from a page title.
    Takes the LAST segment after | or - separators, which is typically the brand.

    Example:
        "Best Dental Clinic in Hyderabad | ABC Dental" → "ABC Dental"
        "About Us - ABC Dental" → "ABC Dental"
        "ABC Dental" → "ABC Dental"
    """
    if not title or not title.strip():
        return ""

    title = title.strip()

    # Try splitting by | first, then by -
    for separator in ["|", " - ", " – ", " — "]:
        if separator in title:
            parts = [p.strip() for p in title.split(separator) if p.strip()]
            if len(parts) >= 2:
                # Return the last segment (typically the brand)
                return parts[-1]

    # No separator found — return as-is but only if it's reasonably short (< 60 chars)
    if len(title) < 60:
        return title

    return ""
