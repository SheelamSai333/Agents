"""
Rule auditing canonical URL implementation and conflicts.
"""

from typing import List
from urllib.parse import urlparse
from seo_audit.config import AuditConfig
from seo_audit.evidence import format_canonical_evidence, truncate_snippet
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity
from seo_audit.url_normalizer import URLNormalizer


class CanonicalRule(BaseRule):
    """Audits <link rel="canonical"> tags for existence, syntax, and conflicts."""

    name = "canonical"
    description = "Checks canonical tag presence, multiple canonical conflicts, and relative/mismatched targets."

    def __init__(self, normalizer: URLNormalizer = None):
        self.normalizer = normalizer or URLNormalizer()

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        # 1. Missing canonical tag
        if not page.canonical_urls:
            findings.append(
                SEOFinding(
                    metric="missing_canonical",
                    page=page.url,
                    severity=get_severity("missing_canonical"),
                    evidence=format_canonical_evidence([], []),
                    suggested_fix="Add a self-referential or authoritative <link rel=\"canonical\" href=\"...\"> in <head> to prevent duplicate content issues.",
                )
            )
            return findings

        # 2. Multiple canonical tags
        if len(page.canonical_urls) > 1:
            findings.append(
                SEOFinding(
                    metric="multiple_canonical",
                    page=page.url,
                    severity=get_severity("multiple_canonical"),
                    evidence=format_canonical_evidence(page.canonical_urls, page.canonical_raw_htmls),
                    suggested_fix="Ensure only one canonical tag is defined per page to avoid confusing search engines.",
                )
            )

        canonical_url = page.canonical_urls[0]
        canonical_raw = page.canonical_raw_htmls[0] if page.canonical_raw_htmls else ""

        # 3. Relative canonical tag
        # Check raw tag href attribute
        if 'href="/' in canonical_raw or ('href="' in canonical_raw and not ('href="http://' in canonical_raw or 'href="https://' in canonical_raw)):
            findings.append(
                SEOFinding(
                    metric="relative_canonical",
                    page=page.url,
                    severity=get_severity("relative_canonical"),
                    evidence=f"Canonical tag uses a relative URL: '{truncate_snippet(canonical_raw, 80)}'.",
                    suggested_fix="Use an absolute URL (including https:// and domain) in the canonical link element.",
                )
            )

        # 4. Canonical pointing to different domain
        if not self.normalizer.is_same_domain(page.url, canonical_url):
            findings.append(
                SEOFinding(
                    metric="canonical_mismatch",
                    page=page.url,
                    severity=get_severity("canonical_mismatch"),
                    evidence=(
                        f"Canonical URL '{canonical_url}' points to an external domain "
                        f"differing from current page domain '{urlparse(page.url).netloc}'."
                    ),
                    suggested_fix="Verify whether cross-domain canonicalization is intentional. If not, update to point to the current site.",
                )
            )

        return findings
