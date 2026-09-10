"""
Configuration definitions for the SEO Audit Agent.
"""

from dataclasses import dataclass, field
from typing import Set


@dataclass
class AuditConfig:
    """Settings controlling crawler behavior and SEO audit rules."""

    # Target URL
    start_url: str = ""

    # Crawl limits & politeness
    max_pages: int = 25
    max_depth: int = 3
    timeout: float = 15.0
    delay: float = 0.1  # seconds between requests to avoid overloading
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    respect_robots_txt: bool = True
    verify_ssl: bool = True

    # Output options
    output_file: str = "outputs/audit.json"
    summary_file: str = "outputs/audit_summary.json"

    # Link & asset verification
    check_broken_links: bool = True
    check_broken_images: bool = True
    max_asset_checks_per_page: int = 15

    # Thresholds for SEO checks
    min_title_length: int = 30
    max_title_length: int = 60
    min_meta_desc_length: int = 70
    max_meta_desc_length: int = 160
    min_word_count: int = 200

    # Tracking query parameters to strip during normalization
    tracking_params: Set[str] = field(
        default_factory=lambda: {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "gclid",
            "fbclid",
            "msclkid",
            "mc_eid",
            "_ga",
            "_gl",
            "ref",
            "source",
        }
    )
