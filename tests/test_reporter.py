"""
Unit tests for Reporter and JSON schema validation.
"""

import json
from seo_audit.models import PageResponse, ParsedPage, SEOFinding
from seo_audit.reporter import JSONReporter


def test_export_audit_json_schema(tmp_path):
    output_file = tmp_path / "audit.json"

    findings = [
        SEOFinding(
            metric="missing_meta_description",
            page="https://example.com/about",
            severity="high",
            evidence="No meta description tag was found in the HTML head.",
            suggested_fix="Add a unique and relevant meta description for this page.",
        ),
        SEOFinding(
            metric="missing_h1",
            page="https://example.com/about",
            severity="high",
            evidence="Found 0 <h1> elements in the document.",
            suggested_fix="Add a single primary <h1> element.",
        ),
    ]

    JSONReporter.export_audit_json(findings, output_path=str(output_file))

    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 2

    for item in data:
        assert "metric" in item
        assert "page" in item
        assert "severity" in item
        assert "evidence" in item
        assert "suggested_fix" in item
        assert isinstance(item["metric"], str)
        assert isinstance(item["page"], str)
        assert item["severity"] in ["critical", "high", "medium", "low", "info"]
        assert len(item["evidence"]) > 0
        assert len(item["suggested_fix"]) > 0
