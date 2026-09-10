"""
Main Q3 Question-Answering Agent Orchestrator.

Processes crawled pages, builds search index, retrieves best grounded passage,
extracts verbatim excerpt, verifies grounding against source visible text,
and exports answer.json.
"""

import logging
from typing import List, Optional

from seo_audit.models import ParsedPage
from site_qa.content_extractor import ContentExtractor
from site_qa.excerpt_extractor import ExcerptExtractor
from site_qa.indexer import BM25Index
from site_qa.models import ContentChunk, QAResponse
from site_qa.query_processor import QueryProcessor
from site_qa.reporter import export_answer_json, print_qa_cli_summary
from site_qa.searcher import PassageSearcher
from site_qa.verifier import GroundingVerifier

logger = logging.getLogger(__name__)


class QAAgent:
    """Orchestrates end-to-end question answering on crawled website pages."""

    def __init__(
        self,
        min_score_threshold: float = 0.35,
        min_term_coverage: float = 0.4,
    ):
        self.extractor = ContentExtractor()
        self.excerpt_extractor = ExcerptExtractor()
        self.verifier = GroundingVerifier(extractor=self.extractor)
        self.min_score_threshold = min_score_threshold
        self.min_term_coverage = min_term_coverage

    def answer_query(
        self,
        crawled_pages: List[ParsedPage],
        query: str,
    ) -> QAResponse:
        """
        Process crawled pages, search for query answer, extract verbatim excerpt,
        and verify against source page text.
        """
        logger.info("Processing user query: '%s' across %d crawled pages", query, len(crawled_pages))

        # 1. Process query
        processed_query = QueryProcessor.process(query)
        if not processed_query.has_substantive_terms:
            logger.info("Query has no substantive terms. Returning null answer.")
            return QAResponse(query=query, url=None, excerpt=None, confidence=0.0)

        # 2. Extract content chunks from all crawled pages
        all_chunks: List[ContentChunk] = []
        for page in crawled_pages:
            chunks = self.extractor.extract_chunks(page)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("No content chunks extracted from crawled pages.")
            return QAResponse(query=query, url=None, excerpt=None, confidence=0.0)

        # 3. Build in-memory BM25 index
        index = BM25Index(all_chunks)

        # 4. Search and retrieve top candidate passage
        searcher = PassageSearcher(
            index=index,
            min_score_threshold=self.min_score_threshold,
            min_term_coverage=self.min_term_coverage,
        )
        result = searcher.get_best_supported_passage(processed_query)

        if not result:
            logger.info("Query is unsupported by crawled content. Returning null answer.")
            return QAResponse(query=query, url=None, excerpt=None, confidence=0.0)

        top_passage, score = result
        target_url = top_passage.chunk.page_url

        # 5. Extract verbatim excerpt
        excerpt = self.excerpt_extractor.extract(top_passage, processed_query)

        # 6. Verify grounding against actual visible text of source page
        is_verified = self.verifier.verify(target_url, excerpt, crawled_pages)

        if not is_verified:
            logger.warning(
                "Grounding verification failed for url %s and excerpt '%s'. Returning null answer.",
                target_url,
                excerpt[:60],
            )
            return QAResponse(query=query, url=None, excerpt=None, confidence=0.0)

        # Confidence normalized to 0.0 - 1.0 range
        confidence = min(1.0, round(score / 10.0, 2)) if score > 0 else 0.0

        logger.info("Answer found on %s with verified excerpt.", target_url)
        return QAResponse(
            query=query,
            url=target_url,
            excerpt=excerpt,
            confidence=confidence,
            debug_info={
                "score": round(score, 4),
                "matched_terms": top_passage.matched_terms,
                "has_phrase_match": top_passage.has_phrase_match,
            },
        )

    def export_answer(
        self,
        response: QAResponse,
        output_path: str = "outputs/answer.json",
    ) -> None:
        """Export answer to JSON."""
        export_answer_json(response, output_path)

    def print_summary(
        self,
        response: QAResponse,
        crawled_count: int,
        duration: float,
        output_path: str = "outputs/answer.json",
    ) -> None:
        """Print CLI summary table."""
        print_qa_cli_summary(response, crawled_count, duration, output_path)
