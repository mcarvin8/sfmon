"""Unit tests for constants.py."""

import os
import pytest


class TestTimeoutConstants:
    def test_default_requests_timeout(self, monkeypatch):
        monkeypatch.delenv("REQUESTS_TIMEOUT_SECONDS", raising=False)
        import importlib
        import constants
        importlib.reload(constants)
        assert constants.REQUESTS_TIMEOUT_SECONDS == 300

    def test_custom_requests_timeout(self, monkeypatch):
        monkeypatch.setenv("REQUESTS_TIMEOUT_SECONDS", "60")
        import importlib
        import constants
        importlib.reload(constants)
        assert constants.REQUESTS_TIMEOUT_SECONDS == 60

    def test_default_query_timeout(self, monkeypatch):
        monkeypatch.delenv("QUERY_TIMEOUT_SECONDS", raising=False)
        import importlib
        import constants
        importlib.reload(constants)
        assert constants.QUERY_TIMEOUT_SECONDS == 30

    def test_custom_query_timeout(self, monkeypatch):
        monkeypatch.setenv("QUERY_TIMEOUT_SECONDS", "45")
        import importlib
        import constants
        importlib.reload(constants)
        assert constants.QUERY_TIMEOUT_SECONDS == 45


class TestAllowedSectionsActions:
    @pytest.fixture(autouse=True)
    def _import(self):
        import constants as c
        self.c = c

    def test_is_dict(self):
        assert isinstance(self.c.ALLOWED_SECTIONS_ACTIONS, dict)

    def test_manage_users_section_exists(self):
        assert "Manage Users" in self.c.ALLOWED_SECTIONS_ACTIONS

    def test_manage_users_contains_expected_actions(self):
        actions = self.c.ALLOWED_SECTIONS_ACTIONS["Manage Users"]
        for expected in ("activateduser", "createduser", "PermSetAssign", "deactivateduser"):
            assert expected in actions

    def test_empty_section_key_exists(self):
        assert "" in self.c.ALLOWED_SECTIONS_ACTIONS
        assert "createScratchOrg" in self.c.ALLOWED_SECTIONS_ACTIONS[""]

    def test_all_values_are_lists(self):
        for section, actions in self.c.ALLOWED_SECTIONS_ACTIONS.items():
            assert isinstance(actions, list), f"Section '{section}' value is not a list"

    def test_groups_section(self):
        assert "groupMembership" in self.c.ALLOWED_SECTIONS_ACTIONS["Groups"]
