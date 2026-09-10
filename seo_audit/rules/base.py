"""
Base class and registry for SEO audit rules.
"""

from abc import ABC
from typing import List, Optional
from seo_audit.config import AuditConfig
from seo_audit.models import ParsedPage, SEOFinding


class BaseRule(ABC):
    """Abstract base class for individual SEO audit rules."""

    # Unique identifier for the rule
    name: str = "base_rule"
    description: str = "Base SEO Rule"

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        """
        Evaluate a single page and return any findings.
        Override in rules that operate on individual pages.
        """
        return []

    def check_site(self, pages: List[ParsedPage], config: AuditConfig) -> List[SEOFinding]:
        """
        Evaluate the aggregate set of crawled pages (e.g. cross-page duplicates, broken links).
        Override in rules that require whole-site context.
        """
        return []
