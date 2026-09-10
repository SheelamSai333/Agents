"""
Tests for ContentExtractor: semantic segmentation, boilerplate tagging, and heading hierarchy.
"""

from seo_audit.models import PageResponse, ParsedPage
from site_qa.content_extractor import ContentExtractor


def _make_page(html: str, url: str = "https://example.com/page") -> ParsedPage:
    resp = PageResponse(
        requested_url=url,
        final_url=url,
        status_code=200,
        headers={"content-type": "text/html"},
        content=html,
    )
    return ParsedPage(url=url, response=resp)


def test_extract_paragraphs_and_headings():
    html = """
    <html>
      <body>
        <h1>Welcome to Acme</h1>
        <p>Acme develops high-performance widgets for industrial automation.</p>
        <h2>Product Warranty</h2>
        <p>All Acme widgets carry an unconditional three-year replacement warranty.</p>
      </body>
    </html>
    """
    page = _make_page(html)
    extractor = ContentExtractor()
    chunks = extractor.extract_chunks(page)

    assert len(chunks) == 4
    # Check heading breadcrumbs for warranty paragraph
    warranty_chunk = chunks[3]
    assert "warranty" in warranty_chunk.text.lower()
    assert "Product Warranty" in warranty_chunk.heading_hierarchy
    assert not warranty_chunk.is_boilerplate


def test_boilerplate_detection():
    html = """
    <html>
      <body>
        <header>
          <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
          </nav>
        </header>
        <main>
          <p>This is the primary main content of the web page.</p>
        </main>
        <footer>
          <p class="copyright">Copyright 2026 Acme Corp. All rights reserved.</p>
        </footer>
      </body>
    </html>
    """
    page = _make_page(html)
    extractor = ContentExtractor()
    chunks = extractor.extract_chunks(page)

    main_chunks = [c for c in chunks if not c.is_boilerplate]
    boilerplate_chunks = [c for c in chunks if c.is_boilerplate]

    assert len(main_chunks) == 1
    assert "primary main content" in main_chunks[0].text
    assert len(boilerplate_chunks) == 1
    assert "Copyright" in boilerplate_chunks[0].text


def test_script_and_style_stripping():
    html = """
    <html>
      <head>
        <style>body { color: red; }</style>
      </head>
      <body>
        <script>var secretToken = "xyz123";</script>
        <p>Visible documentation content here.</p>
      </body>
    </html>
    """
    page = _make_page(html)
    extractor = ContentExtractor()
    chunks = extractor.extract_chunks(page)
    full_text = extractor.extract_full_visible_text(page)

    assert "secretToken" not in full_text
    assert "color: red" not in full_text
    assert "Visible documentation content here." in full_text
    assert len(chunks) == 1
    assert chunks[0].text == "Visible documentation content here."


def test_verbatim_text_preservation():
    html = """
    <html>
      <body>
        <p>Exact Punctuation &amp; Casing: Acme-v2.0 costs $499.99/mo (billed annually)!</p>
      </body>
    </html>
    """
    page = _make_page(html)
    extractor = ContentExtractor()
    chunks = extractor.extract_chunks(page)

    assert chunks[0].text == "Exact Punctuation & Casing: Acme-v2.0 costs $499.99/mo (billed annually)!"
