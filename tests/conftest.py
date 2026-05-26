"""Shared fixtures for sfmon unit tests."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset config module cache between tests."""
    import config
    config._cached_config = None
    config._config_file_has_schedules = None
    yield
    config._cached_config = None
    config._config_file_has_schedules = None


@pytest.fixture
def mock_sf():
    """Return a mock Simple Salesforce connection object."""
    sf = MagicMock()
    sf.query_all.return_value = {"records": [], "done": True, "totalSize": 0}
    sf.toolingexecute.return_value = {"records": [], "done": True, "totalSize": 0}
    sf.limits.return_value = {}
    return sf


@pytest.fixture
def sample_sf_records():
    """Factory for building mock SOQL records."""
    def _make(fields):
        return [dict(attributes={"type": "SObject"}, **fields)]
    return _make
