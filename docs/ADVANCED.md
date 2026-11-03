# Advanced setup

File-based collectors and custom images. Most deployments need neither.

## PMD + minimal permission sets (file-based)

The **published** `mcarvin8/sfmon` image does **not** include an Apex ruleset, `pmd-report.xml`, or `minimal-perm-sets.json` (they stay in your repo/CI only; see **[`.dockerignore`](../.dockerignore)**). Collectors **`monitor_pmd_code_smells`** and **`monitor_minimal_perm_sets`** need those files **inside the container** at fixed paths:

| File | In-container path |
|------|-------------------|
| PMD ruleset (XML) | Any path you choose; set **`PMD_RULESET_PATH`** to it |
| PMD report | **`/app/sfmon/tech_debt/pmd-report.xml`** |
| Minimal perm set report | **`/app/sfmon/tech_debt/minimal-perm-sets.json`** |

**Typical flow:**

1. **In your fork/clone** (with org access), refresh reports in CI so **`pmd-report.xml`** and **`minimal-perm-sets.json`** are produced under **`src/sfmon/tech_debt/`** and pushed to your default branch. Maintain **`manifest/package.xml`** and **`apexruleset.xml`** in that folder.
   - **GitHub Actions:** Workflow **[`.github/workflows/update-local-reports.yml`](../.github/workflows/update-local-reports.yml)** — repository secret **`SALESFORCE_AUTH_URL`** (SFDX URL). Optional `workflow_dispatch` input **`manifest_path`** (default **`manifest/package.xml`**).
   - **Other CI systems (GitLab, etc.):** port the GitHub workflow's steps and push the report files with a repository write token. Details: **[docs/ENVIRONMENT.md](ENVIRONMENT.md#refreshing-reports-in-ci)**.
2. **Get those files into the runtime container** (pick one):
   - **Mounts (no image rebuild):** copy or sync the committed files to the host/CI artifact store, then **bind-mount** or use a **ConfigMap** / volume (watch size limits for very large `pmd-report.xml`). Set **`PMD_RULESET_PATH`** and redeploy the **same** public image tag when you refresh reports.
   - **Private image:** **`docker build -f docker/Dockerfile`** from a branch that contains the refreshed files and **remove or trim the `src/sfmon/tech_debt/*` lines in `.dockerignore`** so `COPY src/sfmon/` bakes them in; push to your registry and redeploy when reports change.

3. **Opt in via `config.json`:** These collectors have **no default schedule**. Add **`monitor_pmd_code_smells`** and **`monitor_minimal_perm_sets`** under **`schedules`** with a cron string (see **[docs/CONFIGURATION.md](CONFIGURATION.md#opt-in-only--file-based-reports-no-default-schedule)**). If your file uses a **non-empty** `schedules` block, list every other job you still want as well.

If **`PMD_RULESET_PATH`** is unset or the ruleset file is missing, PMD metrics are skipped (quiet at INFO). If **`minimal-perm-sets.json`** is missing, that collector logs a warning and exits. More detail: **[docs/ENVIRONMENT.md](ENVIRONMENT.md#pmd-and-minimal-permission-sets-optional)**.

## Building your own image

The default image covers **standard** monitoring: env vars + optional JSON config. It excludes org-specific PMD/perm-set files by default (see **[`.dockerignore`](../.dockerignore)**) — for baking those in, see [PMD + minimal permission sets](#pmd--minimal-permission-sets-file-based) above.

To add metrics for CPQ or other custom objects, you probably don't need your own image: [custom SOQL metrics](CUSTOM_METRICS.md) cover anything that's a query result stored in a gauge.

**Build and run your own image** if you need to change **application code** — new checks, different logic, pinned dependencies, private registry policy, or anything not covered by env/config.

```bash
docker build \
  -f docker/Dockerfile \
  -t your-registry/sfmon:latest .

docker push your-registry/sfmon:latest   # if using a registry
```

Then run `your-registry/sfmon:latest` the same way as above (`-e SALESFORCE_AUTH_URL=...`, ports, volumes).

## Using SFMon as a library

The PyPI package is also importable, for scripts that want one collector's logic without the daemon, e.g. `from sfmon.core.limits import salesforce_limits_descriptions`. Without Docker there's no default `/app/sfmon/config.json`, so set `CONFIG_FILE_PATH` if you use a config file ([details](CONFIGURATION.md)).
