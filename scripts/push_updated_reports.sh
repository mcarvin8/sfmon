#!/usr/bin/env bash
set -euo pipefail

# Commit and push generated report files if they changed. Intended for CI (GitHub Actions / GitLab).
# Paths must match the exporter: tech_debt package reads these from src/sfmon/tech_debt/

REPORT_FILES=(
  "src/sfmon/tech_debt/pmd-report.xml"
  "src/sfmon/tech_debt/minimal-perm-sets.json"
)

git config user.name "${GIT_COMMITTER_NAME:-github-actions[bot]}"
git config user.email "${GIT_COMMITTER_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}"

git add "${REPORT_FILES[@]}"

if git diff --staged --quiet; then
  echo "No changes to report files; skipping commit."
  exit 0
fi

git commit -m "chore: refresh PMD and minimal permission set reports"
git push
