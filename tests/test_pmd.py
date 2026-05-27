"""Unit tests for tech_debt/pmd.py"""

import os
import pytest
from unittest.mock import MagicMock, patch


def write_ruleset(path, rules):
    """Write a minimal PMD ruleset XML."""
    rules_xml = "\n".join(
        f'  <rule ref="category/apex/{r}.xml/{r}"/>' for r in rules
    )
    path.write_text(f'<?xml version="1.0"?>\n<ruleset>\n{rules_xml}\n</ruleset>')


def write_pmd_report(path, violations):
    """Write a minimal PMD report XML with violations dict {rule: count}."""
    files_xml = ""
    for rule, count in violations.items():
        v_xml = "\n".join(
            f'    <violation rule="{rule}" beginline="1" endline="1" begincolumn="1" endcolumn="1" priority="3"></violation>'
            for _ in range(count)
        )
        files_xml += f'  <file name="test.cls">\n{v_xml}\n  </file>\n'
    path.write_text(f'<?xml version="1.0"?>\n<pmd version="6.0">\n{files_xml}</pmd>')


class TestMonitorPmdCodeSmells:
    def test_no_ruleset_path_exits_quietly(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        with patch.dict(os.environ, {"PMD_RULESET_PATH": ""}):
            monitor_pmd_code_smells(mock_sf)  # Should not raise

    def test_missing_ruleset_file_exits_quietly(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(tmp_path / "nonexistent.xml")}):
            monitor_pmd_code_smells(mock_sf)  # Should not raise

    def test_counts_violations_from_report(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["AvoidDebugStatements", "NoPrint"])

        report_path = tmp_path / "pmd-report.xml"
        write_pmd_report(report_path, {"AvoidDebugStatements": 3, "NoPrint": 1})

        mock_gauge = MagicMock()
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_gauge):
            monitor_pmd_code_smells(mock_sf)

        # Expect labels called for each rule + TOTAL
        assert mock_gauge.labels.call_count >= 2

    def test_no_report_file_sets_rules_to_zero(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["RuleA", "RuleB"])

        # Point pmd_file_path to a non-existent file
        fake_report = str(tmp_path / "pmd-report.xml")  # doesn't exist

        mock_gauge = MagicMock()
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=fake_report), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_gauge):
            monitor_pmd_code_smells(mock_sf)

        # Should set 0 for each rule in ruleset
        assert mock_gauge.labels.call_count == 2

    def test_handles_parse_error(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        ruleset.write_text("NOT VALID XML")
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}):
            monitor_pmd_code_smells(mock_sf)  # Should not raise
