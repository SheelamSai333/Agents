"""
Rule checking HTTP response codes, redirect chains, and loop conditions.
"""

from typing import List
from seo_audit.config import AuditConfig
from seo_audit.models import ParsedPage, SEOFinding
from seo_audit.rules.base import BaseRule
from seo_audit.severity import get_severity


class HttpStatusRule(BaseRule):
    """Audits HTTP status codes and redirect chains."""

    name = "http_status"
    description = "Checks HTTP response status codes and redirect behavior."

    def check_page(self, page: ParsedPage, config: AuditConfig) -> List[SEOFinding]:
        findings: List[SEOFinding] = []
        resp = page.response
        # 0. Connection / Timeout Errors
        if resp.status_code == 0 or (resp.error and not resp.is_client_error and not resp.is_server_error):
            findings.append(
                SEOFinding(
                    metric="network_connection_error",
                    page=resp.requested_url,
                    severity=get_severity("network_connection_error"),
                    evidence=f"Request failed with network/connection error: '{resp.error or 'Failed to establish connection'}'.",
                    suggested_fix="Verify server availability, domain DNS records, and ensure firewall/CDN rules permit crawler requests.",
                )
            )

        # 1. Server Errors (5xx)
        elif resp.is_server_error:
            findings.append(
                SEOFinding(
                    metric="http_server_error",
                    page=resp.requested_url,
                    severity=get_severity("http_server_error"),
                    evidence=f"Server returned HTTP status {resp.status_code} ({resp.error or 'Internal Server Error'}).",
                    suggested_fix="Investigate backend logs and resolve the server-side error causing the 5xx response.",
                )
            )

        # 2. Client Errors (4xx)
        elif resp.is_client_error:
            findings.append(
                SEOFinding(
                    metric="http_client_error",
                    page=resp.requested_url,
                    severity=get_severity("http_client_error"),
                    evidence=f"Client request returned HTTP status {resp.status_code} ({resp.error or 'Not Found'}).",
                    suggested_fix="Ensure the URL exists or return a proper 301 redirect to the updated location.",
                )
            )

        # 3. Redirect chains (> 1 hop)
        if len(resp.redirect_chain) > 1:
            chain_str = " -> ".join(resp.redirect_chain + [resp.final_url])
            findings.append(
                SEOFinding(
                    metric="redirect_chain_excessive",
                    page=resp.requested_url,
                    severity=get_severity("redirect_chain_excessive"),
                    evidence=f"Redirect chain contains {len(resp.redirect_chain)} hops: {chain_str}.",
                    suggested_fix="Update internal links and server redirects to point directly to the destination URL (single hop 301).",
                )
            )

        # 4. Check for temporary redirect on crawled pages
        # If the requested URL was redirected using 302 or 307
        if resp.redirect_chain and resp.status_code in (302, 307):
            findings.append(
                SEOFinding(
                    metric="redirect_temporary",
                    page=resp.requested_url,
                    severity=get_severity("redirect_temporary"),
                    evidence=f"Page returned temporary redirect HTTP {resp.status_code} to '{resp.final_url}'.",
                    suggested_fix="Use HTTP 301 Moved Permanently for permanent URL migrations to pass link equity.",
                )
            )

        return findings
