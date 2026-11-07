#!/usr/bin/env python3
"""F5 helper: compare the claude-ops audit log with the lab's PVE task log.

CLI: f5_match.py audit.jsonl tasks.json SINCE_ISO MIN_COUNT
Prints AUDIT_LINES=, PVE_TASKS=, UNMATCHED=<command> (per miss) and RESULT=PASS|FAIL.
Exit 0 on PASS, 1 on FAIL. PASS = audit lines since SINCE >= MIN_COUNT and every
`pct|qm create|start|stop|shutdown|destroy <vmid>` in those lines has a PVE task of the
matching type (pct -> vz*, qm -> qm*) and id. `pct set` etc. make no task and are ignored.
"""
import json
import re
import sys
from datetime import datetime, timezone

_CMD = re.compile(r"\b(pct|qm)\s+(create|start|stop|shutdown|destroy)\s+(\d+)\b")
_PREFIX = {"pct": "vz", "qm": "qm"}


def parse_ts(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def _records(audit_lines, since):
    for raw in audit_lines:
        try:
            rec = json.loads(raw)
            if parse_ts(rec["ts"]) >= since:
                yield rec
        except (ValueError, KeyError, TypeError, AttributeError):
            continue


def evaluate(audit_lines, tasks, since, min_count):
    records = list(_records(audit_lines, since))
    have = {(str(t.get("type")), str(t.get("id"))) for t in tasks}
    unmatched = []
    for rec in records:
        if rec.get("tool") != "Bash" or not isinstance(rec.get("input"), dict):
            continue
        for tool, verb, vmid in _CMD.findall(str(rec["input"].get("command", ""))):
            if (_PREFIX[tool] + verb, vmid) not in have:
                unmatched.append(f"{tool} {verb} {vmid}")
    ok = len(records) >= min_count and not unmatched
    return {
        "audit_lines": len(records),
        "pve_tasks": len(tasks),
        "unmatched": unmatched,
        "result": "PASS" if ok else "FAIL",
    }


def main(argv):
    if len(argv) != 5:
        print("usage: f5_match.py audit.jsonl tasks.json SINCE_ISO MIN_COUNT", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        audit = f.read().splitlines()
    with open(argv[2], encoding="utf-8") as f:
        tasks = json.load(f)
    r = evaluate(audit, tasks, parse_ts(argv[3]), int(argv[4]))
    print(f"AUDIT_LINES={r['audit_lines']}")
    print(f"PVE_TASKS={r['pve_tasks']}")
    for u in r["unmatched"]:
        print(f"UNMATCHED={u}")
    print(f"RESULT={r['result']}")
    return 0 if r["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
