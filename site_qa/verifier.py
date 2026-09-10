"""
Grounding Verifier for Q3.

Ensures that any returned answer excerpt is strictly confirmed to be a
contiguous substring of the target page's visible text, preventing
hallucinations, approximations, or detached content.
"""

import logging
from typing import List, Optional

from seo_audit.models import ParsedPage
from site_qa.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)


class GroundingVerifier:
    """Verifies that an extracted excerpt exists verbatim in the source page's visible text."""

    def __init__(self, extractor: Optional[ContentExtractor] = None):
        self.extractor = extractor or ContentExtractor()

    def verify(
        self,
        url: str,
        excerpt: str,
        crawled_pages: List[ParsedPage],
    ) -> bool:
        """
        Verify that excerpt is a contiguous substring of the visible text
        of the ParsedPage identified by url.
        """
        if not url or not excerpt:
            return False

        # Locate the selected ParsedPage
        target_page: Optional[ParsedPage] = None
        for p in crawled_pages:
            if p.url == url or (p.response and p.response.final_url == url):
                target_page = p
                break

        if not target_page:
            logger.warning("GroundingVerifier: Target page %s not found in crawled pages.", url)
            return False

        # Extract visible text using the deterministic extraction logic
        visible_text = self.extractor.extract_full_visible_text(target_page)

        # Check contiguous substring
        if excerpt in visible_text:
            return True

        logger.warning(
            "GroundingVerifier: Excerpt is not a contiguous substring of page visible text. URL: %s",
            url,
        )
        return False
