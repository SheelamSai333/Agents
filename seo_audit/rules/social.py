"""
Rule auditing social media metadata (Open Graph and Twitter Cards).
"""

from typing import List
from seo_audit.config import AuditConfig
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity

ESSENTIAL_OG_TAGS = ["og:title", "og:description", "og:image", "og:url"]


class SocialMetadataRule(BaseRule):
    """Audits Open Graph and social sharing metadata tags."""

    name = "social_metadata"
    description = "Checks for presence and completeness of Open Graph (og:) metadata tags."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        missing_og = [tag for tag in ESSENTIAL_OG_TAGS if tag not in page.open_graph]

        if missing_og:
            tags_list = ", ".join(f"'{t}'" for t in missing_og)
            findings.append(
                SEOFinding(
                    metric="missing_open_graph",
                    page=page.url,
                    severity=get_severity("missing_open_graph"),
                    evidence=f"Missing essential Open Graph metadata tag(s) in <head>: {tags_list}.",
                    suggested_fix="Add Open Graph meta tags (og:title, og:description, og:image, og:url) to enhance social sharing previews.",
                )
            )

        return findings
