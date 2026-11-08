#!/usr/bin/env python3
"""Claude Code PreToolUse hook: append one JSON line per tool call to an audit log.

Installed as /usr/local/bin/claude-audit-hook. Reads the hook payload on stdin.
The tier ("read" | "change" | "destructive") is advisory: it drafts a prod approval
policy from real usage and enforces nothing. The hook ALWAYS exits 0 and never blocks.
"""
import json
import re
import sys
from datetime import datetime, timezone

# Fixed on purpose: no environment override, so the agent cannot redirect its own audit log.
LOG_PATH = "/var/log/claude-audit/audit.jsonl"

# Global options may sit between a binary and its subcommand (apt-get -y install, systemctl --user stop).
_OPTS = r"(?:\s+-{1,2}[\w=.-]+)*"
_GIT_OPTS = r"(?:\s+(?:-C|-c)\s+\S+|\s+-{1,2}[\w=.-]+)*"


def _sub(binary, verbs, opts=_OPTS):
    return rf"\b{binary}{opts}\s+(?:{verbs})\b"


_DESTRUCTIVE = [re.compile(p, re.IGNORECASE) for p in (
    r"\brm\s+(?:-[A-Za-z-]+\s+)*-[A-Za-z]*[rR][A-Za-z]*(?=\s|$)",
    r"\brm\s.*--recursive\b",
    _sub("pct", "destroy|rollback|delsnapshot"),
    _sub("qm", "destroy|rollback|delsnapshot"),
    r"\bqm\s+(?:disk\s+)?unlink\b",
    _sub("zfs", "destroy"),
    r"\bzfs\s+(?:recv|receive)\b.*\s-\w*F",
    _sub("zpool", "destroy|detach|offline|labelclear|create|replace|add"),
    r"\bmkfs(?:\.\w+)?\b",
    r"\bwipefs\b",
    r"\b(?:blkdiscard|shred|lvremove|vgremove|pvremove)\b",
    r"\bsgdisk\s.*(?:--zap|-Z\b|-o\b)",
    r"(?<![\w.-])dd\s",
    _sub("pvesm", "remove|free"),
    _sub("pvesh", "delete"),
    r"\bfind\b.*\s-delete\b",
    _sub("git", "clean", _GIT_OPTS),
    r"\bdocker(?:\s+compose)?\s+down\b.*\s-\w*v",
    r"\bdocker\s+(?:volume|system)\s+(?:rm|prune)\b",
    r"\bcurl\b.*(?:-X|--request)[\s=]*DELETE\b",
    r"\brmtree\b",
)]

_CHANGE = [re.compile(p, re.IGNORECASE) for p in (
    _sub("pct", "set|start|stop|shutdown|reboot|create|restore|resize"),
    _sub("qm", "set|start|stop|shutdown|reboot|create|restore|resize"),
    _sub("systemctl", "start|stop|restart|enable|disable"),
    _sub("apt", "install|remove|purge|upgrade|full-upgrade|dist-upgrade|autoremove"),
    _sub("apt-get", "install|remove|purge|upgrade|full-upgrade|dist-upgrade|autoremove"),
    _sub("git", "push|commit|merge|reset", _GIT_OPTS),
    _sub("zfs", "set|create|snapshot|rollback|recv|receive"),
    r"\bsed\b[^|;&]*\s-[A-Za-z]*i[A-Za-z0-9.]*(?=\s|$)",
    r"\btee\b(?:\s+-\S+)*\s+[^\s|;&-]",
    _sub("pvesh", "create|set"),
    _sub("pvesm", "add|set|alloc"),
    r"\bpveum\b.*\s(?:add|modify|delete|remove|passwd)\b",
    r"\bvzdump\b",
    r"\btruncate\b",
    r"(?<![\w.-])(?:rm|mv|chmod|chown|kill|pkill|killall|reboot|poweroff)(?=\s|$|[;&|])",
    r"\bcurl\b.*(?:-X|--request)[\s=]*(?:POST|PUT|PATCH)\b",
    r"\bcurl\b.*\s(?:-d|--data\S*|-F|--form|-T|--upload-file)(?=[\s=]|$)",
    r"\b(?:python3?|perl|ruby|node)\s+-[ce]\b",
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
        code = main(sys.stdin.read(), LOG_PATH)
    except Exception:  # noqa: BLE001
        code = 0
    sys.exit(code)
