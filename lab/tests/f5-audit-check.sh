#!/usr/bin/env bash
# F5: audit log vs. PVE task log. Runs ON pve-lab (as root).
# Usage: f5-audit-check.sh <since_iso_ts> <min_count>     e.g. 2026-11-07T17:00:00Z 20
# Pulls the audit log from CT 100, lists pve-lab tasks since the timestamp, and prints
# AUDIT_LINES=, PVE_TASKS=, UNMATCHED=..., RESULT=PASS|FAIL (exit 0 only on PASS).
# PCT / PVESH / NODE overrides exist so it can be tested off-host.
set -euo pipefail

if [ $# -ne 2 ] || ! [[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || ! [[ $2 =~ ^[0-9]+$ ]]; then
  echo "usage: f5-audit-check.sh <YYYY-MM-DDTHH:MM:SSZ> <min_count>" >&2
  exit 2
fi
since=$1
min_count=$2
PCT=${PCT:-pct}
PVESH=${PVESH:-pvesh}
node=${NODE:-pve-lab}
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
match=$here/../tools/f5_match.py

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

epoch=$(date -u -d "$since" +%s)
"$PCT" exec 100 -- cat /var/log/claude-audit/audit.jsonl > "$tmp/audit.jsonl"
"$PVESH" get "/nodes/$node/tasks" --since "$epoch" --limit 1000 --output-format json > "$tmp/tasks.json"

python3 "$match" "$tmp/audit.jsonl" "$tmp/tasks.json" "$since" "$min_count"
