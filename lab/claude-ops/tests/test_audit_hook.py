import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_hook import build_record, classify, main  # noqa: E402

KEYS = {"ts", "session_id", "tool", "input", "prod_tier"}


def bash(cmd):
    return classify("Bash", {"command": cmd})


@pytest.mark.parametrize("cmd", [
    "pveversion",
    "pct list",
    "zpool status -v",
    "journalctl -u jellyfin -n 50",
])
def test_classify_read(cmd):
    assert bash(cmd) == "read"


@pytest.mark.parametrize("cmd", [
    "pct set 101 -memory 512",
    "systemctl restart jellyfin",
    "apt install -y jq",
    "git push origin feature/x",
    "echo x > /etc/foo",
])
def test_classify_change(cmd):
    assert bash(cmd) == "change"


@pytest.mark.parametrize("cmd", [
    "pct destroy 105",
    "zfs destroy tank/media",
    "rm -rf /var/lib/x",
    "zpool detach tank sdb",
])
def test_classify_destructive(cmd):
    assert bash(cmd) == "destructive"


@pytest.mark.parametrize("cmd", [
    "pct list 2>/dev/null",
    "pveversion 2>&1",
    "git add notes.txt",
    "grep -r 'foo' /etc",
])
def test_harmless_lookalikes_are_read(cmd):
    assert bash(cmd) == "read"


def test_compound_command_takes_highest_tier():
    assert bash("pct list; pct destroy 199") == "destructive"
    assert bash("pveversion && systemctl restart pveproxy") == "change"


def test_tee_to_path_is_change():
    assert bash("echo x | tee /etc/foo") == "change"


def test_edit_tool_is_change():
    assert classify("Edit", {"file_path": "/x"}) == "change"
    assert classify("Write", {"file_path": "/x"}) == "change"
    assert classify("NotebookEdit", {}) == "change"


@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "WebSearch", "WebFetch"])
def test_read_tools_are_read(tool):
    assert classify(tool, {}) == "read"


def test_unknown_tool_is_change():
    assert classify("mcp__x__y", {}) == "change"


def test_bash_without_command_is_read():
    assert classify("Bash", {}) == "read"
    assert classify("Bash", None) == "read"


def test_build_record_has_all_keys():
    now = datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc)
    payload = {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": "pct destroy 1"}}
    rec = build_record(payload, now)
    assert set(rec) == KEYS
    assert rec["ts"] == "2026-11-07T12:00:00Z"
    assert rec["session_id"] == "s1"
    assert rec["tool"] == "Bash"
    assert rec["input"] == {"command": "pct destroy 1"}
    assert rec["prod_tier"] == "destructive"


def test_build_record_tolerates_missing_fields():
    rec = build_record({}, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert set(rec) == KEYS


def test_main_appends_jsonl(tmp_path):
    log = tmp_path / "audit.jsonl"
    p1 = json.dumps({"session_id": "s", "tool_name": "Bash", "tool_input": {"command": "pveversion"}})
    p2 = json.dumps({"session_id": "s", "tool_name": "Edit", "tool_input": {"file_path": "/x"}})
    assert main(p1, str(log)) == 0
    assert main(p2, str(log)) == 0
    lines = log.read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        assert set(json.loads(line)) == KEYS
    assert json.loads(lines[0])["prod_tier"] == "read"
    assert json.loads(lines[1])["prod_tier"] == "change"


def test_main_returns_0_on_malformed_json(tmp_path):
    log = tmp_path / "audit.jsonl"
    assert main("{not json", str(log)) == 0
    assert not log.exists()


@pytest.mark.parametrize("text", ["", "[]", '"x"', "null", "42"])
def test_main_returns_0_on_non_object_json(tmp_path, text):
    log = tmp_path / "audit.jsonl"
    assert main(text, str(log)) == 0
    assert not log.exists()


def test_main_returns_0_when_log_unwritable(tmp_path):
    # Parent "directory" is a regular file, so the log can't be created even for root
    # (chmod-based read-only dirs don't stop root, which is how CI/containers run).
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    payload = json.dumps({"session_id": "s", "tool_name": "Bash", "tool_input": {"command": "ls"}})
    assert main(payload, str(blocker / "audit.jsonl")) == 0


def test_settings_json_bypass_mode_with_audit_hook():
    s = json.loads((Path(__file__).resolve().parents[1] / "settings.json").read_text())
    assert s["permissions"]["defaultMode"] == "bypassPermissions"
    assert s["hooks"]["PreToolUse"] == [
        {"matcher": "*", "hooks": [{"type": "command", "command": "/usr/local/bin/claude-audit-hook"}]}
    ]


@pytest.mark.parametrize("cmd", [
    "pvesh delete /nodes/pve-lab/lxc/199",
    "ssh root@lab pvesh delete /nodes/pve-lab/qemu/100",
])
def test_pvesh_delete_is_destructive(cmd):
    assert bash(cmd) == "destructive"


@pytest.mark.parametrize("cmd", [
    "pvesh create /nodes/pve-lab/lxc -vmid 199",
    "pvesh set /nodes/pve-lab/config -description x",
    "rm /etc/foo.conf",
    "mv /etc/a /etc/b",
    "chmod 600 /etc/foo",
    "chown root:root /etc/foo",
    "kill -9 1234",
    "pkill jellyfin",
    "reboot",
    "poweroff",
])
def test_everyday_mutations_are_change_not_read(cmd):
    assert bash(cmd) == "change"


def test_pvesh_get_and_lookalike_words_stay_read():
    assert bash("pvesh get /nodes/pve-lab/status") == "read"
    assert bash("ls /var/lib/removed-items") == "read"
    assert bash("echo permission denied") == "read"
