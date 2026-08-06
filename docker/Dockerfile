FROM python:3.11-slim

# Set working directory to script
WORKDIR /app/sfmon
COPY src/sfmon/ /app/sfmon/

# Copy documentation and license
COPY README.md /app/sfmon/README.md
COPY LICENSE.md /app/sfmon/LICENSE.md
COPY version.txt /app/sfmon/version.txt

LABEL org.opencontainers.image.title="sfmon" \
      org.opencontainers.image.description="Monitor your Salesforce orgs using a custom Docker image to create Prometheus metrics." \
      org.opencontainers.image.authors="Matt Carvin <matthewjcarvin@gmail.com>" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/mcarvin8/sfmon"

# Install curl for HEALTHCHECK, then the required Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir simple_salesforce prometheus_client requests apscheduler pandas && \
    pip list

# Create non-root user
ARG EXPORTER_UID=1001
RUN useradd --uid ${EXPORTER_UID} --create-home --shell /bin/bash exporter && \
    chown -R exporter:exporter /app/sfmon

# Use numeric UID so Kubernetes can verify non-root when runAsNonRoot is set
USER ${EXPORTER_UID}

# Health check: metrics endpoint on METRICS_PORT (default 9001)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f "http://localhost:${METRICS_PORT:-9001}/metrics" || exit 1

# Run the application
ENTRYPOINT ["python3", "salesforce_monitoring.py"]
EXPOSE 9001
