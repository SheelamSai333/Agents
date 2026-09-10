"""Prioritize pages likely to contain NAP information."""

from typing import Dict, List, Tuple
from urllib.parse import urlparse

from seo_audit.models import ParsedPage


class ContactPageDetector:
    """Ranks crawled pages by likelihood of containing business NAP data."""

    HIGH_PRIORITY_TERMS = (
        "contact",
        "about",
        "location",
        "locations",
        "store",
        "stores",
        "find-us",
        "findus",
        "reach-us",
        "reachus",
        "branches",
        "offices",
    )

    def detect(
        self, pages: List[ParsedPage]
    ) -> Tuple[List[ParsedPage], Dict[str, float]]:
        """Return pages sorted by NAP relevance and their priority weights."""
        scored = []

        for page in pages:
            url = page.url.lower()
            path = urlparse(url).path.lower().rstrip("/")

            score = 0.4

            if path in ("", "/"):
                score = max(score, 1.0)

            if any(term in path for term in self.HIGH_PRIORITY_TERMS):
                score = max(score, 0.9)

            title = (page.title or "").lower()

            heading_text = " ".join(
                heading.text.lower()
                for heading in page.headings
                if heading.text
            )

            combined = f"{title} {heading_text}"

            if any(term.replace("-", " ") in combined for term in self.HIGH_PRIORITY_TERMS):
                score = max(score, 0.85)

            scored.append((score, page))

        scored.sort(key=lambda item: item[0], reverse=True)

        priorities = {
            page.url: score
            for score, page in scored
        }

        return [page for score, page in scored], priorities
