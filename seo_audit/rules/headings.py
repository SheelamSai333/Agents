"""
Rule auditing heading tags (H1 presence, multiple H1s, hierarchy skips, empty headings).
"""

from typing import List
from seo_audit.config import AuditConfig
from seo_audit.evidence import format_heading_evidence, truncate_snippet
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class HeadingsRule(BaseRule):
    """Audits headings structure, hierarchy, and content."""

    name = "headings"
    description = "Checks H1 presence, multiple H1s, heading order/hierarchy skips, and empty headings."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        h1_tags = [h for h in page.headings if h.level == 1]
        h1_snippets = [h.raw_html for h in h1_tags]

        # 1. Missing H1
        if len(h1_tags) == 0:
            findings.append(
                SEOFinding(
                    metric="missing_h1",
                    page=page.url,
                    severity=get_severity("missing_h1"),
                    evidence=format_heading_evidence(1, 0, []),
                    suggested_fix="Add a single, descriptive <h1> element representing the main topic of the page.",
                )
            )

        # 2. Multiple H1s
        elif len(h1_tags) > 1:
            findings.append(
                SEOFinding(
                    metric="multiple_h1",
                    page=page.url,
                    severity=get_severity("multiple_h1"),
                    evidence=format_heading_evidence(1, len(h1_tags), h1_snippets),
                    suggested_fix="Structure the page with exactly one primary <h1> and use <h2>/<h3> for subsections.",
                )
            )

        # 3. Empty Headings (H1 to H6)
        empty_headings = [h for h in page.headings if not h.text.strip()]
        if empty_headings:
            snippets = [truncate_snippet(h.raw_html, 60) for h in empty_headings]
            count = len(empty_headings)
            samples = ", ".join(f"'{s}'" for s in snippets[:3])
            suffix = f" (and {count - 3} more)" if count > 3 else ""
            findings.append(
                SEOFinding(
                    metric="empty_heading",
                    page=page.url,
                    severity=get_severity("empty_heading"),
                    evidence=f"Found {count} empty heading tag(s) with no text content: {samples}{suffix}.",
                    suggested_fix="Provide descriptive heading text or remove empty heading tags from the markup.",
                )
            )

        # 4. Heading Hierarchy Skips (e.g. H1 followed by H3 without an intervening H2)
        # We track the highest level encountered so far or the previous heading level
        prev_level = 0
        skipped_findings = []
        for h in page.headings:
            if prev_level > 0 and h.level > prev_level + 1:
                skipped_findings.append((prev_level, h.level, h.raw_html))
            prev_level = h.level

        if skipped_findings:
            prev_lvl, curr_lvl, snippet = skipped_findings[0]
            findings.append(
                SEOFinding(
                    metric="heading_hierarchy_skipped",
                    page=page.url,
                    severity=get_severity("heading_hierarchy_skipped"),
                    evidence=(
                        f"Heading hierarchy skips from <h{prev_lvl}> to <h{curr_lvl}> "
                        f"without an intervening <h{prev_lvl + 1}>: '{truncate_snippet(snippet, 80)}'."
                    ),
                    suggested_fix=f"Maintain sequential heading levels; insert an <h{prev_lvl + 1}> or change the heading tag.",
                )
            )

        return findings
