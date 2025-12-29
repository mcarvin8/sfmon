"""
Salesforce Connection Module

This module handles authentication and connection establishment to Salesforce
organizations using the Salesforce CLI (sf) and Simple Salesforce library.
It provides secure, token-based authentication via SFDX URL method.

Functions:
    - get_salesforce_connection_url: Authenticates and returns a Salesforce connection object

Requirements:
    - Salesforce CLI (sf) v2.24.4 or newer
    - Valid SFDX authentication URL with credentials
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

from simple_salesforce import Salesforce

from logger import logger


def _get_sf_command():
    """Get the Salesforce CLI command, handling Windows .cmd extension."""
    if sys.platform == 'win32':
        # On Windows, try sf.cmd first (npm global install), then sf
        sf_path = shutil.which('sf.cmd') or shutil.which('sf')
    else:
        sf_path = shutil.which('sf')

    if not sf_path:
        raise FileNotFoundError("Salesforce CLI (sf) not found. Please ensure it is installed and in your PATH.")

    return sf_path


def get_salesforce_connection_url(url):
    """
    Connect to Salesforce using the Salesforce CLI and Simple Salesforce via a URL
    Requires `sf` CLI v2.24.4/newer

    Args:
        url: SFDX authentication URL (must be a valid URL string)

    Returns:
        Salesforce connection object

    Raises:
        ValueError: If URL is None or empty
        subprocess.CalledProcessError: If Salesforce CLI command fails
        KeyError: If expected data is missing from CLI output
    """
    # Validate URL before attempting login
    if not url:
        raise ValueError("SFDX authentication URL is required but was not provided. "
                        "Ensure environment variable is set.")

    temp_file = None
    try:
        sf_cmd = _get_sf_command()

        # Use a temporary file for the auth URL (more reliable on Windows than stdin)
        # The file is deleted immediately after use
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(url)
            temp_file = f.name

        # Use --sfdx-url-file which is more reliable across platforms
        login_process = subprocess.run(
            [sf_cmd, 'org', 'login', 'sfdx-url', '--set-default', '--sfdx-url-file', temp_file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Get org display info
        display_cmd = subprocess.run(
            [sf_cmd, 'org', 'display', '--json'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        sfdx_info = json.loads(display_cmd.stdout.decode('utf-8'))

        access_token = sfdx_info['result']['accessToken']
        instance_url = sfdx_info['result']['instanceUrl']
        api_version = sfdx_info['result']['apiVersion']
        domain = 'test' if 'sandbox' in instance_url else 'login'
        return Salesforce(instance_url=instance_url, session_id=access_token,
                          domain=domain, version=api_version)

    except subprocess.CalledProcessError as e:
        # Log the actual error output from the CLI
        stderr_output = e.stderr.decode('utf-8') if e.stderr else 'No stderr output'
        stdout_output = e.stdout.decode('utf-8') if e.stdout else 'No stdout output'
        logger.error("Error logging into Salesforce: %s", e)
        logger.error("CLI stderr: %s", stderr_output)
        logger.error("CLI stdout: %s", stdout_output)
        raise
    except KeyError as e:
        logger.error("Missing expected key in Salesforce CLI output: %s", e)
        raise
    finally:
        # Always clean up the temporary file
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
