"""
Rule auditing page title presence, length, and cross-page duplicates.
"""

from collections import defaultdict
from typing import Dict, List
from seo_audit.config import AuditConfig
from seo_audit.evidence import format_duplicate_evidence, format_title_evidence
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class TitleRule(BaseRule):
    """Audits <title> tags for presence, length guidelines, and uniqueness."""

    name = "title"
    description = "Checks page title presence, character length, and cross-page duplicates."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        # Only audit successful HTML pages
        if not page.response.is_success or not page.response.content:
            return findings

        # 1. Missing or empty title
        if not page.title:
            findings.append(
                SEOFinding(
                    metric="missing_title",
                    page=page.url,
                    severity=get_severity("missing_title"),
                    evidence=format_title_evidence(page.title, page.title_raw_html),
                    suggested_fix="Add a unique, descriptive <title> tag inside the <head> element between 30 and 60 characters.",
                )
            )
            return findings

        title_len = len(page.title)

        # 2. Title too short
        if title_len < config.min_title_length:
            findings.append(
                SEOFinding(
                    metric="title_too_short",
                    page=page.url,
                    severity=get_severity("title_too_short"),
                    evidence=f"Title has only {title_len} characters: '{page.title}' (recommended minimum is {config.min_title_length}).",
                    suggested_fix=f"Expand the title to at least {config.min_title_length} characters to provide richer context for search engines and users.",
                )
            )

        # 3. Title too long
        elif title_len > config.max_title_length:
            findings.append(
                SEOFinding(
                    metric="title_too_long",
                    page=page.url,
                    severity=get_severity("title_too_long"),
                    evidence=f"Title contains {title_len} characters: '{page.title}' (exceeds recommended {config.max_title_length} characters limit).",
                    suggested_fix=f"Shorten the title to under {config.max_title_length} characters to prevent truncation in Google SERPs.",
                )
            )

        return findings

    def check_site(self, pages: List[ParsedPage], config: AuditConfig) -> List[SEOFinding]:
        """Check for identical page titles across multiple URLs."""
        findings: List[SEOFinding] = []
        titles_map: Dict[str, List[str]] = defaultdict(list)

        for page in pages:
            if page.response.is_success and page.title:
                norm_title = page.title.strip().lower()
                titles_map[norm_title].append(page.url)

        for title_str, url_list in titles_map.items():
            if len(url_list) > 1:
                evidence = format_duplicate_evidence("title", title_str, url_list)
                for page_url in url_list:
                    findings.append(
                        SEOFinding(
                            metric="duplicate_title",
                            page=page_url,
                            severity=get_severity("duplicate_title"),
                            evidence=evidence,
                            suggested_fix="Ensure each page has a unique, distinct title tag reflecting its specific topic and purpose.",
                        )
                    )

        return findings
