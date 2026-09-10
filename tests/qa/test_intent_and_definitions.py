"""
Tests for semantic intent classification, definition predicate matching,
oblique mention suppression, and depth weighting.
"""

from seo_audit.models import PageResponse, ParsedPage
from site_qa.agent import QAAgent
from site_qa.content_extractor import ContentExtractor
from site_qa.indexer import BM25Index
from site_qa.models import ContentChunk
from site_qa.query_processor import QueryProcessor
from site_qa.searcher import PassageSearcher, check_explanatory_predicate


def test_query_processor_intent_classification():
    q_def = QueryProcessor.process("What is Google Search Console?")
    assert q_def.intent == "DEFINITION"
    assert "search console" in q_def.target_subject

    q_who = QueryProcessor.process("Who is the CEO of Acme?")
    assert q_who.intent == "DEFINITION"
    assert "ceo of acme" in q_def.target_subject or "ceo" in q_who.target_subject

    q_price = QueryProcessor.process("How much does the Pro subscription cost?")
    assert q_price.intent == "PRICE_COST"

    q_loc = QueryProcessor.process("Where is the headquarters located?")
    assert q_loc.intent == "LOCATION"


def test_check_explanatory_predicates_various_forms():
    # 'is a tool'
    text1 = "Search Console is a tool from Google that can help anyone with a website."
    has_expl1, is_oblique1 = check_explanatory_predicate(text1, "google search console", ["search", "console"], [])
    assert has_expl1 is True
    assert is_oblique1 is False

    # 'helps'
    text2 = "DataSync helps engineering teams automate real-time streaming pipelines."
    has_expl2, is_oblique2 = check_explanatory_predicate(text2, "datasync", ["datasync"], [])
    assert has_expl2 is True
    assert is_oblique2 is False

    # 'provides'
    text3 = "Acme Cloud provides scalable object storage with high durability."
    has_expl3, is_oblique3 = check_explanatory_predicate(text3, "acme cloud", ["acme", "cloud"], [])
    assert has_expl3 is True
    assert is_oblique3 is False

    # 'allows'
    text4 = "WebPulse allows developers to monitor real-time API latency."
    has_expl4, is_oblique4 = check_explanatory_predicate(text4, "webpulse", ["webpulse"], [])
    assert has_expl4 is True
    assert is_oblique4 is False

    # 'enables'
    text5 = "NeuroNet enables enterprise teams to train custom models."
    has_expl5, is_oblique5 = check_explanatory_predicate(text5, "neuronet", ["neuronet"], [])
    assert has_expl5 is True
    assert is_oblique5 is False

    # 'is used to'
    text6 = "Redis is used to cache frequent database queries."
    has_expl6, is_oblique6 = check_explanatory_predicate(text6, "redis", ["redis"], [])
    assert has_expl6 is True
    assert is_oblique6 is False

    # 'refers to'
    text7 = "Latency refers to the delay before transfer of data begins."
    has_expl7, is_oblique7 = check_explanatory_predicate(text7, "latency", ["latency"], [])
    assert has_expl7 is True
    assert is_oblique7 is False

    # 'serves as'
    text8 = "The API Gateway serves as a single entry point for microservices."
    has_expl8, is_oblique8 = check_explanatory_predicate(text8, "api gateway", ["api", "gateway"], [])
    assert has_expl8 is True
    assert is_oblique8 is False

    # Oblique mention
    text_oblique = "To check your indexing status, use the URL Inspection Tool in Search Console."
    has_expl_ob, is_oblique = check_explanatory_predicate(text_oblique, "google search console", ["search", "console"], [])
    assert has_expl_ob is False
    assert is_oblique is True


def test_definitional_intent_prefers_definition_over_incidental_mention():
    c_mention = ContentChunk(
        page_url="https://example.com/starter-guide",
        text="To check how Google sees your page, use the URL Inspection Tool in Search Console .",
        tag="p",
        crawl_depth=1,
        chunk_id=0,
    )
    c_definition = ContentChunk(
        page_url="https://example.com/search-console-start",
        text="Search Console is a tool from Google that can help anyone with a website to understand how they are performing on Google Search.",
        tag="p",
        crawl_depth=0,
        chunk_id=1,
    )

    idx = BM25Index([c_mention, c_definition])
    searcher = PassageSearcher(idx)
    query = QueryProcessor.process("What is Google Search Console?")

    results = searcher.search(query)
    assert len(results) >= 2
    # The definition must rank first
    assert results[0].chunk.page_url == "https://example.com/search-console-start"
    assert results[0].has_explanatory_predicate is True
    assert results[1].is_oblique_mention is True


def test_definitional_query_returns_null_when_only_incidental_mentions_exist():
    # Site where entity is only mentioned in passing without any definition
    p = ParsedPage(
        url="https://example.com/integrations",
        response=PageResponse(
            requested_url="https://example.com/integrations",
            final_url="https://example.com/integrations",
            status_code=200,
            headers={"content-type": "text/html"},
            content="""
            <html>
              <body>
                <h1>Integration Partners</h1>
                <p>We provide one-click sync capabilities with Slack, Jira, and GitHub.</p>
                <p>You can also export your telemetry data directly into Kafka pipelines.</p>
              </body>
            </html>
            """,
        ),
    )

    agent = QAAgent()
    # "What is Kafka?" on a site that only has "...into Kafka pipelines" (no definition of Kafka)
    res = agent.answer_query([p], "What is Kafka?")

    assert res.url is None
    assert res.excerpt is None
    assert res.to_dict() == {
        "query": "What is Kafka?",
        "url": None,
        "excerpt": None,
    }


def test_start_page_depth_boost():
    # Both pages contain valid answers, but start page (depth 0) is prioritized
    c_start = ContentChunk(
        page_url="https://example.com/service",
        text="ServiceX provides automated invoice reconciliations for accountants.",
        tag="p",
        crawl_depth=0,
        chunk_id=0,
    )
    c_subpage = ContentChunk(
        page_url="https://example.com/blog/servicex-feature",
        text="ServiceX provides automated invoice reconciliations for accountants.",
        tag="p",
        crawl_depth=2,
        chunk_id=1,
    )

    idx = BM25Index([c_start, c_subpage])
    searcher = PassageSearcher(idx)
    query = QueryProcessor.process("What is ServiceX?")

    results = searcher.search(query)
    assert results[0].chunk.page_url == "https://example.com/service"
    assert results[0].chunk.crawl_depth == 0
