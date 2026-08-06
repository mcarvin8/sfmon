"""Org registry: resolves which Salesforce orgs to monitor and connects to each.

Fleet mode (config.json has a non-empty "orgs" list): each name resolves to a
SALESFORCE_AUTH_URL_<NAME> environment variable, keeping credentials out of the
mounted config file.

Legacy single-org mode (no "orgs" configured): behaves exactly as before —
one org, named by ORG_NAME (or "default" if unset), authenticated via the
plain SALESFORCE_AUTH_URL environment variable.
"""

import os
import re

from logger import logger
from connection_sf import get_salesforce_connection_url


def _sanitize_env_suffix(org_name):
    return re.sub(r"[^A-Z0-9_]", "_", org_name.upper())


def get_org_names():
    """Return the list of org names to monitor.

    Reads "orgs" from config.json (fleet mode). Falls back to a single
    legacy org named by ORG_NAME (or "default") when "orgs" is absent/empty.
    """
    from config import load_config

    orgs = load_config().get("orgs") or []
    if orgs:
        return list(orgs)
    return [os.getenv("ORG_NAME", "default")]


def is_fleet_mode():
    from config import load_config

    return bool(load_config().get("orgs"))


def auth_url_env_var(org_name):
    """Return the environment variable name holding org_name's SFDX auth URL."""
    if is_fleet_mode():
        return f"SALESFORCE_AUTH_URL_{_sanitize_env_suffix(org_name)}"
    return "SALESFORCE_AUTH_URL"


def build_connections():
    """Authenticate to every configured org.

    Returns a dict of org_name -> Salesforce connection. An org whose
    credentials are missing or invalid is logged and skipped rather than
    aborting the whole fleet.
    """
    connections = {}
    for org_name in get_org_names():
        env_var = auth_url_env_var(org_name)
        try:
            connections[org_name] = get_salesforce_connection_url(
                url=os.getenv(env_var)
            )
            logger.info("Connected to org '%s' (%s)", org_name, env_var)
        except Exception as e:
            logger.error(
                "Failed to connect to org '%s' via %s: %s. Skipping this org.",
                org_name,
                env_var,
                e,
            )
    return connections
