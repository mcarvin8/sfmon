"""
AWS Secrets Manager backend for SALESFORCE_AUTH_URL secrets.

Only imported when SECRETS_BACKEND=aws is set (see orgs.resolve_auth_url), so
boto3 stays an optional dependency (pip install "sfmon[aws]") for the common
case of plain environment-variable auth.
"""

import boto3
from botocore.exceptions import ClientError

from .logger import logger


_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("secretsmanager")
    return _client


def get_secret_aws(secret_name):
    """Fetch a secret string from AWS Secrets Manager.

    Args:
        secret_name: Name or ARN of the secret holding the SFDX auth URL.

    Returns:
        The secret's string value.

    Raises:
        RuntimeError: If the secret can't be fetched (missing, no permission,
            wrong region, etc.) — the underlying ClientError is chained.
    """
    try:
        response = _get_client().get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise RuntimeError(
            f"Failed to fetch secret '{secret_name}' from AWS Secrets Manager: {e}"
        ) from e

    secret = response.get("SecretString")
    if not secret:
        raise RuntimeError(
            f"Secret '{secret_name}' has no SecretString value "
            "(binary secrets are not supported)."
        )
    logger.info("Fetched secret '%s' from AWS Secrets Manager", secret_name)
    return secret
