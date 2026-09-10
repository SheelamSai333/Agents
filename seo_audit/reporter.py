"""
Reporter component generating audit.json, summary reports, and terminal output.
"""

from collections import Counter
import json
import logging
from pathlib import Path
from typing import Dict, List
from seo_audit.models import ParsedPage, SEOFinding

logger = logging.getLogger(__name__)


class JSONReporter:
    """Formats and exports audit findings to audit.json and summary reports."""

    @staticmethod
    def export_audit_json(findings: List[SEOFinding], output_path: str = "outputs/audit.json") -> None:
        """
        Export findings to audit.json.
        Each item strictly adheres to:
        {
          "metric": ...,
          "page": ...,
          "severity": ...,
          "evidence": ...,
          "suggested_fix": ...
        }
        """
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = [f.to_dict() for f in findings]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully generated {out_path} with {len(findings)} findings.")

    @staticmethod
    def export_summary_json(
        findings: List[SEOFinding],
        crawled_pages: List[ParsedPage],
        duration_seconds: float,
        output_path: str = "outputs/audit_summary.json",
    ) -> None:
        """Export comprehensive summary report including metadata and breakdowns."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        severity_counts = Counter(f.severity for f in findings)
        metric_counts = Counter(f.metric for f in findings)

        summary_data = {
            "total_crawled_pages": len(crawled_pages),
            "total_findings": len(findings),
            "duration_seconds": round(duration_seconds, 2),
            "severity_breakdown": {
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
                "info": severity_counts.get("info", 0),
            },
            "metric_breakdown": dict(metric_counts.most_common()),
            "crawled_urls": [p.url for p in crawled_pages],
            "findings": [f.to_dict() for f in findings],
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)


def print_cli_summary(
    findings: List[SEOFinding],
    crawled_pages: List[ParsedPage],
    duration: float,
    output_path: str = "outputs/audit.json",
) -> None:
    """Print an eye-catching, structured terminal summary of the SEO audit."""
    severity_counts = Counter(f.severity for f in findings)
    metric_counts = Counter(f.metric for f in findings)

    divider = "=" * 70
    sub_divider = "-" * 70

    print(f"\n{divider}")
    print("                    ON-PAGE SEO AUDIT REPORT")
    print(divider)
    print(f" Crawled Pages   : {len(crawled_pages)}")
    print(f" Duration        : {duration:.2f}s")
    print(f" Total Findings  : {len(findings)}")
    print(sub_divider)
    print(" FINDINGS BY SEVERITY:")
    print(f"   [!] Critical  : {severity_counts.get('critical', 0)}")
    print(f"   [*] High      : {severity_counts.get('high', 0)}")
    print(f"   [-] Medium    : {severity_counts.get('medium', 0)}")
    print(f"   [.] Low       : {severity_counts.get('low', 0)}")
    print(f"   [i] Info      : {severity_counts.get('info', 0)}")
    print(sub_divider)

    if metric_counts:
        print(" TOP IDENTIFIED ISSUES:")
        for metric, count in metric_counts.most_common(8):
            sev = next((f.severity for f in findings if f.metric == metric), "medium")
            print(f"   - {metric:<30} [{sev.upper()}]: {count} occurrences")
        print(sub_divider)

    print(f" Output written to: {output_path}")
    print(f"{divider}\n")
