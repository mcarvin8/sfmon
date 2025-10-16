"""
Logger Configuration Module

This module configures Python logging for the production monitoring service.
It sets up basic logging with INFO level and timestamp formatting for structured
logging output that can be ingested by various log aggregation platforms
(AWS CloudWatch Logs, Loki, etc.).

Exports:
    - logger: Configured logging instance for use across monitoring modules
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

