"""
Data models representing crawled pages, parsed markup, findings, and audit reports.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

SeverityLevel = Literal["critical", "high", "medium", "low", "info"]


@dataclass
class SEOFinding:
    """Represents an individual SEO issue or observation backed by evidence."""

    metric: str
    page: str
    severity: SeverityLevel
    evidence: str
    suggested_fix: str

    def to_dict(self) -> Dict[str, str]:
        """Convert finding to standard JSON output dictionary."""
        return {
            "metric": self.metric,
            "page": self.page,
            "severity": self.severity,
            "evidence": self.evidence,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class HeadingItem:
    """Heading element found in the document."""

    level: int  # 1 to 6
    text: str
    raw_html: str
    order: int


@dataclass
class ImageItem:
    """Image element found in the document."""

    src: str
    resolved_url: str
    alt: Optional[str]  # None if alt attribute is missing entirely, "" if alt=""
    has_alt: bool
    raw_html: str
    is_data_uri: bool = False


@dataclass
class LinkItem:
    """Hyperlink element found in the document."""

    href: str
    resolved_url: str
    text: str
    is_internal: bool
    is_fragment_only: bool
    rel: List[str]
    raw_html: str


@dataclass
class PageResponse:
    """Network response for a crawled page."""

    requested_url: str
    final_url: str
    status_code: int
    headers: Dict[str, str]
    content: str  # HTML or text
    redirect_chain: List[str] = field(default_factory=list)
    depth: int = 0
    elapsed_seconds: float = 0.0
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").lower()


@dataclass
class ParsedPage:
    """Parsed representation of a page's DOM, metadata, and assets."""

    url: str
    response: PageResponse
    title: Optional[str] = None
    title_raw_html: Optional[str] = None
    meta_description: Optional[str] = None
    meta_description_raw_html: Optional[str] = None
    canonical_urls: List[str] = field(default_factory=list)
    canonical_raw_htmls: List[str] = field(default_factory=list)
    robots_meta: List[str] = field(default_factory=list)
    x_robots_tag: List[str] = field(default_factory=list)
    viewport: Optional[str] = None
    html_lang: Optional[str] = None
    headings: List[HeadingItem] = field(default_factory=list)
    images: List[ImageItem] = field(default_factory=list)
    links: List[LinkItem] = field(default_factory=list)
    open_graph: Dict[str, str] = field(default_factory=dict)
    twitter_cards: Dict[str, str] = field(default_factory=dict)
    visible_word_count: int = 0
    visible_text_snippet: str = ""
    insecure_subresources: List[str] = field(default_factory=list)
    is_disallowed_by_robots_txt: bool = False
    robots_txt_directive: Optional[str] = None


@dataclass
class CrawlSummary:
    """Summary metrics of crawl execution."""

    start_url: str
    crawled_count: int
    duration_seconds: float
    status_breakdown: Dict[int, int] = field(default_factory=dict)
