"""
Tests for ExcerptExtractor: exact substring fidelity and bounding sentence extraction.
"""

from site_qa.excerpt_extractor import ExcerptExtractor
from site_qa.models import ContentChunk, ScoredPassage
from site_qa.query_processor import QueryProcessor


def test_excerpt_is_exact_substring_of_short_chunk():
    chunk = ContentChunk(
        page_url="https://example.com/pricing",
        text="Pro plan costs $29 per month with unlimited projects.",
        tag="p",
    )
    passage = ScoredPassage(chunk=chunk, score=5.0)
    query = QueryProcessor.process("How much does the Pro plan cost?")

    extractor = ExcerptExtractor()
    excerpt = extractor.extract(passage, query)

    assert excerpt in chunk.text
    assert excerpt == "Pro plan costs $29 per month with unlimited projects."


def test_excerpt_extracts_best_sentence_from_multi_sentence_chunk():
    text = (
        "Welcome to our platform overview. "
        "We support companies of all sizes across North America. "
        "Enterprise subscriptions include 24/7 phone and email support. "
        "Contact sales for customized on-premise hardware deployments."
    )
    chunk = ContentChunk(
        page_url="https://example.com/enterprise",
        text=text,
        tag="p",
    )
    passage = ScoredPassage(chunk=chunk, score=6.0)
    query = QueryProcessor.process("Does Enterprise have 24/7 support?")

    extractor = ExcerptExtractor(max_excerpt_chars=120)
    excerpt = extractor.extract(passage, query)

    # Must be exact verbatim substring
    assert excerpt in chunk.text
    assert "Enterprise subscriptions include 24/7 phone and email support." in excerpt


def test_excerpt_preserves_original_casing_and_punctuation():
    text = "Important Note: API v3.5 requires TLS-1.3 & Bearer token authorization!"
    chunk = ContentChunk(
        page_url="https://example.com/docs",
        text=text,
        tag="p",
    )
    passage = ScoredPassage(chunk=chunk, score=4.5)
    query = QueryProcessor.process("What TLS version is required for the API?")

    extractor = ExcerptExtractor()
    excerpt = extractor.extract(passage, query)

    assert excerpt == text
    assert excerpt in chunk.text
