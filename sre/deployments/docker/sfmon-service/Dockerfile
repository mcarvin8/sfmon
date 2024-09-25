FROM ubuntu:latest

# Pull in build arguments
ARG SALESFORCE_AUTH_URL

# Set Salesforce CLI Environment Variables
ENV SF_AUTOUPDATE_DISABLE=true \
    SF_USE_GENERIC_UNIX_KEYCHAIN=true \
    SF_DOMAIN_RETRY=300 \
    SF_PROJECT_AUTOUPDATE_DISABLE_FOR_PACKAGE_CREATE=true \
    SF_PROJECT_AUTOUPDATE_DISABLE_FOR_PACKAGE_VERSION_CREATE=true \
    SF_DISABLE_DNS_CHECK=true \
    SF_DISABLE_SOURCE_MEMBER_POLLING=true \
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
    /opt/venv/bin/pip install --no-cache-dir simple_salesforce prometheus_client requests schedule && \
    sf version --verbose --json && \
    /opt/venv/bin/pip list

# Set the environment variables to use the venv
ENV PATH="/opt/venv/bin:$PATH"

# Run the application
ENTRYPOINT ["python3", "salesforce_monitoring.py"]
EXPOSE 9001
