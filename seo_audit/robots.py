"""
robots.txt parsing and compliance checker.
"""

import logging
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import httpx

logger = logging.getLogger(__name__)

STANDARD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}


class RobotsPolicy:
    """Manages robots.txt retrieval and permission checks for crawled domains."""

    def __init__(self, user_agent: str, enabled: bool = True, timeout: float = 10.0):
        self.user_agent = user_agent
        self.enabled = enabled
        self.timeout = timeout
        self._parsers: dict[str, Optional[RobotFileParser]] = {}
        self._raw_content: dict[str, str] = {}

    def _get_robots_url(self, target_url: str) -> str:
        parsed = urlparse(target_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return urljoin(base, "/robots.txt")

    def fetch_policy(self, target_url: str, client: Optional[httpx.Client] = None) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt for the given target_url's domain."""
        if not self.enabled:
            return None

        parsed = urlparse(target_url)
        origin = f"{parsed.scheme}://{parsed.netloc}".lower()

        if origin in self._parsers:
            return self._parsers[origin]

        robots_url = self._get_robots_url(target_url)
        rfp = RobotFileParser()

        # Try fetching robots.txt with client (which carries full session headers)
        try:
            if client:
                resp = client.get(robots_url, timeout=self.timeout)
            else:
                resp = httpx.get(
                    robots_url,
                    headers=STANDARD_HEADERS,
                    follow_redirects=True,
                    timeout=self.timeout,
                )

            if resp.status_code == 200:
                content = resp.text
                self._raw_content[origin] = content
                rfp.parse(content.splitlines())
                self._parsers[origin] = rfp
                logger.info(f"Loaded robots.txt from {robots_url}")
                return rfp
            elif resp.status_code in (404, 410):
                logger.info(f"No robots.txt found (HTTP {resp.status_code}) at {robots_url}; crawling allowed.")
                self._parsers[origin] = None
                return None
            else:
                logger.info(f"robots.txt returned HTTP {resp.status_code} at {robots_url}.")
        except Exception as e:
            logger.warning(f"Primary attempt to fetch robots.txt from {robots_url} failed: {e}")

        # Fallback attempt with clean standalone client and browser headers
        try:
            with httpx.Client(
                headers=STANDARD_HEADERS,
                timeout=max(self.timeout, 10.0),
                follow_redirects=True,
            ) as fallback_client:
                resp = fallback_client.get(robots_url)
                if resp.status_code == 200:
                    content = resp.text
                    self._raw_content[origin] = content
                    rfp.parse(content.splitlines())
                    self._parsers[origin] = rfp
                    logger.info(f"Successfully loaded robots.txt via fallback from {robots_url}")
                    return rfp
                else:
                    self._parsers[origin] = None
        except Exception as e:
            logger.warning(f"Could not reach {robots_url}: {e}. Proceeding with crawl.")
            self._parsers[origin] = None

        return self._parsers[origin]

    def can_fetch(self, url: str, client: Optional[httpx.Client] = None) -> bool:
        """Check if the given URL is allowed to be crawled according to robots.txt."""
        if not self.enabled:
            return True

        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}".lower()

        rfp = self._parsers.get(origin)
        if origin not in self._parsers:
            rfp = self.fetch_policy(url, client=client)

        if rfp is None:
            return True

        try:
            # Check with specific agent first, then check general policy
            return rfp.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def get_raw_content(self, target_url: str) -> Optional[str]:
        parsed = urlparse(target_url)
        origin = f"{parsed.scheme}://{parsed.netloc}".lower()
        return self._raw_content.get(origin)
