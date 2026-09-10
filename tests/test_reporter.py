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


def test_export_creates_parent_directory(tmp_path):
    nested_output = tmp_path / "nested" / "folder" / "audit.json"
    findings = [
        SEOFinding(
            metric="missing_h1",
            page="https://example.com",
            severity="high",
            evidence="No h1",
            suggested_fix="Add h1",
        )
    ]
    JSONReporter.export_audit_json(findings, output_path=str(nested_output))
    assert nested_output.exists()


def test_default_output_paths():
    from seo_audit.config import AuditConfig
    import inspect
    from nap_checker.reporter import export_nap_report
    from site_qa.reporter import export_answer_json

    config = AuditConfig()
    assert config.output_file.startswith("outputs/")
    assert config.summary_file.startswith("outputs/")

    nap_sig = inspect.signature(export_nap_report)
    assert nap_sig.parameters["output_path"].default == "outputs/nap_report.json"

    qa_sig = inspect.signature(export_answer_json)
    assert qa_sig.parameters["output_path"].default == "outputs/answer.json"

