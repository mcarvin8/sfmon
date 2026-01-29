FROM ubuntu:22.04

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
    SF_CONTAINER_MODE=true

# Set working directory to script
WORKDIR /app/sfmon
COPY src/sfmon/ /app/sfmon/

# Copy documentation and license
COPY README.md /app/sfmon/README.md
COPY LICENSE.md /app/sfmon/LICENSE.md
COPY version.txt /app/sfmon/version.txt

# Install required Salesforce and Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl python3 python3-pip python3-venv && \
    python3 -m venv /opt/venv && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    npm install --global @salesforce/cli@latest && \
    /opt/venv/bin/pip install --no-cache-dir simple_salesforce prometheus_client requests apscheduler pandas && \
    sf version --verbose --json && \
    /opt/venv/bin/pip list

# Set the environment variables to use the venv #
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for running the application
RUN groupadd --gid 1000 sfmon && \
    useradd --uid 1000 --gid sfmon --shell /bin/bash --create-home sfmon && \
    chown -R sfmon:sfmon /app/sfmon /opt/venv

USER sfmon

# Run the application
ENTRYPOINT ["python3", "salesforce_monitoring.py"]
EXPOSE 9001
