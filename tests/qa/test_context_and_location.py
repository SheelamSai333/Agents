"""
Regression tests for context-dependent queries and location grounding.
Ensures context pronouns ('this', 'it', 'here') are grounded against the website entity,
unrelated keyword matches (such as legal dispute court clauses) are rejected,
and unsupported queries return null.
"""

import pytest
from seo_audit.models import PageResponse, ParsedPage
from site_qa.agent import QAAgent
from site_qa.query_processor import QueryProcessor
from site_qa.searcher import check_location_evidence


def test_location_evidence_disqualifies_court_jurisdiction_clauses():
    """Legal dispute court jurisdiction clauses must be rejected as location evidence."""
    query = QueryProcessor.process("where is this located?")

    court_clause = (
        "The Terms shall be subject to the exclusive jurisdiction of the competent courts "
        "located in Hyderabad and You hereby accede to and accept the jurisdiction of such courts."
    )
    has_ev, is_disq = check_location_evidence(court_clause, ["Terms and Conditions"], "https://example.com/terms", query)
    assert is_disq is True
    assert has_ev is False

    dispute_clause = "Any dispute arising out of this agreement shall be governed by the laws of California."
    has_ev2, is_disq2 = check_location_evidence(dispute_clause, ["Legal Information"], "https://example.com/legal", query)
    assert is_disq2 is True


def test_location_evidence_rejects_pure_opening_hours():
    """Opening hours or days of operation must not be mistaken for location evidence."""
    query = QueryProcessor.process("where is this located?")

    hours_text = "Monday - Sunday 10AM - 9 PM"
    has_ev, is_disq = check_location_evidence(hours_text, ["Our Centers Across Multiple Locations"], "https://example.com/locations", query)
    assert has_ev is False
    assert is_disq is False


def test_location_evidence_accepts_physical_address():
    """Physical address containing street/building/road/postal code must be accepted."""
    query = QueryProcessor.process("where is this located?")

    addr_text = "Survey No 76, Block-B, Premier Building, 3rd & 4th Floor, Sri Sai Nagar, Madhapur, Hyderabad, Telangana 500081"
    has_ev, is_disq = check_location_evidence(addr_text, ["Our Training Centers"], "https://example.com/intensive", query)
    assert has_ev is True
    assert is_disq is False


def test_context_dependent_location_selects_address_over_legal_court_clause():
    """
    Regression test for: 'Where is this located?'
    Site has:
    1. Start page with physical branch addresses.
    2. Terms page mentioning 'courts located in Hyderabad'.
    The agent must select the target page address and reject the court clause on /terms.
    """
    start_html = """
    <html>
      <body>
        <h1>Apex Tech Bootcamp</h1>
        <h2>Our Training Centers Across Multiple Locations</h2>
        <div>
          <h3>Hyderabad Campus</h3>
          <div>Plot 42, Silicon Valley Road, HITEC City, Hyderabad, Telangana 500081</div>
        </div>
      </body>
    </html>
    """
    terms_html = """
    <html>
      <body>
        <h1>Terms of Service</h1>
        <p>Section 18. Governing Law and Jurisdiction. These Terms shall be governed by and construed in accordance with the laws of India. Further, the Terms shall be subject to the exclusive jurisdiction of the competent courts located in Hyderabad.</p>
      </body>
    </html>
    """
    start_page = ParsedPage(
        url="https://apextech.edu/bootcamp",
        response=PageResponse(
            requested_url="https://apextech.edu/bootcamp",
            final_url="https://apextech.edu/bootcamp",
            status_code=200,
            headers={"content-type": "text/html"},
            content=start_html,
            depth=0,
        ),
    )
    terms_page = ParsedPage(
        url="https://apextech.edu/terms-and-conditions",
        response=PageResponse(
            requested_url="https://apextech.edu/terms-and-conditions",
            final_url="https://apextech.edu/terms-and-conditions",
            status_code=200,
            headers={"content-type": "text/html"},
            content=terms_html,
            depth=1,
        ),
    )

    agent = QAAgent()
    response = agent.answer_query([start_page, terms_page], "where is this located?", start_url="https://apextech.edu/bootcamp")

    assert response.url == "https://apextech.edu/bootcamp"
    assert response.excerpt is not None
    assert "HITEC City" in response.excerpt
    assert "Plot 42" in response.excerpt
    assert "courts located" not in response.excerpt


def test_context_dependent_location_returns_null_when_unsupported():
    """
    When an arbitrary website has NO physical address, office, or location mentioned,
    'Where is this located?' must return url=None and excerpt=None.
    """
    saas_html = """
    <html>
      <body>
        <h1>CloudMetrics API</h1>
        <p>CloudMetrics collects real-time telemetry from Kubernetes clusters.</p>
        <h2>Features</h2>
        <p>Support for Prometheus metrics, OpenTelemetry traces, and structured JSON logs.</p>
      </body>
    </html>
    """
    page = ParsedPage(
        url="https://cloudmetrics.dev/",
        response=PageResponse(
            requested_url="https://cloudmetrics.dev/",
            final_url="https://cloudmetrics.dev/",
            status_code=200,
            headers={"content-type": "text/html"},
            content=saas_html,
            depth=0,
        ),
    )

    agent = QAAgent()
    response = agent.answer_query([page], "Where is this located?")

    assert response.url is None
    assert response.excerpt is None
    assert response.to_dict() == {
        "query": "Where is this located?",
        "url": None,
        "excerpt": None,
    }


def test_cross_page_semantic_location_retrieval():
    """
    When the query uses 'where is this located?' and the address is on a linked
    semantically relevant page (/contact), the agent should find and ground it.
    """
    home_html = """
    <html>
      <body>
        <h1>Nordic Roasters</h1>
        <p>We source ethical specialty coffee from smallholder farms worldwide.</p>
      </body>
    </html>
    """
    contact_html = """
    <html>
      <body>
        <h1>Contact &amp; Roastery Location</h1>
        <p>Our flagship roastery is located at 104 Fjordgata, Oslo, Norway 0152.</p>
      </body>
    </html>
    """
    home_page = ParsedPage(
        url="https://nordicroasters.com/",
        response=PageResponse(
            requested_url="https://nordicroasters.com/",
            final_url="https://nordicroasters.com/",
            status_code=200,
            headers={"content-type": "text/html"},
            content=home_html,
            depth=0,
        ),
    )
    contact_page = ParsedPage(
        url="https://nordicroasters.com/contact",
        response=PageResponse(
            requested_url="https://nordicroasters.com/contact",
            final_url="https://nordicroasters.com/contact",
            status_code=200,
            headers={"content-type": "text/html"},
            content=contact_html,
            depth=1,
        ),
    )

    agent = QAAgent()
    response = agent.answer_query([home_page, contact_page], "Where is this located?")

    assert response.url == "https://nordicroasters.com/contact"
    assert response.excerpt is not None
    assert "Oslo, Norway" in response.excerpt
