"""
End-to-End integration tests for QAAgent with GroundingVerifier.
"""

import json
from pathlib import Path
import pytest

from seo_audit.models import PageResponse, ParsedPage
from site_qa.agent import QAAgent
from site_qa.content_extractor import ContentExtractor
from site_qa.verifier import GroundingVerifier


@pytest.fixture
def multi_page_site() -> list[ParsedPage]:
    home_html = """
    <html>
      <body>
        <header><nav><a href="/">Home</a> <a href="/pricing">Pricing</a> <a href="/contact">Contact</a></nav></header>
        <main>
          <h1>CloudSync Software</h1>
          <p>CloudSync automatically synchronizes database backups to distributed S3 storage.</p>
        </main>
        <footer><p>&copy; 2026 CloudSync Technologies</p></footer>
      </body>
    </html>
    """
    pricing_html = """
    <html>
      <body>
        <header><nav><a href="/">Home</a> <a href="/pricing">Pricing</a> <a href="/contact">Contact</a></nav></header>
        <main>
          <h1>Subscription Pricing</h1>
          <p>The Developer tier is free for up to 10 gigabytes of monthly backup transfers.</p>
          <p>The Enterprise plan is $199 monthly with unlimited storage and dedicated account management.</p>
        </main>
      </body>
    </html>
    """
    security_html = """
    <html>
      <body>
        <header><nav><a href="/">Home</a> <a href="/security">Security</a></nav></header>
        <main>
          <h1>Data Security &amp; Encryption</h1>
          <p>All backups are encrypted in transit with TLS-1.3 and at rest using AES-256-GCM.</p>
          <p>Our infrastructure holds SOC-2 Type II and ISO-27001 compliance certifications.</p>
        </main>
      </body>
    </html>
    """
    return [
        ParsedPage(
            url="https://cloudsync.io/",
            response=PageResponse(
                requested_url="https://cloudsync.io/",
                final_url="https://cloudsync.io/",
                status_code=200,
                headers={"content-type": "text/html"},
                content=home_html,
            ),
        ),
        ParsedPage(
            url="https://cloudsync.io/pricing",
            response=PageResponse(
                requested_url="https://cloudsync.io/pricing",
                final_url="https://cloudsync.io/pricing",
                status_code=200,
                headers={"content-type": "text/html"},
                content=pricing_html,
            ),
        ),
        ParsedPage(
            url="https://cloudsync.io/security",
            response=PageResponse(
                requested_url="https://cloudsync.io/security",
                final_url="https://cloudsync.io/security",
                status_code=200,
                headers={"content-type": "text/html"},
                content=security_html,
            ),
        ),
    ]


def test_e2e_answer_retrieval_and_grounding(multi_page_site, tmp_path):
    agent = QAAgent()
    extractor = ContentExtractor()

    # Query 1: Pricing question
    q1 = "How much does the Enterprise plan cost per month?"
    resp1 = agent.answer_query(multi_page_site, q1)

    assert resp1.url == "https://cloudsync.io/pricing"
    assert resp1.excerpt is not None
    assert "$199" in resp1.excerpt
    assert "Enterprise plan is $199 monthly" in resp1.excerpt

    # Verify excerpt is a verbatim substring of source page's visible text
    pricing_page = next(p for p in multi_page_site if p.url == resp1.url)
    visible_text = extractor.extract_full_visible_text(pricing_page)
    assert resp1.excerpt in visible_text

    # Query 2: Encryption question
    q2 = "What encryption standard is used for backups at rest?"
    resp2 = agent.answer_query(multi_page_site, q2)

    assert resp2.url == "https://cloudsync.io/security"
    assert resp2.excerpt is not None
    assert "AES-256-GCM" in resp2.excerpt

    security_page = next(p for p in multi_page_site if p.url == resp2.url)
    assert resp2.excerpt in extractor.extract_full_visible_text(security_page)

    # Test export to answer.json
    out_file = tmp_path / "answer.json"
    agent.export_answer(resp1, str(out_file))

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["query"] == q1
    assert data["url"] == "https://cloudsync.io/pricing"
    assert data["excerpt"] == resp1.excerpt


def test_grounding_verifier_rejects_hallucinated_excerpt(multi_page_site):
    verifier = GroundingVerifier()

    # Excerpt that doesn't exist on security page
    fake_excerpt = "All backups are stored on floppy disks in Nevada."
    is_valid = verifier.verify("https://cloudsync.io/security", fake_excerpt, multi_page_site)

    assert is_valid is False
