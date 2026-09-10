"""
Rule auditing internal hyperlinks, anchor text, and broken internal links.
"""

from typing import Dict, List
from seo_audit.config import AuditConfig
from seo_audit.evidence import format_broken_link_evidence, truncate_snippet
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity
from seo_audit.url_normalizer import URLNormalizer


class LinksRule(BaseRule):
    """Audits internal links for broken destinations, missing hrefs, and descriptive anchor text."""

    name = "links"
    description = "Checks internal links for 404/5xx errors, empty anchor text, and missing href attributes."

    def __init__(self, normalizer: URLNormalizer = None):
        self.normalizer = normalizer or URLNormalizer()

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        # Check for empty anchor text or missing href
        empty_anchors = []
        for link in page.links:
            # Missing or empty href
            if not link.href:
                findings.append(
                    SEOFinding(
                        metric="missing_href",
                        page=page.url,
                        severity=get_severity("missing_href"),
                        evidence=f"Anchor element is missing an 'href' attribute: '{truncate_snippet(link.raw_html, 70)}'.",
                        suggested_fix="Add a valid destination URL to the 'href' attribute or convert to a button element.",
                    )
                )
            elif link.is_internal and not link.is_fragment_only and not link.text:
                empty_anchors.append(link.raw_html)

        if empty_anchors:
            samples = ", ".join(f"'{truncate_snippet(a, 60)}'" for a in empty_anchors[:3])
            count = len(empty_anchors)
            suffix = f" (and {count - 3} more)" if count > 3 else ""
            findings.append(
                SEOFinding(
                    metric="empty_anchor_text",
                    page=page.url,
                    severity=get_severity("empty_anchor_text"),
                    evidence=f"Found {count} internal link(s) with empty anchor text: {samples}{suffix}.",
                    suggested_fix="Provide descriptive anchor text or an 'aria-label' describing the destination page.",
                )
            )

        return findings

    def check_site(self, pages: List[ParsedPage], config: AuditConfig) -> List[SEOFinding]:
        """Cross-check internal links against crawled page status codes to flag broken links."""
        findings: List[SEOFinding] = []

        # Map normalized URLs to their HTTP status code
        status_map: Dict[str, int] = {}
        for p in pages:
            norm = self.normalizer.normalize(p.url)
            status_map[norm] = p.response.status_code
            if p.response.requested_url:
                norm_req = self.normalizer.normalize(p.response.requested_url)
                status_map[norm_req] = p.response.status_code

        for p in pages:
            if not p.response.is_success:
                continue

            for link in p.links:
                if not link.is_internal or not link.resolved_url:
                    continue

                norm_target = self.normalizer.normalize(link.resolved_url)
                target_status = status_map.get(norm_target)

                if target_status and target_status >= 400:
                    findings.append(
                        SEOFinding(
                            metric="broken_internal_link",
                            page=p.url,
                            severity=get_severity("broken_internal_link"),
                            evidence=format_broken_link_evidence(link.href, link.resolved_url, target_status, link.raw_html),
                            suggested_fix=f"Update or remove the broken internal link pointing to HTTP {target_status} page.",
                        )
                    )

        return findings
