"""
Severity classification and rationale documentation for SEO findings.
"""

from typing import Dict
from seo_audit.models import SeverityLevel

# Severity level documentation and rationale
SEVERITY_RATIONALE: Dict[SeverityLevel, str] = {
    "critical": (
        "Issues that prevent search engine indexing altogether, break crawlability, "
        "or return fatal server/client errors (e.g. 5xx server errors, accidental noindex "
        "directives on key pages, complete absence of <title> tags)."
    ),
    "high": (
        "High-impact on-page deficiencies that substantially degrade search visibility, "
        "cause ranking penalties, or impair core user experience (e.g. missing H1, multiple H1s, "
        "duplicate titles across pages, broken internal links, mixed content over HTTPS, "
        "missing mobile viewport tags, or conflicting canonical tags)."
    ),
    "medium": (
        "Significant optimization gaps that reduce click-through rates, semantic clarity, "
        "or crawl efficiency (e.g. missing or duplicate meta descriptions, titles/descriptions "
        "exceeding or failing length limits, missing image alt attributes, broken images, "
        "skipped heading levels, or thin content)."
    ),
    "low": (
        "Minor technical improvements or accessibility enhancements that offer marginal "
        "SEO gains (e.g. missing HTML lang attributes, empty heading tags, relative canonical "
        "URLs, missing Open Graph tags, or non-descriptive anchor text like 'click here')."
    ),
    "info": (
        "Informational notices or confirmed positive best practices detected during the audit "
        "(e.g. clean 301 redirects, valid self-referential canonical tags, verified HTTPS enforcement, "
        "or properly configured robots.txt)."
    ),
}

# Default metric severity mapping
DEFAULT_METRIC_SEVERITY: Dict[str, SeverityLevel] = {
    # HTTP & Crawlability
    "http_server_error": "critical",
    "http_client_error": "critical",
    "network_connection_error": "critical",
    "redirect_chain_excessive": "medium",
    "redirect_temporary": "low",
    "redirect_loop": "critical",
    "robots_txt_disallowed": "high",
    # Title Tag
    "missing_title": "critical",
    "title_too_short": "medium",
    "title_too_long": "medium",
    "duplicate_title": "high",
    # Meta Description
    "missing_meta_description": "high",
    "meta_description_too_short": "medium",
    "meta_description_too_long": "medium",
    "duplicate_meta_description": "medium",
    # Headings
    "missing_h1": "high",
    "multiple_h1": "high",
    "heading_hierarchy_skipped": "medium",
    "empty_heading": "low",
    # Images
    "missing_image_alt": "medium",
    "broken_image": "high",
    # Canonical Tag
    "missing_canonical": "medium",
    "multiple_canonical": "high",
    "relative_canonical": "low",
    "canonical_mismatch": "high",
    # Indexation & Robots
    "robots_noindex": "critical",
    "robots_conflicting": "high",
    "x_robots_noindex": "critical",
    # Mobile & Localization
    "missing_viewport": "high",
    "missing_html_lang": "low",
    "invalid_html_lang": "low",
    # Links & Navigation
    "broken_internal_link": "high",
    "empty_anchor_text": "low",
    "missing_href": "low",
    # Security & HTTPS
    "insecure_http": "high",
    "mixed_content": "high",
    # Social & Semantic
    "missing_open_graph": "low",
    # Content Quality
    "thin_content": "medium",
    "empty_content": "high",
}


def get_severity(metric: str, override: SeverityLevel = None) -> SeverityLevel:
    """Retrieve severity level for a metric with optional override."""
    if override:
        return override
    return DEFAULT_METRIC_SEVERITY.get(metric, "medium")
