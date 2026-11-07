#!/usr/bin/env python3
"""Claude Code PreToolUse hook: append one JSON line per tool call to an audit log.

Installed as /usr/local/bin/claude-audit-hook. Reads the hook payload on stdin.
The tier ("read" | "change" | "destructive") is advisory: it drafts a prod approval
policy from real usage and enforces nothing. The hook ALWAYS exits 0 and never blocks.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

DEFAULT_LOG = "/var/log/claude-audit/audit.jsonl"

_DESTRUCTIVE = [re.compile(p) for p in (
    r"\brm\s+(?:-[A-Za-z-]+\s+)*-[A-Za-z]*[rR][A-Za-z]*(?=\s|$)",
    r"\brm\s.*--recursive\b",
    r"\bpct\s+destroy\b",
    r"\bqm\s+destroy\b",
    r"\bzfs\s+destroy\b",
    r"\bzpool\s+(?:destroy|detach|offline|labelclear)\b",
    r"\bmkfs(?:\.\w+)?\b",
    r"\bwipefs\b",
    r"(?<![\w.-])dd\s",
    r"\bpvesm\s+remove\b",
)]

_CHANGE = [re.compile(p) for p in (
    r"\b(?:pct|qm)\s+(?:set|start|stop|shutdown|reboot|create|restore|resize)\b",
    r"\bsystemctl\s+(?:start|stop|restart|enable|disable)\b",
    r"\bapt(?:-get)?\s+(?:install|remove|purge|upgrade|full-upgrade)\b",
    r"\bgit\s+(?:push|commit|merge|reset)\b",
    r"\bzfs\s+(?:set|create|snapshot|rollback)\b",
    r"\bsed\s+(?:-\S+\s+)*-\S*i",
    r"\btee\b(?:\s+-\S+)*\s+[^\s|;&-]",
)]

# Redirections that don't write a file: 2>&1, >&2, >/dev/null, &>/dev/null
_BENIGN_REDIRECT = re.compile(r"&?\d*>>?\s*/dev/null|\d*>&\d*-?")
_FILE_REDIRECT = re.compile(r">>?\s*[^\s&]")

_READ_TOOLS = {"Read", "Grep", "Glob", "WebSearch", "WebFetch"}


def _classify_bash(command):
    command = str(command)
    if any(p.search(command) for p in _DESTRUCTIVE):
        return "destructive"
    if any(p.search(command) for p in _CHANGE):
        return "change"
    if _FILE_REDIRECT.search(_BENIGN_REDIRECT.sub(" ", command)):
        return "change"
    return "read"


def classify(tool_name, tool_input):
    if tool_name == "Bash":
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
        return _classify_bash(command)
    if tool_name in _READ_TOOLS:
        return "read"
    return "change"  # Edit/Write/NotebookEdit and anything unknown


def build_record(payload, now):
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input")
    return {
        "ts": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_id": payload.get("session_id", ""),
        "tool": tool,
        "input": tool_input if tool_input is not None else {},
        "prod_tier": classify(tool, tool_input),
    }


def main(stdin_text, log_path):
    try:
        payload = json.loads(stdin_text)
        if not isinstance(payload, dict):
            return 0
        line = json.dumps(build_record(payload, datetime.now(timezone.utc)), default=str)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:  # noqa: BLE001 - the hook must never block a tool call
        pass
    return 0


if __name__ == "__main__":
    try:
        code = main(sys.stdin.read(), os.environ.get("CLAUDE_AUDIT_LOG", DEFAULT_LOG))
    except Exception:  # noqa: BLE001
        code = 0
    sys.exit(code)
