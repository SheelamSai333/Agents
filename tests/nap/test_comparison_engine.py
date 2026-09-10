"""Tests for NAP comparison engine (O, Q, R + consistency/mismatch scenarios)."""

from nap_checker.models import NAPOccurrence
from nap_checker.comparison_engine import ComparisonEngine


def _occ(field, raw, normalized, url, source_type="json_ld", quality=1.0):
    return NAPOccurrence(
        field=field,
        raw_value=raw,
        normalized_value=normalized,
        source_url=url,
        source_type=source_type,
        source_quality=quality,
    )


# ─── Existing tests preserved ──────────────────────────────────────────

def test_same_name_is_consistent():
    engine = ComparisonEngine()
    occurrences = [
        _occ("name", "Acme Technologies", "acme technologies", "https://example.com/"),
        _occ("name", "Acme Technologies", "acme technologies", "https://example.com/contact"),
    ]
    report = engine.compare_field(occurrences, "name")
    assert report.verdict == "consistent"


def test_phone_formatting_is_not_mismatch():
    engine = ComparisonEngine()
    occurrences = [
        _occ("phone", "+91 76720 18022", "917672018022", "https://example.com/contact"),
        _occ("phone", "76720 18022", "7672018022", "https://example.com/about"),
    ]
    report = engine.compare_field(occurrences, "phone")
    assert report.verdict in ("consistent", "minor_formatting_difference")


def test_different_phone_is_genuine_mismatch():
    engine = ComparisonEngine()
    occurrences = [
        _occ("phone", "+91 76720 18022", "917672018022", "https://example.com/contact"),
        _occ("phone", "+91 98765 43210", "919876543210", "https://example.com/about"),
    ]
    report = engine.compare_field(occurrences, "phone")
    assert report.verdict == "genuine_mismatch"


def test_weak_logo_name_does_not_create_false_mismatch():
    engine = ComparisonEngine()
    occurrences = [
        _occ("name", "GenTech Studio", "gentech studio", "https://example.com/", "json_ld", 1.0),
        _occ("name", "Gen Tech Logo", "gen tech logo", "https://example.com/", "html_logo_alt", 0.4),
    ]
    report = engine.compare_field(occurrences, "name")
    assert report.verdict == "consistent"


# ─── O: Single high-quality JSON-LD → not auto-uncertain ──────────────

def test_o_single_jsonld_high_confidence():
    engine = ComparisonEngine()
    occurrences = [
        _occ("phone", "+91 9876543210", "919876543210", "https://example.com/", "json_ld", 1.0),
    ]
    report = engine.compare_field(occurrences, "phone")
    assert report.verdict == "consistent"
    assert report.confidence >= 0.5


def test_o_single_jsonld_name_not_uncertain():
    engine = ComparisonEngine()
    occurrences = [
        _occ("name", "ABC Dental", "abc dental", "https://example.com/", "json_ld", 1.0),
    ]
    report = engine.compare_field(occurrences, "name")
    assert report.verdict == "consistent"
    assert report.confidence >= 0.5


# ─── Q: Missing NAP field → not_found ─────────────────────────────────

def test_q_missing_phone_not_found():
    engine = ComparisonEngine()
    report = engine.compare_field([], "phone")
    assert report.verdict == "not_found"
    assert report.confidence == 0.0


def test_q_missing_name_not_found():
    engine = ComparisonEngine()
    report = engine.compare_field([], "name")
    assert report.verdict == "not_found"


def test_q_missing_address_not_found():
    engine = ComparisonEngine()
    report = engine.compare_field([], "address")
    assert report.verdict == "not_found"


# ─── R: Ambiguous extraction → uncertain or low confidence ────────────

def test_r_single_title_derived_is_uncertain():
    """A single occurrence from title_derived (quality 0.30) should be uncertain."""
    engine = ComparisonEngine()
    occurrences = [
        _occ("name", "Some Website", "some website", "https://example.com/",
             "html_title", 0.30),
    ]
    report = engine.compare_field(occurrences, "name")
    assert report.verdict == "uncertain"
    assert report.confidence <= 0.40


def test_r_single_logo_alt_is_uncertain():
    engine = ComparisonEngine()
    occurrences = [
        _occ("name", "Biz Logo", "biz logo", "https://example.com/",
             "html_logo_alt", 0.40),
    ]
    report = engine.compare_field(occurrences, "name")
    assert report.verdict == "uncertain"
    assert report.confidence <= 0.40


# ─── Address: same components → consistent ─────────────────────────────

def test_address_same_components_consistent():
    engine = ComparisonEngine()
    occurrences = [
        _occ("address",
             "123 Main St., Hyderabad, Telangana, 500001",
             "123 main street, hyderabad, telangana, 500001",
             "https://example.com/"),
        _occ("address",
             "123 Main Street, Hyderabad, Telangana, 500001",
             "123 main street, hyderabad, telangana, 500001",
             "https://example.com/contact"),
    ]
    report = engine.compare_field(occurrences, "address")
    assert report.verdict in ("consistent", "minor_formatting_difference")


# ─── Address: different postal code → genuine_mismatch ─────────────────

def test_address_different_postal_code_mismatch():
    engine = ComparisonEngine()
    occurrences = [
        _occ("address",
             "123 Main Street, Hyderabad, Telangana, 500001",
             "123 main street, hyderabad, telangana, 500001",
             "https://example.com/"),
        _occ("address",
             "123 Main Street, Bangalore, Karnataka, 560001",
             "123 main street, bangalore, karnataka, 560001",
             "https://example.com/contact"),
    ]
    report = engine.compare_field(occurrences, "address")
    assert report.verdict == "genuine_mismatch"


# ─── Address: different city → genuine_mismatch ────────────────────────

def test_address_different_city_mismatch():
    engine = ComparisonEngine()
    occurrences = [
        _occ("address",
             "10 Road, Hyderabad, Telangana",
             "10 road, hyderabad, telangana",
             "https://example.com/"),
        _occ("address",
             "10 Road, Mumbai, Maharashtra",
             "10 road, mumbai, maharashtra",
             "https://example.com/contact"),
    ]
    report = engine.compare_field(occurrences, "address")
    assert report.verdict == "genuine_mismatch"


# ─── Phone: US formatting equivalence ──────────────────────────────────

def test_us_phone_formatting_equivalence():
    """US phone with and without country code should be equivalent."""
    engine = ComparisonEngine()
    occurrences = [
        _occ("phone", "+1 (212) 555-1234", "12125551234", "https://example.com/"),
        _occ("phone", "(212) 555-1234", "2125551234", "https://example.com/contact"),
    ]
    report = engine.compare_field(occurrences, "phone")
    assert report.verdict in ("consistent", "minor_formatting_difference")


def test_indian_phone_formatting_equivalence():
    """Indian phone with +91 and without +91 should be equivalent."""
    engine = ComparisonEngine()
    occurrences = [
        _occ("phone", "+91 92749 85691", "919274985691", "https://example.com/"),
        _occ("phone", "92749 85691", "9274985691", "https://example.com/contact"),
    ]
    report = engine.compare_field(occurrences, "phone")
    assert report.verdict in ("consistent", "minor_formatting_difference")



# ─── Pages_compared accuracy ──────────────────────────────────────────

def test_pages_compared_only_includes_relevant_pages():
    """pages_compared should only contain pages where the field was found."""
    engine = ComparisonEngine()
    occurrences = [
        _occ("phone", "+91 1234567890", "911234567890", "https://example.com/contact"),
        _occ("name", "Biz", "biz", "https://example.com/"),
    ]
    phone_report = engine.compare_field(occurrences, "phone")
    assert phone_report.pages_compared == ["https://example.com/contact"]

    name_report = engine.compare_field(occurrences, "name")
    assert name_report.pages_compared == ["https://example.com/"]
