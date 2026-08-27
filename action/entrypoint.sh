#!/usr/bin/env bash
# Entrypoint for the SFMon GitHub Action. Runs `sfmon --once --job <job-id>`,
# echoes the raw output to the log, then writes three GITHUB_OUTPUT values:
#   exit-code    - 0/1/2 from sfmon (see run_once() in salesforce_monitoring.py)
#   metrics-raw  - the full Prometheus exposition text, verbatim
#   metrics-json - the same text parsed into a flat {"metric{labels}": value} object
#
# Metric names/labels differ per job and aren't enumerated anywhere central,
# so this parses generically instead of hardcoding per-job keys.
set -uo pipefail

job_id="${1:?job-id argument is required}"

output="$(sfmon --once --job "$job_id")"
exit_code=$?

echo "$output"

{
  echo "exit-code=${exit_code}"
  echo "metrics-raw<<SFMON_METRICS_EOF"
  echo "$output"
  echo "SFMON_METRICS_EOF"
} >>"$GITHUB_OUTPUT"

metrics_json="$(
  echo "$output" | awk '
    /^#/ { next }
    NF == 0 { next }
    {
      value = $NF
      NF--
      key = $0
      gsub(/\\/, "\\\\", key)
      gsub(/"/, "\\\"", key)
      printf "%s\"%s\":%s", (n++ ? "," : ""), key, value
    }
  '
)"
echo "metrics-json={${metrics_json}}" >>"$GITHUB_OUTPUT"

exit "$exit_code"
