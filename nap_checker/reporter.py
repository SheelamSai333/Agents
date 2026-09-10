"""NAP report output: JSON export and CLI summary table."""

import json
import logging
from pathlib import Path
from typing import Dict, List

from nap_checker.models import NAPFieldReport

logger = logging.getLogger(__name__)


def export_nap_report(
    reports: Dict[str, NAPFieldReport],
    output_path: str = "outputs/nap_report.json",
) -> None:
    """Write NAP report to JSON as an array of field reports."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [report.to_dict() for report in reports.values()]

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info(
        "Successfully generated %s with %d field reports.",
        output_path,
        len(data),
    )


def print_nap_cli_summary(
    reports: Dict[str, NAPFieldReport],
    crawled_count: int,
    duration: float,
    output_path: str = "outputs/nap_report.json",
) -> None:
    """Print a formatted terminal summary of the NAP consistency check."""
    divider = "=" * 70
    sub_divider = "-" * 70

    print(f"\n{divider}")
    print("                  NAP CONSISTENCY REPORT")
    print(divider)
    print(f" Crawled Pages   : {crawled_count}")
    print(f" Duration        : {duration:.2f}s")
    print(sub_divider)

    # Header
    print(f" {'Field':<10}| {'Verdict':<32}| {'Confidence':<12}| Values")
    print(f" {'-'*9}|{'-'*32}|{'-'*12}|{'-'*20}")

    for field_name in ("name", "address", "phone"):
        report = reports.get(field_name)
        if not report:
            continue

        raw_count = len(report.values)
        norm_count = len(report.normalized_values)

        if raw_count == 0:
            val_display = "—"
        elif raw_count == norm_count:
            val_display = str(raw_count)
        else:
            val_display = f"{raw_count} raw / {norm_count} normalized"

        print(
            f" {field_name.capitalize():<10}"
            f"| {report.verdict:<32}"
            f"| {report.confidence:<12.2f}"
            f"| {val_display}"
        )

    print(sub_divider)
    print(f" Output written to: {output_path}")
    print(f"{divider}\n")
