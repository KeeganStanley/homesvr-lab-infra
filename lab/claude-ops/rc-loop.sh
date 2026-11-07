#!/usr/bin/env bash
# Keeps Claude Code Remote Control alive. Runs under tmux (see claude-rc.service) as user `claude`.
# Remote Control exits after a prolonged network loss, so restart it after every exit.
# CLAUDE_BIN / WORKDIR / LOG_FILE / SLEEP_S / MAX_ITERATIONS are overridable for tests;
# MAX_ITERATIONS=0 (default) means loop forever.
set -uo pipefail

export PATH="$HOME/.local/bin:$PATH"
CLAUDE_BIN=${CLAUDE_BIN:-claude}
WORKDIR=${WORKDIR:-/home/claude/lab}
LOG_FILE=${LOG_FILE:-/home/claude/rc-loop.log}
SLEEP_S=${SLEEP_S:-30}
MAX_ITERATIONS=${MAX_ITERATIONS:-0}

n=0
while :; do
  cd "$WORKDIR" || { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) cannot cd to $WORKDIR" >> "$LOG_FILE"; }
  "$CLAUDE_BIN" remote-control --name "HomeSVR Lab" --spawn worktree --permission-mode bypassPermissions
  rc=$?
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) claude remote-control exited with code $rc; restarting in ${SLEEP_S}s" >> "$LOG_FILE"
  n=$((n + 1))
  if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$n" -ge "$MAX_ITERATIONS" ]; then
    break
  fi
  sleep "$SLEEP_S"
done
