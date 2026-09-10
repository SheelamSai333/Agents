"""
Tests for QueryProcessor, BM25Index, and PassageSearcher.
"""

from site_qa.indexer import BM25Index
from site_qa.models import ContentChunk
from site_qa.query_processor import QueryProcessor
from site_qa.searcher import PassageSearcher


def test_query_processor_question_stripping():
    query = "Where can I find the return policy for international orders?"
    processed = QueryProcessor.process(query)

    assert "return" in processed.content_terms
    assert "policy" in processed.content_terms
    assert "international" in processed.content_terms
    assert "orders" in processed.content_terms
    assert "can" not in processed.content_terms
    assert "find" not in processed.content_terms
    assert "where" not in processed.content_terms
    assert "return policy" in processed.phrases


def test_bm25_relevance_ranking():
    chunks = [
        ContentChunk(
            page_url="https://example.com/about",
            text="Acme Corp was founded in 1998 in Chicago.",
            tag="p",
            chunk_id=0,
        ),
        ContentChunk(
            page_url="https://example.com/shipping",
            text="Standard domestic shipping takes 3 to 5 business days.",
            tag="p",
            chunk_id=1,
        ),
        ContentChunk(
            page_url="https://example.com/returns",
            text="Our return policy allows items to be returned within 30 days for a full refund.",
            tag="p",
            chunk_id=2,
        ),
    ]

    index = BM25Index(chunks)
    searcher = PassageSearcher(index)

    query = QueryProcessor.process("What is the return policy duration?")
    results = searcher.search(query)

    assert len(results) > 0
    top = results[0]
    assert top.chunk.page_url == "https://example.com/returns"
    assert "return" in top.matched_terms
    assert "policy" in top.matched_terms


def test_exact_phrase_boost():
    chunks = [
        ContentChunk(
            page_url="https://example.com/scattered",
            text="You can policy your items or return to our warehouse anytime.",
            tag="p",
            chunk_id=0,
        ),
        ContentChunk(
            page_url="https://example.com/exact",
            text="The standard return policy is valid for thirty days.",
            tag="p",
            chunk_id=1,
        ),
    ]

    index = BM25Index(chunks)
    searcher = PassageSearcher(index)

    query = QueryProcessor.process("return policy")
    results = searcher.search(query)

    assert results[0].chunk.page_url == "https://example.com/exact"
    assert results[0].has_phrase_match is True


def test_boilerplate_penalization():
    chunks = [
        ContentChunk(
            page_url="https://example.com/",
            text="Privacy and Return Policy Footer Link",
            tag="p",
            is_boilerplate=True,
            chunk_id=0,
        ),
        ContentChunk(
            page_url="https://example.com/returns",
            text="Customers may return merchandise within thirty calendar days of purchase.",
            tag="p",
            is_boilerplate=False,
            heading_hierarchy=["Refund Information"],
            chunk_id=1,
        ),
    ]

    index = BM25Index(chunks)
    searcher = PassageSearcher(index)

    query = QueryProcessor.process("How to return merchandise?")
    results = searcher.search(query)

    assert results[0].chunk.page_url == "https://example.com/returns"
    assert results[0].chunk.is_boilerplate is False
