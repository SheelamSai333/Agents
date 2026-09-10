"""
Rule auditing HTTPS usage and mixed content vulnerabilities.
"""

from typing import List
from urllib.parse import urlparse
from seo_audit.config import AuditConfig
from seo_audit.evidence import format_mixed_content_evidence
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class HttpsSecurityRule(BaseRule):
    """Audits page protocol (HTTPS enforcement) and insecure mixed content."""

    name = "https_security"
    description = "Checks that pages are served over HTTPS and free from insecure mixed HTTP subresources."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []
        parsed = urlparse(page.url)

        # 1. Page served over insecure HTTP
        if parsed.scheme.lower() == "http":
            findings.append(
                SEOFinding(
                    metric="insecure_http",
                    page=page.url,
                    severity=get_severity("insecure_http"),
                    evidence=f"Page is served over unencrypted HTTP protocol: '{page.url}'.",
                    suggested_fix="Configure an SSL/TLS certificate and permanently redirect (301) all HTTP traffic to HTTPS.",
                )
            )

        # 2. Mixed Content on HTTPS pages
        elif parsed.scheme.lower() == "https" and page.insecure_subresources:
            findings.append(
                SEOFinding(
                    metric="mixed_content",
                    page=page.url,
                    severity=get_severity("mixed_content"),
                    evidence=format_mixed_content_evidence(page.insecure_subresources),
                    suggested_fix="Update all subresource URLs (scripts, stylesheets, images) to use secure 'https://' or protocol-relative paths.",
                )
            )

        return findings
