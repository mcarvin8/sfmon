"""
Core (Always-On) Monitoring Package

Baseline functions that run regardless of preset or opt-in mode. They can be
explicitly disabled by setting the job id to "disabled" in the config schedules block.
"""

from .overall_sf_org import (
    get_salesforce_instance,
    get_salesforce_licenses,
    monitor_salesforce_limits,
)

__all__ = [
    "monitor_salesforce_limits",
    "get_salesforce_licenses",
    "get_salesforce_instance",
]
