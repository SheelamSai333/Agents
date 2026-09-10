"""
Rule auditing HTML lang attribute for internationalization and accessibility.
"""

from typing import List
from seo_audit.config import AuditConfig
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class LanguageRule(BaseRule):
    """Audits the <html> lang attribute."""

    name = "language"
    description = "Checks that the <html> tag specifies a valid lang attribute."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        # 1. Missing lang attribute
        if page.html_lang is None:
            findings.append(
                SEOFinding(
                    metric="missing_html_lang",
                    page=page.url,
                    severity=get_severity("missing_html_lang"),
                    evidence="The <html> element is missing the 'lang' attribute.",
                    suggested_fix="Declare the primary language on the <html> tag (e.g. <html lang=\"en\">).",
                )
            )

        # 2. Empty or whitespace-only lang attribute
        elif not page.html_lang.strip():
            findings.append(
                SEOFinding(
                    metric="invalid_html_lang",
                    page=page.url,
                    severity=get_severity("invalid_html_lang"),
                    evidence="The <html> element contains an empty 'lang=\"\"' attribute.",
                    suggested_fix="Specify a valid ISO language code in the 'lang' attribute (e.g. 'en', 'es', 'fr').",
                )
            )

        return findings
