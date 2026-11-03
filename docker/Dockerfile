FROM python:3.11-slim

# Working directory is the parent of the sfmon/ package so it can be run as
# `python3 -m sfmon.salesforce_monitoring` (package-relative imports require this).
WORKDIR /app

# Install Python dependencies from pyproject.toml so the image uses the same
# version bounds as the PyPI package. Done before copying the source so this
# layer is cached across code-only changes. boto3 (the "aws" extra) is only
# used when SECRETS_BACKEND=aws is set (see src/sfmon/secrets_manager.py) but
# is installed unconditionally so no rebuild is needed to opt in.
COPY pyproject.toml /tmp/pyproject.toml
RUN python3 -c "import tomllib; p = tomllib.load(open('/tmp/pyproject.toml', 'rb'))['project']; print('\n'.join(p['dependencies'] + p['optional-dependencies']['aws']))" > /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/pyproject.toml /tmp/requirements.txt && \
    pip list

COPY src/sfmon/ /app/sfmon/

# Copy documentation and license
COPY README.md /app/sfmon/README.md
COPY LICENSE.md /app/sfmon/LICENSE.md
COPY version.txt /app/sfmon/version.txt

LABEL org.opencontainers.image.title="sfmon" \
      org.opencontainers.image.description="Monitor a Salesforce org and expose Prometheus metrics from a long-running Python service." \
      org.opencontainers.image.authors="Matt Carvin <matthewjcarvin@gmail.com>" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/mcarvin8/sfmon"

# Create non-root user
ARG EXPORTER_UID=1001
RUN useradd --uid ${EXPORTER_UID} --create-home --shell /bin/bash exporter && \
    chown -R exporter:exporter /app/sfmon

# Use numeric UID so Kubernetes can verify non-root when runAsNonRoot is set
USER ${EXPORTER_UID}

# Health check: metrics endpoint on METRICS_PORT (default 9001). Uses python3
# (already required by the app) instead of curl so no extra package is needed.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"METRICS_PORT\", 9001)}/metrics', timeout=2)" || exit 1

# Run the application
ENTRYPOINT ["python3", "-m", "sfmon.salesforce_monitoring"]
EXPOSE 9001
