"""
Rule auditing robots meta directives (noindex, nofollow, conflicting directives).
"""

from typing import List
from seo_audit.config import AuditConfig
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class RobotsMetaRule(BaseRule):
    """Audits robots meta tags and X-Robots-Tag HTTP headers."""

    name = "robots_meta"
    description = "Checks for indexation blockers (noindex), nofollow directives, and conflicting rules."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success:
            return findings

        # 1. HTML <meta name="robots">
        for raw_directive in page.robots_meta:
            lower = raw_directive.lower()
            tokens = [t.strip() for t in lower.split(",")]

            # Conflicting directives
            if "noindex" in tokens and "index" in tokens:
                findings.append(
                    SEOFinding(
                        metric="robots_conflicting",
                        page=page.url,
                        severity=get_severity("robots_conflicting"),
                        evidence=f"Conflicting robots directives found in '<meta name=\"robots\" content=\"{raw_directive}\">': specifies both 'index' and 'noindex'.",
                        suggested_fix="Remove the conflicting directive and specify explicitly whether search engines should index the page.",
                    )
                )

            # Noindex directive
            if "noindex" in tokens:
                findings.append(
                    SEOFinding(
                        metric="robots_noindex",
                        page=page.url,
                        severity=get_severity("robots_noindex"),
                        evidence=f"<meta name=\"robots\" content=\"{raw_directive}\"> contains 'noindex', preventing search engines from indexing this page.",
                        suggested_fix="Remove the 'noindex' directive from the robots meta tag if this page should appear in search results.",
                    )
                )

        # 2. X-Robots-Tag HTTP response headers
        for x_robot in page.x_robots_tag:
            lower = x_robot.lower()
            if "noindex" in lower:
                findings.append(
                    SEOFinding(
                        metric="x_robots_noindex",
                        page=page.url,
                        severity=get_severity("x_robots_noindex"),
                        evidence=f"HTTP response header 'X-Robots-Tag: {x_robot}' contains 'noindex', preventing indexation.",
                        suggested_fix="Remove the 'noindex' directive from the server HTTP response header if the page is intended for search indexing.",
                    )
                )

        # 3. robots.txt Disallowed
        if page.is_disallowed_by_robots_txt:
            findings.append(
                SEOFinding(
                    metric="robots_txt_disallowed",
                    page=page.url,
                    severity=get_severity("robots_txt_disallowed"),
                    evidence=f"Page is disallowed from crawling and indexing by a directive in robots.txt ({page.robots_txt_directive or 'Disallow'}).",
                    suggested_fix="Update robots.txt if search engine crawlers should be permitted to crawl and index this URL.",
                )
            )

        return findings
