"""
URL normalization, domain validation, loop detection, and link resolution.
"""

import re
from typing import Optional, Set
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlparse, urlunparse

NON_HTML_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".bmp",
    ".tiff",
    ".mp3",
    ".wav",
    ".ogg",
    ".mp4",
    ".webm",
    ".avi",
    ".mov",
    ".mkv",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".csv",
}

DEFAULT_TRACKING_PARAMS = {
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


class URLNormalizer:
    """Provides methods for cleaning, canonicalizing, and scoping URLs."""

    def __init__(self, tracking_params: Optional[Set[str]] = None):
        self.tracking_params = tracking_params or DEFAULT_TRACKING_PARAMS

    @staticmethod
    def ensure_scheme(url: str) -> str:
        """Ensure URL has an http or https scheme. Defaults to https."""
        url = url.strip()
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return f"https://{url}"
        return url

    def normalize(self, url: str) -> str:
        """
        Normalize a URL for deduplication and consistent crawling:
        - Lowercases scheme and host.
        - Strips URL fragments (#hash).
        - Strips tracking parameters and sorts remaining query parameters.
        - Removes default ports (:80, :443).
        - Removes duplicate consecutive slashes in the path.
        - Ensures root domain has a trailing slash (https://site.com -> https://site.com/).
        """
        if not url:
            return ""

        url = self.ensure_scheme(url)
        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Normalize path
        path = parsed.path
        if not path:
            path = "/"
        else:
            # Replace duplicate slashes except at start
            path = re.sub(r"/+", "/", path)

        # Process query params: strip tracking params & sort
        query = ""
        if parsed.query:
            filtered_params = []
            for k, v in parse_qsl(parsed.query, keep_blank_values=True):
                if k.lower() not in self.tracking_params:
                    filtered_params.append((k, v))
            if filtered_params:
                filtered_params.sort(key=lambda item: item[0])
                query = urlencode(filtered_params)

        # Fragments are discarded for crawling
        fragment = ""

        normalized = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
        return normalized

    @staticmethod
    def resolve_url(base_url: str, href: str) -> Optional[str]:
        """
        Resolve a relative or protocol-relative href against base_url.
        Returns None if href is an ignored pseudo-protocol (javascript:, mailto:, tel:).
        """
        if not href:
            return None

        href = href.strip()
        lower_href = href.lower()

        # Ignore common non-HTTP links
        if lower_href.startswith(("javascript:", "mailto:", "tel:", "data:", "sms:", "#")):
            return None

        try:
            resolved = urljoin(base_url, href)
            parsed = urlparse(resolved)
            if parsed.scheme.lower() in ("http", "https"):
                return resolved
            return None
        except Exception:
            return None

    @staticmethod
    def is_same_domain(base_url: str, target_url: str) -> bool:
        """
        Check if target_url belongs to the same domain/hostname as base_url.
        Allows exact host match or www/non-www variant.
        """
        base_host = urlparse(base_url).netloc.lower().split(":")[0]
        target_host = urlparse(target_url).netloc.lower().split(":")[0]

        if not base_host or not target_host:
            return False

        if base_host == target_host:
            return True

        # Handle www.example.com and example.com equivalence
        base_stripped = base_host[4:] if base_host.startswith("www.") else base_host
        target_stripped = target_host[4:] if target_host.startswith("www.") else target_host
        return base_stripped == target_stripped

    @staticmethod
    def is_html_target(url: str) -> bool:
        """
        Check if URL likely points to an HTML document rather than a binary asset.
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        for ext in NON_HTML_EXTENSIONS:
            if path.endswith(ext):
                return False
        return True

    @staticmethod
    def detect_path_loop(url: str) -> bool:
        """
        Detect cyclical/infinite path loops, e.g.:
        /category/item/category/item/category/item
        or consecutive repeated segments.
        """
        parsed = urlparse(url)
        segments = [s.lower() for s in parsed.path.split("/") if s]

        if len(segments) > 8:
            return True

        # Check if any single segment repeats more than 3 times
        for seg in set(segments):
            if segments.count(seg) >= 3:
                return True

        # Check for 2-segment pattern repetition (A/B/A/B)
        if len(segments) >= 4:
            for i in range(len(segments) - 3):
                if (segments[i] == segments[i + 2]) and (segments[i + 1] == segments[i + 3]):
                    return True

        return False
