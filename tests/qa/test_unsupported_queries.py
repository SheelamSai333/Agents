"""
Tests for unsupported query detection and zero-hallucination behavior.
"""

from seo_audit.models import PageResponse, ParsedPage
from site_qa.agent import QAAgent


def _create_mock_site() -> list[ParsedPage]:
    p1 = ParsedPage(
        url="https://coffeeshop.com/",
        response=PageResponse(
            requested_url="https://coffeeshop.com/",
            final_url="https://coffeeshop.com/",
            status_code=200,
            headers={"content-type": "text/html"},
            content="""
            <html>
              <body>
                <h1>Downtown Artisan Coffee</h1>
                <p>We roast single-origin espresso beans every morning in Seattle.</p>
                <p>Opening hours are Monday through Friday, 7 AM to 6 PM.</p>
              </body>
            </html>
            """,
        ),
    )
    p2 = ParsedPage(
        url="https://coffeeshop.com/menu",
        response=PageResponse(
            requested_url="https://coffeeshop.com/menu",
            final_url="https://coffeeshop.com/menu",
            status_code=200,
            headers={"content-type": "text/html"},
            content="""
            <html>
              <body>
                <h1>Beverage Menu</h1>
                <p>Cappuccino is crafted with double espresso and steamed oat milk for $4.50.</p>
                <p>Cold brew is steeped for 18 hours and served over ice for $5.00.</p>
              </body>
            </html>
            """,
        ),
    )
    return [p1, p2]


def test_unrelated_query_returns_null():
    pages = _create_mock_site()
    agent = QAAgent()

    # Completely off-topic query
    response = agent.answer_query(pages, "What is the launch schedule of the Falcon 9 rocket?")

    assert response.url is None
    assert response.excerpt is None
    assert response.to_dict() == {
        "query": "What is the launch schedule of the Falcon 9 rocket?",
        "url": None,
        "excerpt": None,
    }


def test_conversational_fluff_query_returns_null():
    pages = _create_mock_site()
    agent = QAAgent()

    # Query with no substantive content words
    response = agent.answer_query(pages, "Can you tell me about what this is?")

    assert response.url is None
    assert response.excerpt is None


def test_partial_term_absence_returns_null():
    pages = _create_mock_site()
    agent = QAAgent()

    # Site has 'espresso', but nothing about 'quantum mechanics' or 'crypto wallets'
    response = agent.answer_query(pages, "Does this shop accept Bitcoin cryptocurrency wallets for espresso?")

    assert response.url is None
    assert response.excerpt is None
