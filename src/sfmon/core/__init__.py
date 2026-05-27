"""
Core (Always-On) Monitoring Package

Baseline functions that run regardless of preset or opt-in mode. They can be
explicitly disabled by setting the job id to "disabled" in the config schedules block.
"""

import sys
import os

_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from .overall_sf_org import (
    monitor_salesforce_limits,
    get_salesforce_licenses,
    get_salesforce_instance,
)

__all__ = [
    "monitor_salesforce_limits",
    "get_salesforce_licenses",
    "get_salesforce_instance",
]
