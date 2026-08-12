"""Unit tests for salesforce_monitoring.py's --once/--job CLI path.

Note: this module is excluded from the coverage report (see pyproject.toml)
because main()/schedule_tasks() are integration-flavored (real APScheduler,
real HTTP server) and not worth mocking that heavily. run_once(), _run_job(),
and _parse_args() are self-contained enough to test directly, so they're
covered here for correctness even though the numbers don't show up in the
coverage report.

Job functions are captured by value inside ALWAYS_ON_JOBS/SCHEDULED_JOBS at
module import time, so patching e.g. sfmon.salesforce_monitoring.
monitor_salesforce_limits does NOT reach the copy stored in those tuples.
The correct seam to control success/failure per test is _run_job itself.
"""

import pytest
from unittest.mock import MagicMock, patch

from sfmon import salesforce_monitoring as sm


class TestParseArgs:
    def test_defaults_to_daemon_mode(self):
        args = sm._parse_args([])
        assert args.once is False
        assert args.job is None

    def test_once_flag(self):
        args = sm._parse_args(["--once"])
        assert args.once is True
        assert args.job is None

    def test_once_with_job(self):
        args = sm._parse_args(["--once", "--job", "monitor_salesforce_limits"])
        assert args.once is True
        assert args.job == "monitor_salesforce_limits"


class TestRunJob:
    def test_returns_true_on_success(self):
        func = MagicMock()
        assert sm._run_job("default", MagicMock(), func, "Test Job") is True
        func.assert_called_once()

    def test_returns_false_on_exception(self):
        func = MagicMock(side_effect=RuntimeError("boom"))
        assert sm._run_job("default", MagicMock(), func, "Test Job") is False


class TestRunOnce:
    def test_unknown_job_filter_returns_2_without_connecting(self):
        with patch("sfmon.orgs.build_connections") as mock_build:
            code = sm.run_once(job_filter="not_a_real_job")
        assert code == 2
        mock_build.assert_not_called()

    def test_no_connections_returns_1(self):
        with patch("sfmon.orgs.build_connections", return_value={}):
            code = sm.run_once()
        assert code == 1

    def test_job_filter_forces_run_regardless_of_config(self):
        fake_sf = MagicMock()
        with patch("sfmon.orgs.build_connections", return_value={"default": fake_sf}), \
             patch.object(sm, "get_always_on_config", return_value=None), \
             patch.object(sm, "get_schedule_config", return_value=None), \
             patch.object(sm, "_run_job", return_value=True) as mock_run:
            code = sm.run_once(job_filter="monitor_salesforce_limits")

        assert code == 0
        mock_run.assert_called_once()
        _, _, func, job_name = mock_run.call_args[0]
        assert job_name == "Monitor Salesforce Limits"

    def test_no_filter_runs_only_enabled_jobs(self):
        fake_sf = MagicMock()

        def always_on_side_effect(job_id, default_schedule, org_name=None):
            return default_schedule if job_id == "monitor_salesforce_limits" else None

        def scheduled_side_effect(job_id, default_schedule, org_name=None):
            return default_schedule if job_id == "monitor_apex_flex_queue" else None

        with patch("sfmon.orgs.build_connections", return_value={"default": fake_sf}), \
             patch.object(sm, "get_always_on_config", side_effect=always_on_side_effect), \
             patch.object(sm, "get_schedule_config", side_effect=scheduled_side_effect), \
             patch.object(sm, "_run_job", return_value=True) as mock_run:
            code = sm.run_once()

        assert code == 0
        run_job_ids = {call.args[3] for call in mock_run.call_args_list}
        assert run_job_ids == {"Monitor Salesforce Limits", "Monitor Apex Flex Queue"}

    def test_runs_once_per_org_in_fleet_mode(self):
        connections = {"prod": MagicMock(), "sandbox": MagicMock()}
        with patch("sfmon.orgs.build_connections", return_value=connections), \
             patch.object(sm, "_run_job", return_value=True) as mock_run:
            sm.run_once(job_filter="monitor_salesforce_limits")

        org_names = {call.args[0] for call in mock_run.call_args_list}
        assert org_names == {"prod", "sandbox"}

    def test_any_failure_returns_exit_code_1(self):
        fake_sf = MagicMock()
        with patch("sfmon.orgs.build_connections", return_value={"default": fake_sf}), \
             patch.object(sm, "_run_job", return_value=False):
            code = sm.run_once(job_filter="monitor_salesforce_limits")
        assert code == 1

    def test_prints_prometheus_exposition_text_to_stdout(self, capsys):
        fake_sf = MagicMock()
        with patch("sfmon.orgs.build_connections", return_value={"default": fake_sf}), \
             patch.object(sm, "_run_job", return_value=True):
            sm.run_once(job_filter="monitor_salesforce_limits")

        captured = capsys.readouterr()
        assert "# HELP" in captured.out
        assert "# TYPE" in captured.out


class TestMainCliDispatch:
    def test_job_without_once_exits_2_without_running(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["sfmon", "--job", "monitor_salesforce_limits"])
        with patch.object(sm, "run_once") as mock_run_once, \
             patch("sfmon.orgs.build_connections") as mock_build:
            with pytest.raises(SystemExit) as exc_info:
                sm.main()

        assert exc_info.value.code == 2
        mock_run_once.assert_not_called()
        mock_build.assert_not_called()

    def test_once_dispatches_to_run_once_and_exits_with_its_code(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["sfmon", "--once"])
        with patch.object(sm, "run_once", return_value=0) as mock_run_once:
            with pytest.raises(SystemExit) as exc_info:
                sm.main()

        mock_run_once.assert_called_once_with(job_filter=None)
        assert exc_info.value.code == 0
