"""
Data models for NAP Consistency Checker.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

NAPField = Literal["name", "address", "phone"]
NAPVerdict = Literal["consistent", "minor_formatting_difference", "genuine_mismatch", "not_found", "uncertain"]


@dataclass
class NAPOccurrence:
    """A single extracted NAP value with full source metadata."""

    field: NAPField
    raw_value: str
    normalized_value: str
    source_url: str
    source_type: str  # json_ld | microdata | tel_link | address_tag | meta_tag |
                      # header_brand | footer_text | copyright | title_derived |
                      # logo_alt | html_text
    source_quality: float  # 0.0 – 1.0 weight
    context_snippet: str = ""
    entity_name: str = ""  # associated business entity name if identifiable


@dataclass
class NAPEvidence:
    """Single evidence entry for the report."""

    page: str
    raw_value: str
    source_type: str
    source_quality: float

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "raw_value": self.raw_value,
            "source_type": self.source_type,
            "source_quality": self.source_quality,
        }


@dataclass
class NAPFieldReport:
    """Comparison result for a single NAP field."""

    field: NAPField
    pages_compared: List[str]  # only pages where this field was actually found
    values: List[str]  # unique raw values
    normalized_values: List[str]  # unique normalized values
    confidence: float
    verdict: NAPVerdict
    evidence: List[NAPEvidence] = field(default_factory=list)
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "pages_compared": self.pages_compared,
            "values": self.values,
            "normalized_values": self.normalized_values,
            "confidence": round(self.confidence, 2),
            "verdict": self.verdict,
            "evidence": [e.to_dict() for e in self.evidence],
            "details": self.details,
        }


@dataclass
class AddressComponents:
    """Parsed address broken into comparable components."""

    street: str = ""
    locality: str = ""  # city
    region: str = ""  # state
    postal_code: str = ""
    country: str = ""
    raw_normalized: str = ""

    def has_components(self) -> bool:
        """True if at least one meaningful component was parsed."""
        return bool(self.street or self.locality or self.region or self.postal_code)
