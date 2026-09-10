"""
Rule auditing meta description and viewport meta tags.
"""

from collections import defaultdict
from typing import Dict, List
from seo_audit.config import AuditConfig
from seo_audit.evidence import format_duplicate_evidence, format_meta_desc_evidence
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class MetaTagsRule(BaseRule):
    """Audits meta description and mobile viewport configuration."""

    name = "meta_tags"
    description = "Checks meta description presence/length, cross-page duplicates, and viewport configuration."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        # 1. Meta Description
        if not page.meta_description:
            findings.append(
                SEOFinding(
                    metric="missing_meta_description",
                    page=page.url,
                    severity=get_severity("missing_meta_description"),
                    evidence=format_meta_desc_evidence(page.meta_description, page.meta_description_raw_html),
                    suggested_fix="Add a compelling, unique meta description between 70 and 160 characters in the HTML <head>.",
                )
            )
        else:
            desc_len = len(page.meta_description)
            if desc_len < config.min_meta_desc_length:
                findings.append(
                    SEOFinding(
                        metric="meta_description_too_short",
                        page=page.url,
                        severity=get_severity("meta_description_too_short"),
                        evidence=f"Meta description contains only {desc_len} characters: '{page.meta_description}' (recommended minimum is {config.min_meta_desc_length}).",
                        suggested_fix=f"Expand the meta description to at least {config.min_meta_desc_length} characters to encourage click-throughs from SERPs.",
                    )
                )
            elif desc_len > config.max_meta_desc_length:
                findings.append(
                    SEOFinding(
                        metric="meta_description_too_long",
                        page=page.url,
                        severity=get_severity("meta_description_too_long"),
                        evidence=f"Meta description contains {desc_len} characters: '{page.meta_description}' (exceeds recommended {config.max_meta_desc_length} characters max).",
                        suggested_fix=f"Shorten the meta description to under {config.max_meta_desc_length} characters to prevent truncation in search snippets.",
                    )
                )

        # 2. Viewport Meta Tag
        if not page.viewport:
            findings.append(
                SEOFinding(
                    metric="missing_viewport",
                    page=page.url,
                    severity=get_severity("missing_viewport"),
                    evidence="No <meta name=\"viewport\"> tag was found in the HTML <head>.",
                    suggested_fix="Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> to ensure mobile-responsive rendering.",
                )
            )
        elif "width=device-width" not in page.viewport.lower():
            findings.append(
                SEOFinding(
                    metric="missing_viewport",
                    page=page.url,
                    severity=get_severity("missing_viewport"),
                    evidence=f"Viewport tag exists but is missing 'width=device-width': '<meta name=\"viewport\" content=\"{page.viewport}\">'.",
                    suggested_fix="Update the viewport meta tag to include 'width=device-width, initial-scale=1' for standard responsive design.",
                )
            )

        return findings

    def check_site(self, pages: List[ParsedPage], config: AuditConfig) -> List[SEOFinding]:
        """Check for duplicate meta descriptions across distinct URLs."""
        findings: List[SEOFinding] = []
        desc_map: Dict[str, List[str]] = defaultdict(list)

        for page in pages:
            if page.response.is_success and page.meta_description:
                norm_desc = page.meta_description.strip().lower()
                desc_map[norm_desc].append(page.url)

        for desc_str, url_list in desc_map.items():
            if len(url_list) > 1:
                evidence = format_duplicate_evidence("meta description", desc_str, url_list)
                for page_url in url_list:
                    findings.append(
                        SEOFinding(
                            metric="duplicate_meta_description",
                            page=page_url,
                            severity=get_severity("duplicate_meta_description"),
                            evidence=evidence,
                            suggested_fix="Create distinct, custom meta descriptions for each individual page instead of repeating boilerplates.",
                        )
                    )

        return findings
