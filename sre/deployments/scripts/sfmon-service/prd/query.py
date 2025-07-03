'''
    Runs a query using the Salesforce CLI and parses the JSON response.
    Optionally use tooling API if needed.
'''
import json
import subprocess

from cloudwatch_logging import logger

def run_sf_cli_query(alias, query, use_tooling_api=False):
    """Run Salesforce CLI query and return parsed records."""
    try:
        # normalize query first
        normalized_query = ' '.join(line.strip() for line in query.strip().splitlines())
        command = f'sf data query --query "{normalized_query}" --target-org "{alias}" --json'
        if use_tooling_api:
            command += ' --use-tooling-api'
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            shell=True
        )
        data = json.loads(result.stdout)
        return data.get("result", {}).get("records", [])
    except subprocess.CalledProcessError as e:
        logger.error("Salesforce CLI query failed for alias %s: %s", alias, e.stderr)
        return []
    except json.JSONDecodeError:
        logger.error("Invalid JSON output from Salesforce CLI for alias %s", alias)
        return []
