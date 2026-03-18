# Salesforce Monitoring (SFMon)

![Docker Image Version](https://img.shields.io/docker/v/mcarvin8/sfmon?sort=date)
![Docker Pulls](https://img.shields.io/docker/pulls/mcarvin8/sfmon)
![Docker Image Size](https://img.shields.io/docker/image-size/mcarvin8/sfmon)

SFMon runs in **Docker**, talks to your Salesforce org, and serves **Prometheus** metrics at `/metrics`. Deploy on ECS, Kubernetes, VMs, or any host that runs containers.

---

## Run the published image

Image: **[mcarvin8/sfmon](https://hub.docker.com/r/mcarvin8/sfmon)**.

1. **Auth URL** — from your machine: `sf org display --url-only` (or legacy `sfdx force:org:display --urlonly`).
2. **Run:**

```bash
docker run -d \
  --name sfmon \
  -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://PlatformCLI::..." \
  mcarvin8/sfmon:latest
```

3. **Prometheus** — scrape `http://<host>:9001/metrics` (match host/port to your publish mapping).
4. **Sanity check:** `curl http://localhost:9001/metrics`

No config file is required: all collectors run on **default schedules**. Optional tuning:

- **Environment variables** (timeouts, compliance lists, thresholds, log level, etc.) → **[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)**
- **Config file** (schedules, disable jobs, `exclude_users`) → **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** · template **`config.example.json`**

Example with a mounted config:

```bash
docker run -d --name sfmon -p 9001:9001 \
  -e SALESFORCE_AUTH_URL="force://..." \
  -v /path/on/host/config.json:/app/sfmon/config.json \
  mcarvin8/sfmon:latest
```

---

## When you need your own image

The Hub image is meant for **standard** monitoring: env vars + optional JSON config.

**Build and run your own image** if you need to change **application code** (new checks, different logic, pinned dependencies, private registry policy, or anything not covered by env/config).

```bash
docker build \
  -f docker/Dockerfile \
  --build-arg SALESFORCE_AUTH_URL="$SALESFORCE_AUTH_URL" \
  -t your-registry/sfmon:latest .

docker push your-registry/sfmon:latest   # if using a registry
```

Then run `your-registry/sfmon:latest` the same way as above (`-e SALESFORCE_AUTH_URL=...`, ports, volumes).

---

## Grafana

Import the JSON dashboards under **`grafana/`** and point them at your Prometheus data source.

---

## Authors

Originally developed by **Deep Suthar** and **Matt Carvin** (e.g. ECS / Kubernetes at Avalara).
