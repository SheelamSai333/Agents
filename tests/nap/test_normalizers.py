"""Tests for NAP normalizers — phone, address, name (A–J)."""

from nap_checker.normalizers import (
    normalize_phone,
    normalize_name,
    normalize_address,
    parse_address_components,
    extract_title_brand,
)


# ─── A: Same phone, different formatting ───────────────────────────────

def test_a_same_phone_different_formatting():
    """Indian phone in three formats should all normalize equivalently."""
    v1 = normalize_phone("+91 98765 43210")
    v2 = normalize_phone("+919876543210")
    v3 = normalize_phone("+91-98765-43210")
    assert v1 == v2 == v3 == "919876543210"


# ─── B: Different phone numbers ────────────────────────────────────────

def test_b_different_phone_numbers():
    v1 = normalize_phone("+91 98765 43210")
    v2 = normalize_phone("+91 99887 66554")
    assert v1 != v2
    assert v1 == "919876543210"
    assert v2 == "919988766554"


# ─── C: Indian phone normalization ─────────────────────────────────────

def test_c_indian_phone_with_country_code():
    assert normalize_phone("+91 76720 18022") == "917672018022"


def test_c_indian_phone_bare_local():
    """Without country hint, do not prepend country code."""
    assert normalize_phone("98765-43210") == "9876543210"


def test_c_indian_phone_with_country_hint():
    """With country hint, prepend country code to local number."""
    assert normalize_phone("98765-43210", country_hint="IN") == "919876543210"


def test_c_indian_phone_00_prefix():
    assert normalize_phone("0091 76720 18022") == "917672018022"


# ─── D: US phone normalization ─────────────────────────────────────────

def test_d_us_phone_international():
    assert normalize_phone("+1 (212) 555-1234") == "12125551234"


def test_d_us_phone_local():
    """Without country hint, do not prepend +1."""
    assert normalize_phone("(212) 555-1234") == "2125551234"


def test_d_us_phone_with_hint():
    assert normalize_phone("(212) 555-1234", country_hint="US") == "12125551234"


def test_d_us_phone_dashes():
    assert normalize_phone("+1-212-555-1234") == "12125551234"


# ─── E: UK phone normalization ─────────────────────────────────────────

def test_e_uk_phone_international():
    assert normalize_phone("+44 20 1234 5678") == "442012345678"


def test_e_uk_phone_local_with_hint():
    assert normalize_phone("020 1234 5678", country_hint="UK") == "442012345678"


# ─── F: Same address with abbreviations ────────────────────────────────

def test_f_same_address_abbreviations():
    a1 = normalize_address("123 Main St., Hyderabad, Telangana, 500001")
    a2 = normalize_address("123 Main Street, Hyderabad, Telangana, 500001")
    assert a1 == a2


def test_f_address_road_abbreviation():
    a1 = normalize_address("45 Park Rd, Mumbai")
    a2 = normalize_address("45 Park Road, Mumbai")
    assert a1 == a2


# ─── G: Different city ─────────────────────────────────────────────────

def test_g_different_city():
    c1 = parse_address_components("123 Main Street, Hyderabad, Telangana, 500001")
    c2 = parse_address_components("123 Main Street, Bangalore, Karnataka, 560001")
    assert c1.locality != c2.locality
    assert "hyderabad" in c1.locality
    assert "bangalore" in c2.locality


# ─── H: Different postal code ──────────────────────────────────────────

def test_h_different_postal_code():
    c1 = parse_address_components("123 Main Street, Hyderabad, Telangana, 500001")
    c2 = parse_address_components("123 Main Street, Hyderabad, Telangana, 500032")
    assert c1.postal_code == "500001"
    assert c2.postal_code == "500032"
    assert c1.postal_code != c2.postal_code


# ─── I: Same name with legal suffix differences ────────────────────────

def test_i_same_name_legal_suffix():
    assert normalize_name("ABC Dental Pvt. Ltd.") == normalize_name("ABC Dental")
    assert normalize_name("ABC Dental") == "abc dental"


def test_i_name_llc():
    assert normalize_name("Acme Corp LLC") == normalize_name("Acme Corp")


def test_i_name_inc():
    assert normalize_name("Tech Solutions Inc.") == normalize_name("Tech Solutions")


# ─── J: Genuine business name mismatch ─────────────────────────────────

def test_j_genuine_name_mismatch():
    n1 = normalize_name("ABC Dental")
    n2 = normalize_name("XYZ Medical")
    assert n1 != n2
    assert n1 == "abc dental"
    assert n2 == "xyz medical"


# ─── Title brand extraction ────────────────────────────────────────────

def test_title_brand_with_pipe():
    assert extract_title_brand("Best Dental Clinic in Hyderabad | ABC Dental") == "ABC Dental"


def test_title_brand_with_dash():
    assert extract_title_brand("About Us - ABC Dental") == "ABC Dental"


def test_title_brand_no_separator():
    assert extract_title_brand("ABC Dental") == "ABC Dental"


def test_title_brand_long_title():
    """Very long titles without separator should return empty."""
    long_title = "A" * 100
    assert extract_title_brand(long_title) == ""
