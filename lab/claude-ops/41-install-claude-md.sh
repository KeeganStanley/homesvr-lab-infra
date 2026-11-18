#!/usr/bin/env bash
# Runs INSIDE the claude-ops CT as root, from this directory (lab/claude-ops of the fetched repo).
# Installs managed-CLAUDE.md as the managed (root-owned) CLAUDE.md, loaded in every Claude Code session.
# The `claude` user cannot edit or exclude it. Prints the file's sha256 so the results can record the version.
# Safe to run on its own: unlike 40-deploy.sh it does not touch ~/.claude/settings.json.
# DEST_ROOT prefixes the destination so the script can be exercised off-host.
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=${DEST_ROOT:-}

install -d -m 0755 "$root/etc/claude-code"
install -m 0644 "$here/managed-CLAUDE.md" "$root/etc/claude-code/CLAUDE.md"
echo "installed /etc/claude-code/CLAUDE.md sha256=$(sha256sum "$root/etc/claude-code/CLAUDE.md" | cut -d' ' -f1)"
