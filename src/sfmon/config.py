"""
Configuration Module

This module handles loading configuration from a JSON file. The configuration file
allows users to customize schedules, enable functions, and set user-specific settings
without modifying code or using multiple environment variables.

Scheduling Behavior:
    - If NO config file exists: Jobs with a default schedule run; jobs with default None are skipped (opt-in only).
    - If config file exists with empty schedules: Same as no file (defaults for jobs that have them).
    - If config file has a non-empty schedules object: OPT-IN — only listed jobs run (use suggested crons in docs for file-based jobs).
    - Set a job to "disabled" to explicitly disable it when it appears under schedules.
    - If config file has a "preset" key: The named preset's jobs are used as the base schedule (opt-in mode).
      Explicit schedules override preset entries; both together are valid.

Configuration File Location:
    - Default: /app/sfmon/config.json (inside container)
    - Can be overridden via CONFIG_FILE_PATH environment variable

Configuration Structure:
    {
        "schedules": {
            "monitor_salesforce_limits": "*/5",
            "daily_analyse_bulk_api": "hour=7,minute=30",
            "get_salesforce_instance": "*/5"
        },
        "integration_user_names": ["User 1", "User 2"],
        "exclude_users": ["Admin User", "Integration User"]
    }

Preset Structure (alternative to a full schedules block):
    {
        "preset": "ops"
    }

    Valid preset values: "ops", "audit", "tech-debt"
    Combine with schedules to add file-based opt-in jobs on top of a preset:
    {
        "preset": "tech-debt",
        "schedules": {
            "monitor_pmd_code_smells": "hour=3,minute=10",
            "monitor_minimal_perm_sets": "hour=2,minute=20"
        }
    }
"""

import json
import os
import re
from logger import logger

# Default config file path
DEFAULT_CONFIG_PATH = "/app/sfmon/config.json"

# Cached config to avoid repeated file reads and log messages
_cached_config = None

# Track whether a config file was found and has schedules defined
_config_file_has_schedules = None

# ---------------------------------------------------------------------------
# Preset definitions — each maps job_id → cron string using default timings
# ---------------------------------------------------------------------------
PRESETS = {
    "ops": {
        "monitor_apex_flex_queue": "*/5",
        "hourly_analyse_bulk_api": "minute=5",
        "get_deployment_status": "minute=55",
        "get_salesforce_ept_and_apt": "hour=6,minute=0",
        "async_apex_job_status": "hour=6,minute=30",
        "monitor_apex_execution_time": "hour=6,minute=45",
        "async_apex_execution_summary": "hour=7,minute=0",
        "concurrent_apex_errors": "hour=7,minute=15",
        "expose_apex_exception_metrics": "hour=7,minute=25",
        "expose_concurrent_long_running_apex_errors": "hour=7,minute=35",
        "daily_analyse_bulk_api": "hour=7,minute=30",
    },
    "audit": {
        "hourly_observe_user_querying_large_records": "minute=25",
        "monitor_forbidden_profile_assignments": "minute=35",
        "hourly_report_export_records": "minute=45",
        "monitor_login_events": "hour=6,minute=15",
        "geolocation": "hour=8,minute=0",
        "expose_suspicious_records": "hour=8,minute=15",
        "monitor_org_wide_sharing_settings": "hour=8,minute=30",
    },
    "tech-debt": {
        "unassigned_permission_sets": "hour=2,minute=0",
        "perm_sets_limited_users": "hour=2,minute=15",
        "profile_assignment_under5": "hour=2,minute=30",
        "profile_no_active_users": "hour=2,minute=45",
        "apex_classes_api_version": "hour=3,minute=0",
        "apex_used_limits_monitoring": "hour=3,minute=5",
        "apex_triggers_api_version": "hour=3,minute=15",
        "security_health_check": "hour=3,minute=30",
        "salesforce_health_risks": "hour=3,minute=45",
        "workflow_rules_monitoring": "hour=4,minute=0",
        "dormant_salesforce_users": "hour=4,minute=15",
        "dormant_portal_users": "hour=4,minute=30",
        "total_queues_per_object": "hour=4,minute=45",
        "queues_with_no_members": "hour=5,minute=0",
        "queues_with_zero_open_cases": "hour=5,minute=15",
        "public_groups_with_no_members": "hour=5,minute=30",
        "dashboards_with_inactive_users": "hour=5,minute=45",
        "scheduled_apex_jobs_monitoring": "hour=5,minute=55",
    },
}


def load_config(force_reload=False):
    """
    Load configuration from JSON file.

    Args:
        force_reload: If True, reload config from file even if cached

    Returns:
        dict: Configuration dictionary with schedules, integration_user_names, and exclude_users
    """
    global _cached_config, _config_file_has_schedules

    if _cached_config is not None and not force_reload:
        return _cached_config

    config_file_path = os.getenv("CONFIG_FILE_PATH", DEFAULT_CONFIG_PATH)

    default_config = {
        "schedules": {},
        "integration_user_names": None,
        "exclude_users": [],
        "preset": None,
    }

    if not os.path.exists(config_file_path):
        logger.info(
            "Config file not found at %s, all jobs will run with default schedules",
            config_file_path,
        )
        _cached_config = default_config
        _config_file_has_schedules = False
        return _cached_config

    try:
        with open(config_file_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Validate and merge with defaults
        result = default_config.copy()
        result["schedules"] = config.get("schedules", {})
        result["integration_user_names"] = config.get("integration_user_names")
        result["exclude_users"] = config.get("exclude_users", [])
        result["preset"] = None

        # Expand preset if specified, merging with any explicit schedules (explicit wins)
        preset_name = config.get("preset", "").strip().lower()
        if preset_name:
            if preset_name in PRESETS:
                merged = {**PRESETS[preset_name], **result["schedules"]}
                result["schedules"] = merged
                result["preset"] = preset_name
                logger.info(
                    "Applying preset '%s' (%d jobs) from %s",
                    preset_name,
                    len(merged),
                    config_file_path,
                )
            else:
                logger.warning(
                    "Unknown preset '%s' in %s. Valid presets: %s. Ignoring preset.",
                    preset_name,
                    config_file_path,
                    ", ".join(PRESETS.keys()),
                )

        # Track whether the config file has any schedules defined
        _config_file_has_schedules = bool(result["schedules"])

        if _config_file_has_schedules:
            logger.info(
                "Loaded configuration from %s with %d scheduled jobs (opt-in mode)",
                config_file_path,
                len(result["schedules"]),
            )
        else:
            logger.info(
                "Loaded configuration from %s, no schedules defined - all jobs will run with defaults",
                config_file_path,
            )

        _cached_config = result
        return _cached_config

    except json.JSONDecodeError as e:
        logger.error(
            "Error parsing config file %s: %s. All jobs will run with default schedules.",
            config_file_path,
            e,
        )
        _cached_config = default_config
        _config_file_has_schedules = False
        return _cached_config
    except Exception as e:
        logger.error(
            "Error loading config file %s: %s. All jobs will run with default schedules.",
            config_file_path,
            e,
        )
        _cached_config = default_config
        _config_file_has_schedules = False
        return _cached_config


def has_custom_schedules():
    """
    Check if a config file with schedules was loaded.

    Returns:
        bool: True if config file exists and has schedules defined (opt-in mode),
              False if no config file or empty schedules (use defaults)
    """
    global _config_file_has_schedules
    if _config_file_has_schedules is None:
        load_config()
    return _config_file_has_schedules


def get_active_preset():
    """
    Return the name of the active preset, or None if no preset is set.

    Returns:
        str or None: Preset name (e.g. 'ops', 'audit', 'tech-debt'), or None
    """
    config = load_config()
    return config.get("preset")


def _parse_json_cron(schedule_str):
    """Parse JSON cron format: '{"minute": "*/5"}'."""
    if not schedule_str.strip().startswith("{"):
        return None
    try:
        return json.loads(schedule_str)
    except json.JSONDecodeError:
        return None


def _parse_five_part_cron(schedule_str):
    """Parse standard 5-part cron: '*/5 * * * *'."""
    parts = schedule_str.split()
    if len(parts) != 5:
        return None
    result = {}
    keys = ("minute", "hour", "day", "month", "day_of_week")
    for key, value in zip(keys, parts):
        if value != "*":
            result[key] = value
    return result if result else None


def _parse_key_value_cron(schedule_str):
    """Parse key=value format: 'minute=*/5' or 'hour=7,minute=30'."""
    if "=" not in schedule_str:
        return None
    params = {}
    for part in schedule_str.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            params[key.strip()] = value.strip()
    return params if params else None


def _parse_simple_minute_cron(schedule_str):
    """Parse simple minute format: '*/5' or '10,50'."""
    if re.match(r"^[\d\*\/,]+$", schedule_str):
        return {"minute": schedule_str}
    return None


def parse_cron_schedule(schedule_str):
    """
    Parse a cron schedule string into CronTrigger parameters.

    Supports multiple formats:
    1. Standard cron: "*/5 * * * *" -> minute='*/5'
    2. Parameter format: "minute=*/5" or "hour=7,minute=30"
    3. JSON format: '{"minute": "*/5"}' or '{"hour": "7", "minute": "30"}'
    4. Simple minute: "*/5" -> minute='*/5'

    Args:
        schedule_str: Cron schedule string in one of the supported formats

    Returns:
        dict or None: Keyword arguments for CronTrigger, None if disabled
    """
    if not schedule_str or schedule_str.lower().strip() in ("disabled", "none", ""):
        return None
    s = schedule_str.strip()

    parsed = (
        _parse_json_cron(s)
        or _parse_five_part_cron(s)
        or _parse_key_value_cron(s)
        or _parse_simple_minute_cron(s)
    )
    if parsed is not None:
        return parsed
    logger.warning("Could not parse schedule string: %s, using default", schedule_str)
    return None


def get_schedule_from_config(job_id, default_schedule):
    """
    Get schedule for a job from config file or use default.

    Behavior:
        - If NO config file exists (or schedules is empty): Use default_schedule
        - If config file has schedules defined: OPT-IN - only listed jobs run
        - If job is set to "disabled" in config: Skip the job

    Args:
        job_id: The job identifier
        default_schedule: Default schedule dict for CronTrigger

    Returns:
        dict or None: Schedule configuration for CronTrigger, None if disabled
    """
    config = load_config()
    schedules = config.get("schedules", {})

    # If no config file or empty schedules, use built-in default per job (may be None = opt-in only)
    if not has_custom_schedules():
        if default_schedule is None:
            logger.debug(
                "Job %s skipped (opt-in only; add to config schedules to enable)",
                job_id,
            )
        else:
            logger.debug("Job %s using default schedule (no custom config)", job_id)
        return default_schedule

    # Config file has schedules - use opt-in approach
    # Check if job is explicitly defined in config (case-insensitive)
    config_schedule = schedules.get(job_id.lower())

    if config_schedule is None:
        # Job not in config file - skip it (opt-in approach)
        logger.debug(
            "Job %s not defined in config file, skipping (opt-in mode)", job_id
        )
        return None

    # Job is in config - parse the schedule
    parsed = parse_cron_schedule(config_schedule)
    if parsed is None:
        logger.info("Job %s is disabled in config file", job_id)
        return None

    logger.info("Job %s enabled with custom schedule: %s", job_id, config_schedule)
    return parsed


def get_always_on_schedule(job_id, default_schedule):
    """
    Get schedule for an always-on job. Always returns default_schedule unless
    the job is explicitly listed in the config schedules block (which allows
    overriding or disabling it via "disabled").

    Args:
        job_id: The job identifier
        default_schedule: Default schedule dict for CronTrigger

    Returns:
        dict or None: Schedule configuration for CronTrigger, None if explicitly disabled
    """
    config = load_config()
    schedules = config.get("schedules", {})

    if job_id.lower() in schedules:
        parsed = parse_cron_schedule(schedules[job_id.lower()])
        if parsed is None:
            logger.info("Always-on job %s explicitly disabled in config file", job_id)
        else:
            logger.info(
                "Always-on job %s using custom schedule from config: %s",
                job_id,
                schedules[job_id.lower()],
            )
        return parsed

    logger.debug("Always-on job %s using default schedule", job_id)
    return default_schedule


def get_integration_user_names():
    """
    Get integration user names from config file.

    Returns:
        list or None: List of integration user names, or None if not configured
    """
    config = load_config()
    return config.get("integration_user_names")


def get_exclude_users():
    """
    Get exclude users list from config file.

    Returns:
        list: List of user names to exclude from compliance monitoring
    """
    config = load_config()
    exclude_users = config.get("exclude_users", [])

    if exclude_users:
        logger.info(
            "Loaded %d users from config file to exclude from compliance monitoring",
            len(exclude_users),
        )

    return exclude_users
