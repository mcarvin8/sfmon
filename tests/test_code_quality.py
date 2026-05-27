"""Unit tests for tech_debt/code_quality.py"""

import pytest
from unittest.mock import MagicMock, patch


class TestIsTestClass:
    def test_detects_istest_annotation(self):
        from tech_debt.code_quality import _is_test_class
        body = "@isTest\npublic class MyTest {}"
        assert _is_test_class(body) is True

    def test_returns_false_without_annotation(self):
        from tech_debt.code_quality import _is_test_class
        body = "public class MyClass {}"
        assert _is_test_class(body) is False

    def test_returns_false_for_none(self):
        from tech_debt.code_quality import _is_test_class
        assert _is_test_class(None) is False

    def test_returns_false_for_empty_string(self):
        from tech_debt.code_quality import _is_test_class
        assert _is_test_class("") is False

    def test_returns_false_for_non_string(self):
        from tech_debt.code_quality import _is_test_class
        assert _is_test_class(123) is False

    def test_ignores_istest_in_block_comment(self):
        from tech_debt.code_quality import _is_test_class
        body = "/* @isTest */\npublic class MyClass {}"
        assert _is_test_class(body) is False

    def test_ignores_istest_in_line_comment(self):
        from tech_debt.code_quality import _is_test_class
        body = "// @isTest\npublic class MyClass {}"
        assert _is_test_class(body) is False

    def test_detects_istest_case_insensitive(self):
        from tech_debt.code_quality import _is_test_class
        body = "@IsTest\npublic class MyClass {}"
        assert _is_test_class(body) is True

    def test_returns_false_when_no_class_keyword(self):
        from tech_debt.code_quality import _is_test_class
        body = "@isTest interface Foo {}"
        assert _is_test_class(body) is False


class TestApexClassesApiVersion:
    def test_sets_gauge_per_record(self, mock_sf):
        from tech_debt.code_quality import apex_classes_api_version
        records = [
            {"Id": "001", "Name": "OldClass", "ApiVersion": "45"},
            {"Id": "002", "Name": "AnotherOld", "ApiVersion": "40"},
        ]
        mock_gauge = MagicMock()
        with patch("tech_debt.code_quality.query_records_all", return_value=records), \
             patch("tech_debt.code_quality.deprecated_apex_class_gauge", mock_gauge):
            apex_classes_api_version(mock_sf)
        assert mock_gauge.labels.call_count == 2
        mock_gauge.clear.assert_called_once()

    def test_empty_results(self, mock_sf):
        from tech_debt.code_quality import apex_classes_api_version
        mock_gauge = MagicMock()
        with patch("tech_debt.code_quality.query_records_all", return_value=[]), \
             patch("tech_debt.code_quality.deprecated_apex_class_gauge", mock_gauge):
            apex_classes_api_version(mock_sf)
        mock_gauge.labels.assert_not_called()

    def test_handles_exception(self, mock_sf):
        from tech_debt.code_quality import apex_classes_api_version
        with patch("tech_debt.code_quality.query_records_all", side_effect=RuntimeError("fail")):
            apex_classes_api_version(mock_sf)  # Should not raise


class TestApexTriggersApiVersion:
    def test_sets_gauge_per_record(self, mock_sf):
        from tech_debt.code_quality import apex_triggers_api_version
        records = [{"Id": "t01", "Name": "OldTrigger", "ApiVersion": "42"}]
        mock_gauge = MagicMock()
        with patch("tech_debt.code_quality.query_records_all", return_value=records), \
             patch("tech_debt.code_quality.deprecated_apex_trigger_gauge", mock_gauge):
            apex_triggers_api_version(mock_sf)
        mock_gauge.labels.assert_called_once_with(id="t01", name="OldTrigger")
        mock_gauge.labels().set.assert_called_once_with(42)

    def test_handles_exception(self, mock_sf):
        from tech_debt.code_quality import apex_triggers_api_version
        with patch("tech_debt.code_quality.query_records_all", side_effect=RuntimeError("fail")):
            apex_triggers_api_version(mock_sf)  # Should not raise


class TestWorkflowRulesMonitoring:
    def test_sets_gauge_per_rule(self, mock_sf):
        from tech_debt.code_quality import workflow_rules_monitoring
        records = [
            {"Id": "wf01", "CreatedDate": "2020-01-01", "NamespacePrefix": None},
            {"Id": "wf02", "CreatedDate": "2021-06-15", "NamespacePrefix": "ns"},
        ]
        mock_gauge = MagicMock()
        with patch("tech_debt.code_quality.tooling_query_records_all", return_value=records), \
             patch("tech_debt.code_quality.workflow_rules_gauge", mock_gauge):
            workflow_rules_monitoring(mock_sf)
        assert mock_gauge.labels.call_count == 2

    def test_null_namespace_becomes_none_string(self, mock_sf):
        from tech_debt.code_quality import workflow_rules_monitoring
        records = [{"Id": "wf01", "CreatedDate": "2020-01-01", "NamespacePrefix": None}]
        captured = {}
        mock_gauge = MagicMock()
        mock_gauge.labels.side_effect = lambda **kw: captured.update(kw) or MagicMock()
        with patch("tech_debt.code_quality.tooling_query_records_all", return_value=records), \
             patch("tech_debt.code_quality.workflow_rules_gauge", mock_gauge):
            workflow_rules_monitoring(mock_sf)
        assert captured.get("namespace_prefix") == "None"

    def test_handles_exception(self, mock_sf):
        from tech_debt.code_quality import workflow_rules_monitoring
        with patch("tech_debt.code_quality.tooling_query_records_all", side_effect=RuntimeError("fail")):
            workflow_rules_monitoring(mock_sf)  # Should not raise


class TestApexUsedLimitsMonitoring:
    def _make_class(self, is_test_body="public class Foo {}"):
        return {"Id": "c01", "Name": "Foo", "LengthWithoutComments": "1000", "Body": is_test_body}

    def _make_trigger(self):
        return {"Id": "t01", "Name": "FooTrigger", "LengthWithoutComments": "500"}

    def test_sets_class_and_trigger_gauges(self, mock_sf):
        from tech_debt.code_quality import apex_used_limits_monitoring
        classes = [self._make_class()]
        triggers = [self._make_trigger()]
        mock_class_gauge = MagicMock()
        mock_trigger_gauge = MagicMock()
        mock_pct_gauge = MagicMock()
        with patch("tech_debt.code_quality.query_records_all", side_effect=[classes, triggers]), \
             patch("tech_debt.code_quality.apex_class_length_without_comments_gauge", mock_class_gauge), \
             patch("tech_debt.code_quality.apex_trigger_length_without_comments_gauge", mock_trigger_gauge), \
             patch("tech_debt.code_quality.apex_character_limit_percentage_gauge", mock_pct_gauge):
            apex_used_limits_monitoring(mock_sf)
        mock_class_gauge.labels.assert_called_once()
        mock_trigger_gauge.labels.assert_called_once()
        mock_pct_gauge.set.assert_called_once()

    def test_excludes_test_class_from_total(self, mock_sf):
        from tech_debt.code_quality import apex_used_limits_monitoring
        test_body = "@isTest\npublic class MyTest {}"
        classes = [{"Id": "c01", "Name": "MyTest", "LengthWithoutComments": "2000", "Body": test_body}]
        triggers = []
        captured_pct = {}
        mock_class_gauge = MagicMock()
        mock_trigger_gauge = MagicMock()
        mock_pct_gauge = MagicMock()
        mock_pct_gauge.set.side_effect = lambda v: captured_pct.update({"v": v})
        with patch("tech_debt.code_quality.query_records_all", side_effect=[classes, triggers]), \
             patch("tech_debt.code_quality.apex_class_length_without_comments_gauge", mock_class_gauge), \
             patch("tech_debt.code_quality.apex_trigger_length_without_comments_gauge", mock_trigger_gauge), \
             patch("tech_debt.code_quality.apex_character_limit_percentage_gauge", mock_pct_gauge):
            apex_used_limits_monitoring(mock_sf)
        # Test class excluded, so total_chars = 0
        assert captured_pct["v"] == 0.0

    def test_handles_exception(self, mock_sf):
        from tech_debt.code_quality import apex_used_limits_monitoring
        with patch("tech_debt.code_quality.query_records_all", side_effect=RuntimeError("fail")):
            apex_used_limits_monitoring(mock_sf)  # Should not raise
