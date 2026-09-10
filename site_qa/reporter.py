"""
Report generation and CLI summary for Q3 Question-Answering Agent.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from site_qa.models import QAResponse

logger = logging.getLogger(__name__)


def export_answer_json(response: QAResponse, output_path: str = "answer.json") -> None:
    """Export QAResponse to answer.json matching assignment specification."""
    path = Path(output_path)
    data = response.to_dict()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Exported answer report to %s", path.resolve())


def print_qa_cli_summary(
    response: QAResponse,
    crawled_count: int,
    duration: float,
) -> None:
    """Print formatted terminal overview for Q3 QA results."""
    width = 80
    print("\n" + "=" * width)
    print("  Q3 GROUNDED WEBSITE QUESTION-ANSWERING SUMMARY")
    print("=" * width)
    print(f"  Pages Crawled    : {crawled_count}")
    print(f"  Execution Time   : {duration:.2f}s")
    print(f"  User Query       : \"{response.query}\"")

    is_supported = response.url is not None and response.excerpt is not None
    status_str = "SUPPORTED (Grounding Verified)" if is_supported else "UNSUPPORTED (No Grounded Answer on Site)"

    print(f"  Status           : {status_str}")
    print(f"  Confidence Score : {response.confidence:.2f}")

    if is_supported:
        print(f"  Source URL       : {response.url}")
        print("-" * width)
        print("  VERBATIM SOURCE EXCERPT:")
        # Wrap excerpt nicely
        excerpt_lines = response.excerpt.split("\n") if response.excerpt else []
        for line in excerpt_lines:
            print(f"    \"{line}\"")
    else:
        print("-" * width)
        print("  No verifiable answer found in crawled page content.")
        print("  Emitted null result as required by assignment specification.")

    print("=" * width + "\n")
