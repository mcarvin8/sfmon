"""
Salesforce Connection Module

This module handles authentication and connection establishment to Salesforce
organizations using the OAuth2 refresh token flow and Simple Salesforce library.
It provides secure, token-based authentication via SFDX URL method, with no
dependency on the Salesforce CLI.

Functions:
    - get_salesforce_connection_url: Authenticates and returns a Salesforce connection object

Requirements:
    - Valid SFDX authentication URL with credentials
"""

import re

import requests
from simple_salesforce import Salesforce
from simple_salesforce.api import DEFAULT_API_VERSION

from .logger import logger

# SFDX auth URL format: force://<clientId>:<clientSecret>:<refreshToken>@<instanceUrl>
# clientSecret is empty for public/PKCE connected apps (e.g. force://PlatformCLI::<token>@...)
SFDX_URL_RE = re.compile(r"^force://([^:]+):([^:]*):([^@]+)@(.+)$")


def get_salesforce_connection_url(url):
    """
    Connect to Salesforce via the OAuth2 refresh token flow using an SFDX auth URL.

    Args:
        url: SFDX authentication URL (must be a valid URL string)

    Returns:
        Salesforce connection object

    Raises:
        ValueError: If URL is None, empty, or not a valid SFDX auth URL
        requests.HTTPError: If the OAuth token request fails
        KeyError: If expected data is missing from the OAuth response
    """
    if not url:
        raise ValueError(
            "SFDX authentication URL is required but was not provided. "
            "Ensure environment variable is set."
        )

    match = SFDX_URL_RE.match(url)
    if not match:
        raise ValueError(
            "Invalid SFDX auth URL format. Expected "
            "force://<clientId>:<clientSecret>:<refreshToken>@<instanceUrl>"
        )

    client_id, client_secret, refresh_token, instance_url = match.groups()

    token_payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    if client_secret:
        token_payload["client_secret"] = client_secret

    try:
        response = requests.post(
            f"{instance_url}/services/oauth2/token",
            data=token_payload,
            timeout=30,
        )
        response.raise_for_status()
        token_data = response.json()

        access_token = token_data["access_token"]
        actual_instance_url = token_data["instance_url"]
        domain = "test" if "sandbox" in actual_instance_url else "login"
        api_version = _get_latest_api_version(actual_instance_url, access_token)

        return Salesforce(
            instance_url=actual_instance_url,
            session_id=access_token,
            domain=domain,
            version=api_version,
        )

    except requests.HTTPError as e:
        logger.error("Error logging into Salesforce: %s", e)
        logger.error("OAuth response: %s", response.text)
        raise
    except KeyError as e:
        logger.error("Missing expected key in OAuth response: %s", e)
        raise


def _get_latest_api_version(instance_url, access_token):
    """
    Look up the highest REST API version the org's instance supports.

    Falls back to simple_salesforce's bundled default if the discovery
    call fails, so a transient error here never blocks the connection.
    """
    try:
        response = requests.get(
            f"{instance_url}/services/data/",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        response.raise_for_status()
        versions = response.json()
        return max(versions, key=lambda v: float(v["version"]))["version"]
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        logger.warning(
            "Could not determine org API version, using simple_salesforce default: %s",
            e,
        )
        return DEFAULT_API_VERSION
