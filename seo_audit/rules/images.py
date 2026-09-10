"""
Rule auditing image alt attributes and broken images.
"""

from typing import List
import httpx
from seo_audit.config import AuditConfig
from seo_audit.evidence import format_image_alt_evidence, truncate_snippet
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class ImagesRule(BaseRule):
    """Audits image tags for alt attributes and broken sources."""

    name = "images"
    description = "Checks for missing alt attributes and broken image URLs."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []

        if not page.response.is_success or not page.response.content:
            return findings

        # 1. Missing alt attributes (alt attribute is completely absent)
        missing_alt_tags = [img.raw_html for img in page.images if not img.has_alt]
        if missing_alt_tags:
            findings.append(
                SEOFinding(
                    metric="missing_image_alt",
                    page=page.url,
                    severity=get_severity("missing_image_alt"),
                    evidence=format_image_alt_evidence(missing_alt_tags),
                    suggested_fix="Add descriptive 'alt' text to images for search indexing and screen reader accessibility.",
                )
            )

        # 2. Check for broken images (sample up to max_asset_checks_per_page)
        if config.check_broken_images:
            images_to_check = [img for img in page.images if img.resolved_url and not img.is_data_uri]
            checked_count = 0
            for img in images_to_check[: config.max_asset_checks_per_page]:
                # Don't check non-HTTP URLs
                if not img.resolved_url.lower().startswith(("http://", "https://")):
                    continue

                checked_count += 1
                try:
                    # Quick HEAD request with short timeout
                    resp = httpx.head(
                        img.resolved_url,
                        headers={"User-Agent": config.user_agent},
                        timeout=5.0,
                        follow_redirects=True,
                    )
                    # If server doesn't allow HEAD, fallback to GET
                    if resp.status_code == 405:
                        resp = httpx.get(
                            img.resolved_url,
                            headers={"User-Agent": config.user_agent},
                            timeout=5.0,
                            follow_redirects=True,
                        )

                    if resp.status_code >= 400:
                        findings.append(
                            SEOFinding(
                                metric="broken_image",
                                page=page.url,
                                severity=get_severity("broken_image"),
                                evidence=(
                                    f"Image '{truncate_snippet(img.raw_html, 80)}' with source "
                                    f"'{img.resolved_url}' returned HTTP {resp.status_code}."
                                ),
                                suggested_fix="Fix or remove the broken image source URL.",
                            )
                        )
                except Exception as e:
                    # Log or record if unreachable
                    pass

        return findings
