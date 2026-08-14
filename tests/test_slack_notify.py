"""Unit tests for slack_notify.py"""

from unittest.mock import MagicMock, patch

import pytest
import requests
import responses as responses_lib


WEBHOOK_URL = "https://hooks.slack.com/services/T000/B000/XXXX"


@pytest.fixture(autouse=True)
def isolated_cache_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SLACK_ALERT_CACHE_DIR", str(tmp_path / "cache"))


class TestSlackWebhookEnabled:
    def test_disabled_when_unset(self, monkeypatch):
        from sfmon.slack_notify import slack_webhook_enabled

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        assert slack_webhook_enabled() is False

    def test_disabled_when_blank(self, monkeypatch):
        from sfmon.slack_notify import slack_webhook_enabled

        monkeypatch.setenv("SLACK_WEBHOOK_URL", "   ")
        assert slack_webhook_enabled() is False

    def test_enabled_when_set(self, monkeypatch):
        from sfmon.slack_notify import slack_webhook_enabled

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        assert slack_webhook_enabled() is True


class TestSendWebhook:
    @responses_lib.activate
    def test_posts_payload(self, monkeypatch):
        from sfmon.slack_notify import _send_webhook

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        responses_lib.add(responses_lib.POST, WEBHOOK_URL, body="ok", status=200)
        _send_webhook({"blocks": []})
        assert len(responses_lib.calls) == 1

    @responses_lib.activate
    def test_noop_when_url_unset(self, monkeypatch):
        from sfmon.slack_notify import _send_webhook

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        _send_webhook({"blocks": []})
        assert len(responses_lib.calls) == 0

    @responses_lib.activate
    def test_non_200_logs_warning_does_not_raise(self, monkeypatch):
        from sfmon.slack_notify import _send_webhook

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        responses_lib.add(
            responses_lib.POST, WEBHOOK_URL, body="invalid_payload", status=400
        )
        _send_webhook({"blocks": []})  # should not raise

    @responses_lib.activate
    def test_request_exception_logs_warning_does_not_raise(self, monkeypatch):
        from sfmon.slack_notify import _send_webhook

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            body=requests.exceptions.ConnectionError("boom"),
        )
        _send_webhook({"blocks": []})  # should not raise


class TestPostWebhookAsync:
    def test_noop_when_disabled(self, monkeypatch):
        from sfmon import slack_notify

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        with patch("sfmon.slack_notify.threading.Thread") as mock_thread:
            slack_notify._post_webhook_async({"blocks": []})
        mock_thread.assert_not_called()

    def test_starts_daemon_thread_when_enabled(self, monkeypatch):
        from sfmon import slack_notify

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        with patch("sfmon.slack_notify.threading.Thread") as mock_thread:
            slack_notify._post_webhook_async({"blocks": []})
        mock_thread.assert_called_once()
        assert mock_thread.call_args.kwargs["daemon"] is True
        mock_thread.return_value.start.assert_called_once()


class TestNotifyOpenedResolved:
    def test_notify_opened_noop_when_disabled(self, monkeypatch):
        from sfmon.slack_notify import notify_alert_opened

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        with patch("sfmon.slack_notify._post_webhook_async") as mock_post:
            notify_alert_opened("prod", "salesforce_limits", "DailyApiRequests", {"title": "x"})
        mock_post.assert_not_called()

    def test_notify_resolved_noop_when_disabled(self, monkeypatch):
        from sfmon.slack_notify import notify_alert_resolved

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        with patch("sfmon.slack_notify._post_webhook_async") as mock_post:
            notify_alert_resolved("prod", "salesforce_limits", "DailyApiRequests", {"title": "x"})
        mock_post.assert_not_called()

    def test_notify_opened_builds_and_sends_payload(self, monkeypatch):
        from sfmon.slack_notify import notify_alert_opened

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        with patch("sfmon.slack_notify._post_webhook_async") as mock_post:
            notify_alert_opened(
                "prod",
                "salesforce_limits",
                "DailyApiRequests",
                {"title": "over limit", "message": "used 95%", "severity": "critical"},
            )
        mock_post.assert_called_once()
        payload = mock_post.call_args.args[0]
        text = payload["blocks"][0]["text"]["text"]
        assert "Alert opened" in text
        assert "prod" in text
        assert "salesforce_limits" in text
        assert "over limit" in text
        assert "used 95%" in text
        assert "critical" in text
        assert "DailyApiRequests" in text

    def test_notify_resolved_builds_and_sends_payload(self, monkeypatch):
        from sfmon.slack_notify import notify_alert_resolved

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        with patch("sfmon.slack_notify._post_webhook_async") as mock_post:
            notify_alert_resolved(
                "prod", "salesforce_limits", "DailyApiRequests", {"title": "back to normal"}
            )
        mock_post.assert_called_once()
        text = mock_post.call_args.args[0]["blocks"][0]["text"]["text"]
        assert "Alert resolved" in text

    def test_title_falls_back_to_item_id(self, monkeypatch):
        from sfmon.slack_notify import notify_alert_opened

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        with patch("sfmon.slack_notify._post_webhook_async") as mock_post:
            notify_alert_opened("prod", "cat", "item-1", {})
        text = mock_post.call_args.args[0]["blocks"][0]["text"]["text"]
        assert "item-1" in text


class TestSyncAlerts:
    def test_noop_and_no_cache_writes_when_disabled(self, monkeypatch):
        from sfmon.slack_notify import sync_alerts
        from sfmon import alert_cache

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        sync_alerts("salesforce_limits", {"DailyApiRequests": {"title": "x"}})
        assert not alert_cache.get_cache_dir().exists()

    def test_first_run_opens_new_alerts(self, monkeypatch):
        from sfmon import slack_notify

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        monkeypatch.setattr(slack_notify, "get_current_org", lambda: "prod")
        with patch("sfmon.slack_notify.notify_alert_opened") as mock_opened, \
             patch("sfmon.slack_notify.notify_alert_resolved") as mock_resolved:
            slack_notify.sync_alerts(
                "salesforce_limits", {"DailyApiRequests": {"title": "over limit"}}
            )
        mock_opened.assert_called_once_with(
            "prod", "salesforce_limits", "DailyApiRequests", {"title": "over limit"}
        )
        mock_resolved.assert_not_called()

    def test_unchanged_alert_does_not_renotify(self, monkeypatch):
        from sfmon import slack_notify

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        monkeypatch.setattr(slack_notify, "get_current_org", lambda: "prod")
        item = {"DailyApiRequests": {"title": "over limit"}}
        with patch("sfmon.slack_notify.notify_alert_opened") as mock_opened:
            slack_notify.sync_alerts("salesforce_limits", item)
        mock_opened.reset_mock()

        with patch("sfmon.slack_notify.notify_alert_opened") as mock_opened2, \
             patch("sfmon.slack_notify.notify_alert_resolved") as mock_resolved2:
            slack_notify.sync_alerts("salesforce_limits", item)
        mock_opened2.assert_not_called()
        mock_resolved2.assert_not_called()

    def test_resolved_alert_notifies_using_cached_detail(self, monkeypatch):
        from sfmon import slack_notify

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        monkeypatch.setattr(slack_notify, "get_current_org", lambda: "prod")
        with patch("sfmon.slack_notify.notify_alert_opened"):
            slack_notify.sync_alerts(
                "salesforce_limits", {"DailyApiRequests": {"title": "over limit"}}
            )

        with patch("sfmon.slack_notify.notify_alert_opened") as mock_opened, \
             patch("sfmon.slack_notify.notify_alert_resolved") as mock_resolved:
            slack_notify.sync_alerts("salesforce_limits", {})
        mock_opened.assert_not_called()
        mock_resolved.assert_called_once_with(
            "prod", "salesforce_limits", "DailyApiRequests", {"title": "over limit"}
        )

    def test_org_scoping_keeps_caches_independent(self, monkeypatch):
        from sfmon import slack_notify

        monkeypatch.setenv("SLACK_WEBHOOK_URL", WEBHOOK_URL)
        monkeypatch.setattr(slack_notify, "get_current_org", lambda: "prod")
        with patch("sfmon.slack_notify.notify_alert_opened"):
            slack_notify.sync_alerts(
                "salesforce_limits", {"DailyApiRequests": {"title": "over limit"}}
            )

        monkeypatch.setattr(slack_notify, "get_current_org", lambda: "sandbox")
        with patch("sfmon.slack_notify.notify_alert_opened") as mock_opened:
            slack_notify.sync_alerts(
                "salesforce_limits", {"DailyApiRequests": {"title": "over limit"}}
            )
        mock_opened.assert_called_once()
