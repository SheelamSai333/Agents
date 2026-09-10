"""
Data models for the Q3 Question-Answering Agent.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContentChunk:
    """A discrete semantic passage extracted from a page's DOM."""

    page_url: str
    text: str  # Exact rendered text as seen in DOM
    tag: str  # Tag type (p, li, h1-h6, td, blockquote, etc.)
    heading_hierarchy: List[str] = field(default_factory=list)  # Ancestor/preceding headings
    is_boilerplate: bool = False  # True if inside header, footer, nav, aside, cookie notice
    chunk_id: int = 0
    word_count: int = 0
    crawl_depth: int = 0

    def __post_init__(self):
        if not self.word_count:
            self.word_count = len(self.text.split())


@dataclass
class ScoredPassage:
    """A candidate passage scored against a query."""

    chunk: ContentChunk
    score: float
    matched_terms: List[str] = field(default_factory=list)
    has_phrase_match: bool = False
    heading_match_count: int = 0
    url_match_count: int = 0
    has_explanatory_predicate: bool = False
    is_oblique_mention: bool = False


@dataclass
class QAResponse:
    """The final answer structure returned by the QA agent."""

    query: str
    url: Optional[str]
    excerpt: Optional[str]
    confidence: float = 0.0
    debug_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Serialize according to exact assignment schema for answer.json."""
        return {
            "query": self.query,
            "url": self.url,
            "excerpt": self.excerpt,
        }
