"""
SEO Rule Engine orchestrating single-page audits and cross-site aggregate checks.
"""

import logging
from typing import List, Optional
from seo_audit.config import AuditConfig
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules import get_default_rules
from seo_audit.rules.base import BaseRule

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}


class RuleEngine:
    """Orchestrates SEO rule evaluation across single pages and aggregate site crawl data."""

    def __init__(self, rules: Optional[List[BaseRule]] = None, config: Optional[AuditConfig] = None):
        self.rules = rules or get_default_rules()
        self.config = config or AuditConfig()

    def audit(self, pages: List[ParsedPage]) -> List[SEOFinding]:
        """
        Run the complete rule audit across all parsed pages:
        1. Single-page evaluation per page.
        2. Site-wide aggregate evaluation across all pages.
        3. Deduplication and deterministic severity sorting.
        """
        all_findings: List[SEOFinding] = []

        # 1. Single-page audits
        for page in pages:
            for rule in self.rules:
                try:
                    page_findings = rule.check_page(page, self.config)
                    all_findings.extend(page_findings)
                except Exception as e:
                    logger.error(f"Rule '{rule.name}' encountered error on page '{page.url}': {e}", exc_info=True)

        # 2. Site-wide audits (duplicate detection, broken link cross-checks)
        for rule in self.rules:
            try:
                site_findings = rule.check_site(pages, self.config)
                all_findings.extend(site_findings)
            except Exception as e:
                logger.error(f"Rule '{rule.name}' encountered error during site-wide audit: {e}", exc_info=True)

        # 3. Deduplicate findings based on (metric, page, evidence)
        seen = set()
        deduped: List[SEOFinding] = []
        for f in all_findings:
            key = (f.metric, f.page, f.evidence)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        # 4. Sort by severity order (critical first), then page, then metric
        deduped.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.page, item.metric))

        return deduped
