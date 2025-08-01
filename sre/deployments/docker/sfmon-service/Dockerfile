FROM artifacts.platform.avalara.io/docker/ubuntu

# Pull in build arguments
ARG SALESFORCE_AUTH_URL

# Set Salesforce CLI Environment Variables
# https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_dev_cli_env_variables.htm
ENV SF_AUTOUPDATE_DISABLE=true \
    SF_USE_GENERIC_UNIX_KEYCHAIN=true \
    SF_DOMAIN_RETRY=300 \
    SF_PROJECT_AUTOUPDATE_DISABLE_FOR_PACKAGE_CREATE=true \
    SF_PROJECT_AUTOUPDATE_DISABLE_FOR_PACKAGE_VERSION_CREATE=true \
    SF_DISABLE_DNS_CHECK=true \
    SF_DISABLE_SOURCE_MEMBER_POLLING=true \
    SF_HIDE_RELEASE_NOTES=true \
    SF_HIDE_RELEASE_NOTES_FOOTER=true \
    SF_SKIP_NEW_VERSION_CHECK=true \
    SF_CONTAINER_MODE=true \
    SALESFORCE_AUTH_URL=${SALESFORCE_AUTH_URL}

# Set working directory to script
WORKDIR /app/sfmon
COPY sre/deployments/scripts/sfmon-service /app/sfmon

# Install required Salesforce and Python dependencies
RUN apt-get update && apt-get install -y curl python3 python3-pip python3-venv && \
    python3 -m venv /opt/venv && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    npm install --global @salesforce/cli@latest && \
    /opt/venv/bin/pip install --no-cache-dir prometheus_client requests schedule pandas && \
    sf version --verbose --json && \
    /opt/venv/bin/pip list

# Set the environment variables to use the venv #
ENV PATH="/opt/venv/bin:$PATH"

# Run the application
ENTRYPOINT ["python3", "salesforce_monitoring.py"]
EXPOSE 9001
