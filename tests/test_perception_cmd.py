"""Tests for geo perception — deterministic AI perception snapshot (MVP C).

run_full_audit is patched at the command's import site — no real network.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from geo_optimizer.cli.main import cli
from geo_optimizer.models.results import (
    AuditResult,
    BrandEntityResult,
    CitabilityResult,
    MethodScore,
    SchemaResult,
)


def _audit_result() -> AuditResult:
    return AuditResult(
        url="https://example.com",
        score=75,
        band="good",
        brand_entity=BrandEntityResult(
            names_found=["Acme"],
            has_about_link=True,
            has_contact_info=True,
            kg_pillar_count=1,
        ),
        schema=SchemaResult(found_types=["Organization", "FAQPage"], has_faq=True, has_article=True),
        citability=CitabilityResult(
            grade="B",
            methods=[
                MethodScore(name="front_loaded_answers", label="Front-loaded answers", score=9, max_score=10)
            ],
        ),
    )


class TestPerceptionCmd:
    @patch("geo_optimizer.cli.perception_cmd.run_full_audit")
    def test_text_output(self, mock_audit):
        mock_audit.return_value = _audit_result()
        result = CliRunner().invoke(cli, ["perception", "--url", "https://example.com"])
        assert result.exit_code == 0
        assert "AI PERCEPTION SNAPSHOT" in result.output
        assert "Simulated" in result.output
        assert "Acme" in result.output
        assert "Citability grade:" in result.output
        assert "Organization" in result.output

    @patch("geo_optimizer.cli.perception_cmd.run_full_audit")
    def test_json_output_contract(self, mock_audit):
        mock_audit.return_value = _audit_result()
        result = CliRunner().invoke(cli, ["perception", "--url", "https://example.com", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["url"] == "https://example.com"
        assert payload["mode"] == "deterministic"
        assert payload["brand_name"] == "Acme"
        assert payload["citability_grade"] == "B"
        assert "disclaimer" in payload

    def test_rejects_unsafe_url(self):
        result = CliRunner().invoke(cli, ["perception", "--url", "http://localhost:8000"])
        assert result.exit_code == 1
        assert "Unsafe URL" in result.output

    @patch("geo_optimizer.cli.perception_cmd.run_full_audit")
    def test_file_output(self, mock_audit, tmp_path):
        mock_audit.return_value = _audit_result()
        out_file = tmp_path / "perception.txt"
        result = CliRunner().invoke(
            cli, ["perception", "--url", "https://example.com", "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        assert "AI PERCEPTION SNAPSHOT" in out_file.read_text()
