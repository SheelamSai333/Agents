"""
Rule auditing visible content depth and thin content issues.
"""

from typing import List
from seo_audit.config import AuditConfig
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class ContentRule(BaseRule):
    """Audits visible text content volume and thin page issues."""

    name = "content"
    description = "Checks for thin or empty visible text content on crawled pages."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        # 1. Empty body/content
        if page.visible_word_count == 0:
            findings.append(
                SEOFinding(
                    metric="empty_content",
                    page=page.url,
                    severity=get_severity("empty_content"),
                    evidence="No visible body text content was found on this page.",
                    suggested_fix="Ensure the page delivers substantive, indexable text content to users and search crawlers.",
                )
            )

        # 2. Thin content
        elif page.visible_word_count < config.min_word_count:
            snippet_disp = f" Sample: '{page.visible_text_snippet}...'" if page.visible_text_snippet else ""
            findings.append(
                SEOFinding(
                    metric="thin_content",
                    page=page.url,
                    severity=get_severity("thin_content"),
                    evidence=(
                        f"Page contains only {page.visible_word_count} visible words "
                        f"(recommended minimum: {config.min_word_count} words).{snippet_disp}"
                    ),
                    suggested_fix=f"Expand the page content with detailed, helpful copy (at least {config.min_word_count} words) to avoid thin content flags.",
                )
            )

        return findings
