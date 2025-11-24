"""
Salesforce Connection Module

This module handles authentication and connection establishment to the Salesforce
production organization using the Salesforce CLI (sf) and Simple Salesforce library.
It provides secure, token-based authentication via SFDX URL method.

Functions:
    - get_salesforce_connection_url: Authenticates and returns a Salesforce connection object

Requirements:
    - Salesforce CLI (sf) v2.24.4 or newer
    - Valid SFDX authentication URL with credentials
"""
import json
import subprocess

from simple_salesforce import Salesforce

from logger import logger

def get_salesforce_connection_url(url):
    """
    Connect to Salesforce using the Salesforce CLI and Simple Salesforce via a URL
    Requires `sf` CLI v2.24.4/newer
    """
    try:
        login_cmd = f'echo {url} | sf org login sfdx-url --set-default --sfdx-url-stdin -'
        subprocess.run(login_cmd, check=True, shell=True)
        display_cmd = subprocess.run('sf org display --json', check=True,
                                     shell=True, stdout=subprocess.PIPE)
        sfdx_info = json.loads(display_cmd.stdout)

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
