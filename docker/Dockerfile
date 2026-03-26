FROM ubuntu:24.04

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

# Set the environment variables to use the venv
ENV PATH="/opt/venv/bin:$PATH"

# sf CLI writes config to $HOME/.sf and .sfdx. With read-only root FS, we mount emptyDir at
# /app/sfmon/.sf and .sfdx; set HOME so the CLI uses that path
ENV HOME=/app/sfmon

# Create non-root user and sf CLI config dirs (mount points for writable volumes)
ARG EXPORTER_UID=1001
RUN useradd --uid ${EXPORTER_UID} --create-home --shell /bin/bash exporter && \
    chown -R exporter:exporter /app/sfmon /opt/venv && \
    mkdir -p /app/sfmon/.sf /app/sfmon/.sfdx && \
    chown exporter:exporter /app/sfmon/.sf /app/sfmon/.sfdx

# Use numeric UID so Kubernetes can verify non-root when runAsNonRoot is set
USER ${EXPORTER_UID}

# Health check: metrics endpoint on METRICS_PORT (default 9001)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f "http://localhost:${METRICS_PORT:-9001}/metrics" || exit 1

# Run the application
ENTRYPOINT ["python3", "salesforce_monitoring.py"]
EXPOSE 9001
