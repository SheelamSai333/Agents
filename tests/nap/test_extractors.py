"""Tests for structured data and HTML NAP extractors (K–N, P)."""

import json

from seo_audit.models import PageResponse, ParsedPage
from nap_checker.structured_data_extractor import StructuredDataExtractor
from nap_checker.html_nap_extractor import HTMLNAPExtractor


def _make_page(html: str, url: str = "https://example.com/") -> ParsedPage:
    """Create a minimal ParsedPage with the given HTML content."""
    resp = PageResponse(
        requested_url=url,
        final_url=url,
        status_code=200,
        headers={"content-type": "text/html"},
        content=html,
    )
    return ParsedPage(url=url, response=resp)


# ─── K: JSON-LD @graph extraction ──────────────────────────────────────

def test_k_jsonld_graph():
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "LocalBusiness",
                "name": "ABC Dental",
                "telephone": "+91 9876543210",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "12 Main Road",
                    "addressLocality": "Hyderabad",
                },
            },
            {
                "@type": "WebSite",
                "name": "ABC Dental Website",
            },
        ],
    }
    html = f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body></body></html>'
    page = _make_page(html)

    extractor = StructuredDataExtractor()
    occurrences = extractor.extract_from_page(page)

    names = [o for o in occurrences if o.field == "name"]
    phones = [o for o in occurrences if o.field == "phone"]
    addresses = [o for o in occurrences if o.field == "address"]

    assert any(o.raw_value == "ABC Dental" and o.source_type == "json_ld" for o in names)
    assert any(o.raw_value == "+91 9876543210" for o in phones)
    assert any("12 Main Road" in o.raw_value for o in addresses)


# ─── L: JSON-LD nested PostalAddress ───────────────────────────────────

def test_l_jsonld_nested_postal_address():
    ld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "Test Clinic",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "42 MG Road",
            "addressLocality": "Bengaluru",
            "addressRegion": "Karnataka",
            "postalCode": "560001",
            "addressCountry": "IN",
        },
    }
    html = f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body></body></html>'
    page = _make_page(html)

    extractor = StructuredDataExtractor()
    occurrences = extractor.extract_from_page(page)

    addresses = [o for o in occurrences if o.field == "address"]
    assert len(addresses) >= 1
    addr = addresses[0]
    assert "42 MG Road" in addr.raw_value
    assert "Bengaluru" in addr.raw_value
    assert "560001" in addr.raw_value
    assert addr.source_quality == 1.0


# ─── M: JSON-LD root array ────────────────────────────────────────────

def test_m_jsonld_array():
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "ArrayOrg",
            "telephone": "+1 555 123 4567",
        },
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Home",
        },
    ]
    html = f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body></body></html>'
    page = _make_page(html)

    extractor = StructuredDataExtractor()
    occurrences = extractor.extract_from_page(page)

    names = [o for o in occurrences if o.field == "name" and o.source_type == "json_ld"]
    assert any(o.raw_value == "ArrayOrg" for o in names)

    phones = [o for o in occurrences if o.field == "phone"]
    assert any(o.raw_value == "+1 555 123 4567" for o in phones)


# ─── N: Microdata extraction ──────────────────────────────────────────

def test_n_microdata():
    html = """
    <html>
    <body>
    <div itemscope itemtype="https://schema.org/LocalBusiness">
        <span itemprop="name">Micro Dental</span>
        <span itemprop="telephone">+91 11223 34455</span>
        <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
            <span itemprop="streetAddress">99 Church St</span>
            <span itemprop="addressLocality">Chennai</span>
            <span itemprop="postalCode">600001</span>
        </div>
    </div>
    </body>
    </html>
    """
    page = _make_page(html)

    extractor = StructuredDataExtractor()
    occurrences = extractor.extract_from_page(page)

    names = [o for o in occurrences if o.field == "name" and o.source_type == "microdata"]
    assert any(o.raw_value == "Micro Dental" for o in names)
    assert all(o.source_quality == 0.9 for o in names)

    phones = [o for o in occurrences if o.field == "phone" and o.source_type == "microdata"]
    assert any(o.raw_value == "+91 11223 34455" for o in phones)

    addrs = [o for o in occurrences if o.field == "address" and o.source_type == "microdata"]
    assert len(addrs) >= 1
    assert "Chennai" in addrs[0].raw_value


# ─── P: Weak logo-alt extraction ──────────────────────────────────────

def test_p_logo_alt_low_quality():
    html = """
    <html>
    <body>
    <header>
        <nav><img src="/logo.png" alt="MyBiz Logo" /></nav>
    </header>
    </body>
    </html>
    """
    page = _make_page(html)
    page.title = "Welcome to MyBiz"

    extractor = HTMLNAPExtractor()
    occurrences = extractor.extract_from_page(page)

    logo_names = [
        o for o in occurrences
        if o.field == "name" and o.source_type == "html_logo_alt"
    ]
    assert len(logo_names) >= 1
    assert logo_names[0].source_quality == 0.40
    assert logo_names[0].raw_value == "MyBiz Logo"


# ─── Additional: multiple JSON-LD blocks on one page ───────────────────

def test_multiple_jsonld_blocks():
    ld1 = {"@type": "LocalBusiness", "name": "Biz Alpha", "telephone": "+1 111 222 3333"}
    ld2 = {"@type": "Organization", "name": "Biz Beta"}
    html = (
        '<html><head>'
        f'<script type="application/ld+json">{json.dumps(ld1)}</script>'
        f'<script type="application/ld+json">{json.dumps(ld2)}</script>'
        '</head><body></body></html>'
    )
    page = _make_page(html)

    extractor = StructuredDataExtractor()
    occurrences = extractor.extract_from_page(page)

    names = [o.raw_value for o in occurrences if o.field == "name"]
    assert "Biz Alpha" in names
    assert "Biz Beta" in names
