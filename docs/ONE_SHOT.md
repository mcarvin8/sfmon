# One-shot mode: run from CI instead of a daemon

Don't want an always-on container? `sfmon --once` runs every enabled job a single time, prints the resulting Prometheus exposition text to stdout, and exits — the same model sfdx-hardis's org monitoring uses (a scheduled CI/CD pipeline instead of a long-running process). Works with either distribution:

```bash
# Docker
docker run --rm -e SALESFORCE_AUTH_URL="force://PlatformCLI::..." mcarvin8/sfmon:latest --once

# pip install
SALESFORCE_AUTH_URL="force://PlatformCLI::..." sfmon --once
```

- Exit code is `0` if every job that ran succeeded, `1` if any job raised, had a failed Salesforce query, or the initial org connection failed — so a scheduled pipeline goes red on a real problem, the same way a failed CI step would.
- Add `--job JOB_ID` to run exactly one job (its id from the tables in [docs/CONFIGURATION.md](CONFIGURATION.md)) instead of everything currently enabled — `--job` forces that job to run regardless of its opt-in/disabled state in `config.json`, useful for ad-hoc checks. `--job` requires `--once`.
- Without `--job`, `--once` respects the same config as the daemon (presets, opt-in `schedules`, `disabled` entries) — it runs whatever would run at container startup, just without then staying up to serve `/metrics` or wait for the next cron tick.
- Pipe the output wherever it's useful: archive it as a pipeline artifact, `curl --data-binary` it to a Pushgateway, or `grep` it for a threshold check.

# GitHub Action — run a single job as a CI step

Same one-shot model, packaged as a reusable action so a workflow step can gate on the result without shelling out to `docker run` itself:

```yaml
- name: Check Salesforce API limits
  id: limits
  uses: mcarvin8/sfmon@v4
  with:
    job-id: monitor_salesforce_limits
    auth-url: ${{ secrets.SF_AUTH_URL }}

- name: Use the parsed metrics
  run: echo '${{ steps.limits.outputs.metrics-json }}' | jq .
```

| Input | Required | Maps to |
|-------|----------|---------|
| `job-id` | yes | `sfmon --once --job <id>` |
| `auth-url` | yes | `SALESFORCE_AUTH_URL` |
| `org-name` | no | `ORG_NAME` (org label on the metrics) |

| Output | Description |
|--------|-------------|
| `exit-code` | `0`/`1`/`2` from `sfmon --once` — the step also fails naturally on `1`/`2` |
| `metrics-raw` | Full Prometheus exposition text for the run |
| `metrics-json` | Same metrics parsed into a flat `{"metric_name{labels}": value}` object |

Any other env var `sfmon` reads (thresholds, compliance lists, `SECRETS_BACKEND`, etc. — see [docs/ENVIRONMENT.md](ENVIRONMENT.md)) can be set directly on the step's own `env:` block; it's passed through to the container. Fleet mode (`SALESFORCE_AUTH_URL_<ORG>`) isn't wired into the action's inputs yet — single-org only.
