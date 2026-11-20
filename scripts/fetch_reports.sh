#!/usr/bin/env bash
# Unpacks the reports an `evaluate` run printed into its log: scripts/fetch_reports.sh <run-id>
set -euo pipefail
run="$1"
gh run view "$run" -R manojrevenkar12-web/tenant-fair-search --log \
  | sed -n '/TFS-REPORTS-BEGIN/,/TFS-REPORTS-END/p' \
  | grep -v 'TFS-REPORTS' | grep -v 'echo' | sed 's/^.*Z //' | tr -d '\n ' | base64 -d | tar xzf -
python -m tfs.eval.cli readme
