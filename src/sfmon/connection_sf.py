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
import shutil
import subprocess
import sys

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
        subprocess.CalledProcessError: If Salesforce CLI command fails
        KeyError: If expected data is missing from CLI output
    """
    try:
        sf_cmd = _get_sf_command()
        
        # Securely pass URL via stdin without shell command injection
        # Use argument list instead of shell=True to prevent injection
        login_process = subprocess.run(
            [sf_cmd, 'org', 'login', 'sfdx-url', '--set-default', '--sfdx-url-stdin', '-'],
            input=url.encode('utf-8'),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Use argument list instead of shell=True
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
        logger.error("Error logging into Salesforce: %s", e)
        raise
    except KeyError as e:
        logger.error("Missing expected key in Salesforce CLI output: %s", e)
        raise
