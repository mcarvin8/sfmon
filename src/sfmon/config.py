"""
Configuration Module

This module handles loading configuration from a JSON file. The configuration file
allows users to customize schedules, enable functions, and set user-specific settings
without modifying code or using multiple environment variables.

Scheduling Behavior:
    - If NO config file exists: ALL jobs run with their DEFAULT schedules (works out of the box)
    - If config file exists with schedules: OPT-IN approach - only listed jobs run
    - Set a job to "disabled" to explicitly disable it

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
"""
import json
import os
import re
from logger import logger

# Default config file path
DEFAULT_CONFIG_PATH = '/app/sfmon/config.json'

# Cached config to avoid repeated file reads and log messages
_cached_config = None

# Track whether a config file was found and has schedules defined
_config_file_has_schedules = None


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
    
    config_file_path = os.getenv('CONFIG_FILE_PATH', DEFAULT_CONFIG_PATH)
    
    default_config = {
        'schedules': {},
        'integration_user_names': None,
        'exclude_users': []
    }
    
    if not os.path.exists(config_file_path):
        logger.info("Config file not found at %s, all jobs will run with default schedules", config_file_path)
        _cached_config = default_config
        _config_file_has_schedules = False
        return _cached_config
    
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate and merge with defaults
        result = default_config.copy()
        result['schedules'] = config.get('schedules', {})
        result['integration_user_names'] = config.get('integration_user_names')
        result['exclude_users'] = config.get('exclude_users', [])
        
        # Track whether the config file has any schedules defined
        _config_file_has_schedules = bool(result['schedules'])
        
        if _config_file_has_schedules:
            logger.info("Loaded configuration from %s with %d scheduled jobs (opt-in mode)", 
                       config_file_path, len(result['schedules']))
        else:
            logger.info("Loaded configuration from %s, no schedules defined - all jobs will run with defaults", 
                       config_file_path)
        
        _cached_config = result
        return _cached_config
    
    except json.JSONDecodeError as e:
        logger.error("Error parsing config file %s: %s. All jobs will run with default schedules.", config_file_path, e)
        _cached_config = default_config
        _config_file_has_schedules = False
        return _cached_config
    except Exception as e:
        logger.error("Error loading config file %s: %s. All jobs will run with default schedules.", config_file_path, e)
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
    if not schedule_str or schedule_str.lower() in ('disabled', 'none', ''):
        return None
    
    schedule_str = schedule_str.strip()
    
    # Try JSON format first
    if schedule_str.startswith('{'):
        try:
            return json.loads(schedule_str)
        except json.JSONDecodeError:
            pass
    
    # Try standard cron format: "*/5 * * * *"
    cron_parts = schedule_str.split()
    if len(cron_parts) == 5:
        result = {}
        if cron_parts[0] != '*':
            result['minute'] = cron_parts[0]
        if cron_parts[1] != '*':
            result['hour'] = cron_parts[1]
        if cron_parts[2] != '*':
            result['day'] = cron_parts[2]
        if cron_parts[3] != '*':
            result['month'] = cron_parts[3]
        if cron_parts[4] != '*':
            result['day_of_week'] = cron_parts[4]
        return result if result else None
    
    # Try parameter format: "minute=*/5" or "hour=7,minute=30"
    if '=' in schedule_str:
        params = {}
        for part in schedule_str.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.strip()] = value.strip()
        if params:
            return params
    
    # Simple format: assume it's just minutes if it's a single value
    # e.g., "*/5" or "0" or "10,50"
    if re.match(r'^[\d\*\/,]+$', schedule_str):
        return {'minute': schedule_str}
    
    # If we can't parse it, return None to use default
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
    schedules = config.get('schedules', {})
    
    # If no config file or empty schedules, use defaults for all jobs
    if not has_custom_schedules():
        logger.debug("Job %s using default schedule (no custom config)", job_id)
        return default_schedule
    
    # Config file has schedules - use opt-in approach
    # Check if job is explicitly defined in config (case-insensitive)
    config_schedule = schedules.get(job_id.lower())
    
    if config_schedule is None:
        # Job not in config file - skip it (opt-in approach)
        logger.debug("Job %s not defined in config file, skipping (opt-in mode)", job_id)
        return None
    
    # Job is in config - parse the schedule
    parsed = parse_cron_schedule(config_schedule)
    if parsed is None:
        logger.info("Job %s is disabled in config file", job_id)
        return None
    
    logger.info("Job %s enabled with custom schedule: %s", job_id, config_schedule)
    return parsed


def get_integration_user_names():
    """
    Get integration user names from config file.
    
    Returns:
        list or None: List of integration user names, or None if not configured
    """
    config = load_config()
    return config.get('integration_user_names')


def get_exclude_users():
    """
    Get exclude users list from config file.
    
    Returns:
        list: List of user names to exclude from compliance monitoring
    """
    config = load_config()
    exclude_users = config.get('exclude_users', [])
    
    if exclude_users:
        logger.info("Loaded %d users from config file to exclude from compliance monitoring", len(exclude_users))
    
    return exclude_users

