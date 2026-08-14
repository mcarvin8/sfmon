"""
Optional Slack webhook alerting for threshold/compliance breaches.

When SLACK_WEBHOOK_URL is set, sync_alerts() posts to Slack when an alert
item newly appears ("opened") or disappears ("resolved") for a given
(org, category) pair — an edge-triggered pattern any collector can reuse.
Silent when nothing changed, so a metric that's been over threshold for six
hours doesn't re-alert on every scheduler tick; state is diffed against
alert_cache.py's on-disk snapshot from the last run that changed something.

An alert "item" is any dict with at least a "title" key describing the
problem; "message" and "severity" are optional and rendered into the Slack
message if present. A boolean threshold check (e.g. one Salesforce limit
over its usage percentage) is just a one-item dict keyed by a fixed id (the
limit name); a list-shaped check (e.g. forbidden profile assignments) is a
dict keyed by each violation's natural id. An empty dict means nothing is
currently breaching for that category.

Environment Variables:
    - SLACK_WEBHOOK_URL: Slack incoming webhook URL. Unset disables alerting
      entirely — sync_alerts() becomes a no-op with no cache reads/writes,
      so collectors can call it unconditionally at no cost when disabled.

Functions:
    - slack_webhook_enabled: Whether SLACK_WEBHOOK_URL is set
    - sync_alerts: Diff active_items against cache and notify only on
      opened/resolved transitions — the main entry point for collectors
    - notify_alert_opened / notify_alert_resolved: Lower-level single-item
      notifications, used internally by sync_alerts
"""

import logging
import os
import threading

import requests

from .alert_cache import load_active_items, save_active_items
from .org_gauge import get_current_org

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"


def slack_webhook_enabled() -> bool:
    return bool(os.getenv(SLACK_WEBHOOK_ENV, "").strip())


def _get_webhook_url() -> str:
    return os.getenv(SLACK_WEBHOOK_ENV, "").strip()


def _send_webhook(payload: dict) -> None:
    """Synchronous POST to the configured webhook. Never raises — failures
    are logged, not propagated, so a Slack outage can't break a scheduled job."""
    url = _get_webhook_url()
    if not url:
        return
    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if r.status_code != 200:
            logger.warning(
                "Slack webhook returned %s: %s", r.status_code, (r.text or "")[:500]
            )
    except requests.RequestException as e:
        logger.warning("Slack webhook request failed: %s", e)


def _post_webhook_async(payload: dict) -> None:
    """Fire-and-forget the webhook POST on a daemon thread so a slow or
    unreachable Slack endpoint never blocks a scheduled collector job."""
    if not _get_webhook_url():
        return
    threading.Thread(target=_send_webhook, args=(payload,), daemon=True).start()


def _build_payload(
    emoji: str, headline: str, org: str, category: str, item_id: str, detail: dict
) -> dict:
    title = str(detail.get("title", item_id))[:200]
    message = detail.get("message", "")
    severity = detail.get("severity", "warning")
    text = f"{emoji} *{headline}* — *{org or 'unknown org'}* / `{category}`\n*{title}*"
    if message:
        text += f"\n{str(message)[:1000]}"
    text += f"\n• Severity: `{severity}`\n• ID: `{item_id}`"
    return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]}


def notify_alert_opened(org: str, category: str, item_id: str, detail: dict) -> None:
    """Post Slack message when an alert item newly appears for (org, category)."""
    if not slack_webhook_enabled():
        return
    payload = _build_payload("\U0001f534", "Alert opened", org, category, item_id, detail)
    _post_webhook_async(payload)
    logger.info("Slack: queued alert opened for %s/%s (org=%s)", category, item_id, org)


def notify_alert_resolved(org: str, category: str, item_id: str, detail: dict) -> None:
    """Post Slack message when a previously-active alert item disappears."""
    if not slack_webhook_enabled():
        return
    payload = _build_payload(
        "\U0001f7e2", "Alert resolved", org, category, item_id, detail
    )
    _post_webhook_async(payload)
    logger.info("Slack: queued alert resolved for %s/%s (org=%s)", category, item_id, org)


def sync_alerts(category: str, active_items: dict) -> None:
    """Diff active_items against the last known state for (current org,
    category) and notify Slack only for items that newly opened or newly
    resolved; unchanged items are silent.

    active_items: {item_id: {"title": str, "message"?: str, "severity"?: str}}
    """
    if not slack_webhook_enabled():
        return

    org = get_current_org()
    previous = load_active_items(org, category)
    previous_ids = set(previous)
    current_ids = set(active_items)

    opened = current_ids - previous_ids
    resolved = previous_ids - current_ids

    for item_id in opened:
        notify_alert_opened(org, category, item_id, active_items[item_id])
    for item_id in resolved:
        notify_alert_resolved(org, category, item_id, previous[item_id])

    if opened or resolved:
        save_active_items(org, category, active_items)
