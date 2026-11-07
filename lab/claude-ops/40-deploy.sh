#!/usr/bin/env bash
# Runs INSIDE the claude-ops CT as root, from this directory (lab/claude-ops of the fetched repo).
# Installs the audit hook, its log directory and Claude Code settings. Idempotent.
# DEST_ROOT prefixes all destinations so the script can be exercised off-host.
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=${DEST_ROOT:-}
CHOWN=${CHOWN:-chown}

install -D -m 0755 "$here/audit_hook.py" "$root/usr/local/bin/claude-audit-hook"

install -d -m 0755 "$root/var/log/claude-audit"
"$CHOWN" claude:claude "$root/var/log/claude-audit"

install -d -m 0700 "$root/home/claude/.claude"
install -m 0644 "$here/settings.json" "$root/home/claude/.claude/settings.json"
"$CHOWN" -R claude:claude "$root/home/claude/.claude"

echo "deployed audit hook + settings"
