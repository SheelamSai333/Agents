"""
Unit tests for the HTML Parser component.
"""

import pytest
from seo_audit.models import PageResponse
from seo_audit.parser import HTMLParser


@pytest.fixture
def parser():
    return HTMLParser()


def test_parser_extracts_metadata(parser):
    html = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Test Page Title</title>
        <meta name="description" content="A detailed test description for SEO parser verification.">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="robots" content="noindex, follow">
        <link rel="canonical" href="https://example.com/canonical-url">
        <meta property="og:title" content="OG Test Title">
        <meta property="og:description" content="OG Description">
    </head>
    <body>
        <h1>Main Heading</h1>
        <h2>Subheading 1</h2>
        <p>This is test visible body text containing several useful words for extraction.</p>
        <img src="/images/test.jpg" alt="A test logo">
        <img src="/images/no-alt.jpg">
        <a href="/about">About Us</a>
        <a href="https://external.com">External</a>
        <a href="">Empty Link</a>
    </body>
    </html>
    """
    response = PageResponse(
        requested_url="https://example.com/",
        final_url="https://example.com/",
        status_code=200,
        headers={"content-type": "text/html"},
        content=html,
    )

    parsed = parser.parse(response)

    assert parsed.html_lang == "en"
    assert parsed.title == "Test Page Title"
    assert parsed.meta_description == "A detailed test description for SEO parser verification."
    assert parsed.viewport == "width=device-width, initial-scale=1"
    assert "noindex, follow" in parsed.robots_meta
    assert len(parsed.canonical_urls) == 1
    assert parsed.canonical_urls[0] == "https://example.com/canonical-url"
    assert parsed.open_graph.get("og:title") == "OG Test Title"

    # Headings
    assert len(parsed.headings) == 2
    assert parsed.headings[0].level == 1
    assert parsed.headings[0].text == "Main Heading"
    assert parsed.headings[1].level == 2
    assert parsed.headings[1].text == "Subheading 1"

    # Images
    assert len(parsed.images) == 2
    assert parsed.images[0].has_alt is True
    assert parsed.images[0].alt == "A test logo"
    assert parsed.images[1].has_alt is False
    assert parsed.images[1].alt is None

    # Links
    assert len(parsed.links) == 3
    internal_links = [l for l in parsed.links if l.is_internal]
    assert len(internal_links) == 1
    assert internal_links[0].text == "About Us"

    # Word count
    assert parsed.visible_word_count > 5
