"""
Configuration Module

This module handles loading configuration from a JSON file. The configuration file
allows users to customize schedules, enable functions, and set user-specific settings
without modifying code or using multiple environment variables.

IMPORTANT: This module uses an OPT-IN approach for job scheduling.
    - Only jobs explicitly defined in the config file will run
    - Jobs not listed in the config file will be SKIPPED
    - Set a job to "disabled" to explicitly disable it (useful for documentation)

Configuration File Location:
    - Default: /app/sfmon/config.json (inside container)
    - Can be overridden via CONFIG_FILE_PATH environment variable
    - If file doesn't exist or schedules section is empty, NO jobs will run

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


def load_config():
    """
    Load configuration from JSON file.
    
    Returns:
        dict: Configuration dictionary with schedules, integration_user_names, and exclude_users
    """
    config_file_path = os.getenv('CONFIG_FILE_PATH', DEFAULT_CONFIG_PATH)
    
    default_config = {
        'schedules': {},
        'integration_user_names': None,
        'exclude_users': []
    }
    
    if not os.path.exists(config_file_path):
        logger.info("Config file not found at %s, using defaults", config_file_path)
        return default_config
    
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate and merge with defaults
        result = default_config.copy()
        result['schedules'] = config.get('schedules', {})
        result['integration_user_names'] = config.get('integration_user_names')
        result['exclude_users'] = config.get('exclude_users', [])
        
        logger.info("Loaded configuration from %s", config_file_path)
        return result
    
    except json.JSONDecodeError as e:
        logger.error("Error parsing config file %s: %s. Using defaults.", config_file_path, e)
        return default_config
    except Exception as e:
        logger.error("Error loading config file %s: %s. Using defaults.", config_file_path, e)
        return default_config


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
    Get schedule for a job from config file (OPT-IN approach).
    
    IMPORTANT: Only jobs explicitly defined in the config file will run.
    Jobs not listed in the config file will be SKIPPED.
    
    Args:
        job_id: The job identifier
        default_schedule: Default schedule dict for CronTrigger (used as fallback format hint only)
        
    Returns:
        dict or None: Schedule configuration for CronTrigger, None if not in config or disabled
    """
    config = load_config()
    schedules = config.get('schedules', {})
    
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
    
    logger.info("Job %s enabled with schedule: %s", job_id, config_schedule)
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

