"""
Logger Configuration Module

This module configures Python logging for the production monitoring service.
It sets up basic logging with configurable level and timestamp formatting for structured
logging output that can be ingested by various log aggregation platforms
(AWS CloudWatch Logs, Loki, etc.).

Environment Variables:
    - LOG_LEVEL: Logging verbosity level (default: INFO)
                 Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

Exports:
    - logger: Configured logging instance for use across monitoring modules
"""
import logging
import os

# Get log level from environment variable, default to INFO
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Validate log level
VALID_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
if LOG_LEVEL not in VALID_LOG_LEVELS:
    LOG_LEVEL = 'INFO'

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

