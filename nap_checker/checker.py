"""End-to-end NAP consistency checker."""

import logging
from typing import Dict, List, Tuple

from seo_audit.models import ParsedPage

from nap_checker.contact_detector import ContactPageDetector
from nap_checker.structured_data_extractor import StructuredDataExtractor
from nap_checker.html_nap_extractor import HTMLNAPExtractor
from nap_checker.comparison_engine import ComparisonEngine
from nap_checker.models import NAPFieldReport, NAPOccurrence
from nap_checker.reporter import export_nap_report, print_nap_cli_summary

logger = logging.getLogger(__name__)


class NAPChecker:
    """Run NAP extraction and deterministic consistency comparison."""

    def __init__(self):
        self.detector = ContactPageDetector()
        self.structured_extractor = StructuredDataExtractor()
        self.html_extractor = HTMLNAPExtractor()
        self.comparison_engine = ComparisonEngine()

    def check(
        self, pages: List[ParsedPage]
    ) -> Tuple[Dict[str, NAPFieldReport], List[NAPOccurrence]]:
        """Extract and compare NAP information across crawled pages."""

        prioritized_pages, page_priorities = self.detector.detect(pages)

        occurrences: List[NAPOccurrence] = []

        for page in prioritized_pages:
            occurrences.extend(
                self.structured_extractor.extract_from_page(page)
            )
            occurrences.extend(
                self.html_extractor.extract_from_page(page)
            )

        # Deduplicate: same (field, raw_value, source_url, source_type) is a duplicate
        seen = set()
        deduped: List[NAPOccurrence] = []
        for occ in occurrences:
            key = (occ.field, occ.raw_value, occ.source_url, occ.source_type)
            if key not in seen:
                seen.add(key)
                deduped.append(occ)

        occurrences = deduped

        # Compare all fields, passing page_priorities for confidence scoring
        reports = self.comparison_engine.compare_all(
            occurrences, page_priorities
        )

        return reports, occurrences

    @staticmethod
    def export_report(
        reports: Dict[str, NAPFieldReport],
        output_path: str = "outputs/nap_report.json",
    ) -> None:
        """Write NAP report to JSON."""
        export_nap_report(reports, output_path)

    @staticmethod
    def print_summary(
        reports: Dict[str, NAPFieldReport],
        crawled_count: int,
        duration: float,
        output_path: str = "outputs/nap_report.json",
    ) -> None:
        """Print CLI summary table."""
        print_nap_cli_summary(reports, crawled_count, duration, output_path)
