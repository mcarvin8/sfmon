"""Org registry: resolves which Salesforce orgs to monitor and connects to each.

Fleet mode (config.json has a non-empty "orgs" list): each name resolves to a
SALESFORCE_AUTH_URL_<NAME> environment variable, keeping credentials out of the
mounted config file.

Legacy single-org mode (no "orgs" configured): behaves exactly as before —
one org, named by ORG_NAME (or "default" if unset), authenticated via the
plain SALESFORCE_AUTH_URL environment variable.

Secrets backend (optional): set SECRETS_BACKEND=aws to fetch the auth URL
from AWS Secrets Manager instead of the environment, using the same
SALESFORCE_AUTH_URL[_<NAME>] name (optionally prefixed via AWS_SECRETS_PREFIX)
as the secret name. See docs/ENVIRONMENT.md.
"""

import os
import re
import threading

from .connection_sf import get_salesforce_connection_url
from .logger import logger

SUPPORTED_SECRETS_BACKENDS = {"aws"}

# Live connection registry: org_name -> Salesforce connection. Lives here
# rather than in salesforce_monitoring.py because that module runs as
# __main__ under `python -m`, so importing it from elsewhere would load a
# second copy with an empty registry.
_connections = {}
_connections_lock = threading.Lock()
# Serializes logins in reconnect() without holding _connections_lock during
# the network call, so other orgs' jobs can still look up their connection.
_reconnect_lock = threading.Lock()


def _sanitize_env_suffix(org_name):
    return re.sub(r"[^A-Z0-9_]", "_", org_name.upper())


def get_org_names():
    """Return the list of org names to monitor.

    Reads "orgs" from config.json (fleet mode). Falls back to a single
    legacy org named by ORG_NAME (or "default") when "orgs" is absent/empty.
    """
    from .config import load_config

    orgs = load_config().get("orgs") or []
    if orgs:
        return list(orgs)
    return [os.getenv("ORG_NAME", "default")]


def is_fleet_mode():
    from .config import load_config

    return bool(load_config().get("orgs"))


def auth_url_env_var(org_name):
    """Return the environment variable name holding org_name's SFDX auth URL."""
    if is_fleet_mode():
        return f"SALESFORCE_AUTH_URL_{_sanitize_env_suffix(org_name)}"
    return "SALESFORCE_AUTH_URL"


def resolve_auth_url(org_name):
    """Resolve org_name's SFDX auth URL from the configured source.

    Defaults to the plain environment variable (SALESFORCE_AUTH_URL or
    SALESFORCE_AUTH_URL_<NAME>). If SECRETS_BACKEND is set, fetches from that
    backend instead, using the same name (optionally prefixed via
    AWS_SECRETS_PREFIX for the "aws" backend) as the secret identifier.
    """
    env_var = auth_url_env_var(org_name)
    backend = os.getenv("SECRETS_BACKEND", "").strip().lower()
    if not backend:
        return os.getenv(env_var)

    if backend not in SUPPORTED_SECRETS_BACKENDS:
        raise ValueError(
            f"Unsupported SECRETS_BACKEND '{backend}'. Supported: "
            f"{', '.join(sorted(SUPPORTED_SECRETS_BACKENDS))}"
        )

    try:
        from .secrets_manager import get_secret_aws
    except ImportError as e:
        raise RuntimeError(
            'SECRETS_BACKEND=aws requires the boto3 package. Install with: pip install "sfmon[aws]"'
        ) from e

    secret_name = os.getenv("AWS_SECRETS_PREFIX", "") + env_var
    return get_secret_aws(secret_name)


def build_connections():
    """Authenticate to every configured org.

    Returns a dict of org_name -> Salesforce connection. An org whose
    credentials are missing or invalid is logged and skipped rather than
    aborting the whole fleet. The result also becomes the live connection
    registry read by get_connection() and refreshed by reconnect().
    """
    connections = {}
    for org_name in get_org_names():
        env_var = auth_url_env_var(org_name)
        try:
            connections[org_name] = get_salesforce_connection_url(url=resolve_auth_url(org_name))
            logger.info("Connected to org '%s' (%s)", org_name, env_var)
        except Exception as e:
            logger.error(
                "Failed to connect to org '%s' via %s: %s. Skipping this org.",
                org_name,
                env_var,
                e,
            )
    with _connections_lock:
        _connections.clear()
        _connections.update(connections)
    return connections


def get_connection(org_name):
    """Return org_name's current Salesforce connection, or None if not connected.

    Scheduled jobs call this on every run instead of holding on to the
    connection they were scheduled with, so a reconnect() is picked up by
    every later run.
    """
    with _connections_lock:
        return _connections.get(org_name)


def reconnect(org_name, stale=None):
    """Re-authenticate org_name and store the new connection in the registry.

    If stale is given and the registry already holds a different connection
    (another job refreshed this org first), that connection is returned
    without logging in again — so jobs that hit the same expired session at
    the same time trigger one token refresh, not one each.

    Raises whatever get_salesforce_connection_url raises if login fails.
    """
    with _reconnect_lock:
        current = get_connection(org_name)
        if stale is not None and current is not None and current is not stale:
            return current
        connection = get_salesforce_connection_url(url=resolve_auth_url(org_name))
        with _connections_lock:
            _connections[org_name] = connection
        logger.info("Re-authenticated to org '%s'.", org_name)
        return connection
