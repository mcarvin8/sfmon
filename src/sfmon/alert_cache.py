"""
Alert Cache Module

Persists the set of currently-active alert items per (org, category) to disk
as JSON, so slack_notify.sync_alerts() can diff the current run against the
previous one and only notify on state transitions (opened / resolved) instead
of re-alerting on every scheduler tick. Disk (rather than in-memory) state is
needed because SFMon runs both as a long-lived daemon (BlockingScheduler) and
as a `--once` CI-cron job where the process exits after every run — only a
file survives between those invocations.

Cache Strategy:
    - One JSON file per (org, category): {cache_dir}/{org}__{category}.json
    - File holds the full active_items dict from the most recent sync_alerts()
      call that changed something (see slack_notify.sync_alerts)
    - Writes are atomic (temp file + rename) to avoid a torn read if the
      process is killed mid-write
    - A missing or corrupt cache file is treated as "no prior alerts" —
      corrupt files log a warning and are ignored rather than crashing a job

Environment Variables:
    - SLACK_ALERT_CACHE_DIR: Directory for alert cache JSON files (default:
      ./sfmon_alert_cache, relative to the current working directory — this
      matches the Docker image's WORKDIR and is the natural default for a
      pip-installed console script run from a project directory)

Functions:
    - get_cache_dir: Resolve the configured cache directory
    - load_active_items: Read the previously-cached active items for (org, category)
    - save_active_items: Atomically write the current active items for (org, category)
"""

import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_SAFE_KEY_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def get_cache_dir() -> Path:
    """Resolve the alert cache directory (SLACK_ALERT_CACHE_DIR, default
    ./sfmon_alert_cache). Relative paths resolve against the current working
    directory rather than this module's location."""
    cache_dir = Path(os.getenv("SLACK_ALERT_CACHE_DIR", "sfmon_alert_cache"))
    if not cache_dir.is_absolute():
        cache_dir = Path.cwd() / cache_dir
    return cache_dir


def _safe_key(value: str) -> str:
    """Sanitize an org/category value for use in a filename."""
    return _SAFE_KEY_RE.sub("_", value) or "_"


def _cache_path(org: str, category: str) -> Path:
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{_safe_key(org)}__{_safe_key(category)}.json"


def load_active_items(org: str, category: str) -> dict:
    """Return the previously-cached {item_id: detail} dict for (org, category),
    or {} if no cache exists yet or the cache file is corrupt/unreadable."""
    cache_file = _cache_path(org, category)
    if not cache_file.exists():
        return {}
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("Alert cache %s did not contain a JSON object", cache_file)
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load alert cache %s: %s", cache_file, e)
        return {}


def save_active_items(org: str, category: str, active_items: dict) -> None:
    """Atomically overwrite the cache for (org, category) with active_items."""
    cache_file = _cache_path(org, category)
    temp_file = cache_file.with_suffix(".json.tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(active_items, f, ensure_ascii=False)
        temp_file.replace(cache_file)
    except OSError as e:
        logger.warning("Failed to save alert cache %s: %s", cache_file, e)
