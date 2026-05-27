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


def write_pmd_report(path, file_violations):
    """Write a PMD report XML.

    Args:
        path: pathlib.Path to write to.
        file_violations: dict mapping file_name -> {rule: [beginlines]}
            e.g. {"AccountService.cls": {"AvoidDebugStatements": ["10", "42"]}}
            OR dict mapping rule -> count (legacy helper compat, uses "test.cls")
    """
    # Support legacy {rule: count} form by normalising to file-keyed form
    if file_violations and not isinstance(next(iter(file_violations.values())), dict):
        file_violations = {
            "test.cls": {
                rule: [str(i + 1) for i in range(count)]
                for rule, count in file_violations.items()
            }
        }

    files_xml = ""
    for file_name, rules in file_violations.items():
        violations_xml = ""
        for rule, lines in rules.items():
            for line in lines:
                violations_xml += (
                    f'    <violation rule="{rule}" beginline="{line}" '
                    f'endline="{line}" begincolumn="1" endcolumn="1" priority="3">'
                    f'</violation>\n'
                )
        files_xml += f'  <file name="{file_name}">\n{violations_xml}  </file>\n'
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

        mock_smells = MagicMock()
        mock_apex = MagicMock()
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        # Expect labels called for each rule + TOTAL
        assert mock_smells.labels.call_count >= 2

    def test_no_report_file_sets_rules_to_zero(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["RuleA", "RuleB"])

        fake_report = str(tmp_path / "pmd-report.xml")  # doesn't exist

        mock_smells = MagicMock()
        mock_apex = MagicMock()
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=fake_report), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        assert mock_smells.labels.call_count == 2
        mock_apex.labels.assert_not_called()

    def test_handles_parse_error(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        ruleset.write_text("NOT VALID XML")
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}):
            monitor_pmd_code_smells(mock_sf)  # Should not raise


class TestPmdApexViolationsGauge:
    """Tests for the new per-class/rule violation gauge."""

    def test_emits_gauge_per_apex_and_rule(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["AvoidDebugStatements"])

        report_path = tmp_path / "pmd-report.xml"
        write_pmd_report(report_path, {
            "/path/to/AccountService.cls": {"AvoidDebugStatements": ["10", "42", "87"]},
            "/path/to/ContactService.cls": {"AvoidDebugStatements": ["5"]},
        })

        mock_smells = MagicMock()
        mock_apex = MagicMock()
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        # One label call per (apex, rule) combo → 2 combos
        assert mock_apex.labels.call_count == 2

    def test_gauge_value_equals_violation_count(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["AvoidDebugStatements"])

        report_path = tmp_path / "pmd-report.xml"
        write_pmd_report(report_path, {
            "/src/AccountService.cls": {"AvoidDebugStatements": ["10", "42", "87"]},
        })

        captured_set = {}
        mock_smells = MagicMock()
        mock_apex = MagicMock()
        mock_apex.labels.return_value.set.side_effect = lambda v: captured_set.update({"count": v})

        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        assert captured_set["count"] == 3

    def test_start_lines_are_comma_separated(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["AvoidDebugStatements"])

        report_path = tmp_path / "pmd-report.xml"
        write_pmd_report(report_path, {
            "/src/MyClass.cls": {"AvoidDebugStatements": ["10", "42", "87"]},
        })

        captured_labels = {}
        mock_smells = MagicMock()
        mock_apex = MagicMock()
        mock_apex.labels.side_effect = lambda **kw: captured_labels.update(kw) or MagicMock()

        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        assert captured_labels["apex_name"] == "MyClass"
        assert captured_labels["rule_name"] == "AvoidDebugStatements"
        assert captured_labels["start_lines"] == "10,42,87"

    def test_apex_name_strips_extension_and_path(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["NoPrint"])

        report_path = tmp_path / "pmd-report.xml"
        write_pmd_report(report_path, {
            "/very/deep/path/MyTrigger.trigger": {"NoPrint": ["7"]},
        })

        captured_labels = {}
        mock_smells = MagicMock()
        mock_apex = MagicMock()
        mock_apex.labels.side_effect = lambda **kw: captured_labels.update(kw) or MagicMock()

        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        assert captured_labels["apex_name"] == "MyTrigger"

    def test_multiple_rules_per_apex_emit_separate_labels(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["AvoidDebugStatements", "NoPrint"])

        report_path = tmp_path / "pmd-report.xml"
        write_pmd_report(report_path, {
            "/src/AccountService.cls": {
                "AvoidDebugStatements": ["10", "42"],
                "NoPrint": ["5"],
            },
        })

        mock_smells = MagicMock()
        mock_apex = MagicMock()
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        # AccountService has 2 rules → 2 label calls
        assert mock_apex.labels.call_count == 2

    def test_cleared_before_each_run(self, mock_sf, tmp_path):
        from tech_debt.pmd import monitor_pmd_code_smells
        ruleset = tmp_path / "ruleset.xml"
        write_ruleset(ruleset, ["AvoidDebugStatements"])

        report_path = tmp_path / "pmd-report.xml"
        write_pmd_report(report_path, {"AvoidDebugStatements": 1})

        mock_smells = MagicMock()
        mock_apex = MagicMock()
        with patch.dict(os.environ, {"PMD_RULESET_PATH": str(ruleset)}), \
             patch("tech_debt.pmd.os.path.join", return_value=str(report_path)), \
             patch("tech_debt.pmd.pmd_code_smells_gauge", mock_smells), \
             patch("tech_debt.pmd.pmd_apex_violations_gauge", mock_apex):
            monitor_pmd_code_smells(mock_sf)

        mock_apex.clear.assert_called_once()
