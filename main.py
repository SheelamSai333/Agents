#!/usr/bin/env python3
"""
CLI Entry Point for the On-Page SEO Audit Agent.
Usage:
    python main.py --url https://example.com
"""

import argparse
import logging
from pathlib import Path
import sys
import time

from seo_audit.config import AuditConfig
from seo_audit.crawler import Crawler
from seo_audit.engine import RuleEngine
from seo_audit.reporter import JSONReporter, print_cli_summary
from nap_checker.checker import NAPChecker
from site_qa.agent import QAAgent


def setup_logging(verbose: bool = False) -> None:
    """Configure stdout logging format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Production-Quality On-Page SEO Audit Agent",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--url",
        required=True,
        type=str,
        help="Target website URL to audit (e.g. https://example.com)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=25,
        help="Maximum number of internal pages to crawl",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum link traversal depth from starting URL",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Politeness delay between requests in seconds",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/audit.json",
        help="Destination path for findings output",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="Bypass robots.txt crawling restrictions",
    )
    parser.add_argument(
        "--no-ssl-verify",
        action="store_true",
        help="Disable SSL/TLS certificate verification",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging",
    )
    parser.add_argument(
        "--nap",
        action="store_true",
        help="Run NAP consistency checking instead of the SEO audit",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help="Natural-language question to answer using crawled page content",
    )
    parser.add_argument(
        "--answer-file",
        type=str,
        default="outputs/answer.json",
        help="Destination path for Q3 answer JSON output",
    )
    return parser.parse_args()


def main() -> int:
    """Main execution workflow."""
    args = parse_args()
    setup_logging(args.verbose)

    config = AuditConfig(
        start_url=args.url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        timeout=args.timeout,
        delay=args.delay,
        output_file=args.output,
        respect_robots_txt=not args.ignore_robots,
        verify_ssl=not args.no_ssl_verify,
    )

    start_time = time.time()
    crawler = Crawler(config=config)

    try:
        crawled_pages = crawler.crawl()
    except Exception as e:
        logging.error(f"Failed during crawl initialization: {e}")
        return 1

    if not crawled_pages:
        logging.warning("No pages were crawled. Check target URL and network accessibility.")
        return 1

    if args.nap:
        logging.info("Executing NAP consistency checks...")

        nap_checker = NAPChecker()
        reports, occurrences = nap_checker.check(crawled_pages)

        nap_checker.export_report(
            reports,
            output_path="outputs/nap_report.json",
        )

        duration = time.time() - start_time

        nap_checker.print_summary(reports, len(crawled_pages), duration, output_path="outputs/nap_report.json")

        return 0

    if args.query:
        logging.info("Executing Q3 Grounded Website Question-Answering...")

        qa_agent = QAAgent()
        response = qa_agent.answer_query(crawled_pages, args.query)
        qa_agent.export_answer(response, output_path=args.answer_file)

        duration = time.time() - start_time
        qa_agent.print_summary(response, len(crawled_pages), duration, output_path=args.answer_file)

        return 0

    # Run SEO Rule Engine
    logging.info("Executing SEO Rule Engine checks...")
    engine = RuleEngine(config=config)
    findings = engine.audit(crawled_pages)

    duration = time.time() - start_time

    # Determine summary path in same directory as output_file
    out_dir = Path(config.output_file).parent
    summary_path = str(out_dir / "audit_summary.json")

    # Export audit.json & summary
    JSONReporter.export_audit_json(findings, output_path=config.output_file)
    JSONReporter.export_summary_json(findings, crawled_pages, duration, output_path=summary_path)

    # Print terminal overview
    print_cli_summary(findings, crawled_pages, duration, output_path=config.output_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
