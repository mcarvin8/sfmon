""""
    Connect to the Salesforce org.
"""
import subprocess

from cloudwatch_logging import logger

def get_salesforce_connection_url(url, alias):
    """
    Connect to Salesforce using the Salesforce CLI and Simple Salesforce via a URL
    Requires `sf` CLI v2.24.4/newer
    """
    try:
        login_cmd = f'echo {url} | sf org login sfdx-url --set-default --alias {alias} --sfdx-url-stdin -'
        subprocess.run(login_cmd, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        logger.error("Error logging into Salesforce: %s", e)
        raise
    except KeyError as e:
        logger.error("Missing expected key in Salesforce CLI output: %s", e)
        raise
