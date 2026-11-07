import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from f5_match import evaluate  # noqa: E402

TOOL = Path(__file__).resolve().parents[1] / "f5_match.py"
SINCE = datetime(2026, 11, 7, 17, 0, 0, tzinfo=timezone.utc)


def line(cmd, ts="2026-11-07T17:05:00Z", tool="Bash"):
    inp = {"command": cmd} if tool == "Bash" else {"file_path": cmd}
    return json.dumps({"ts": ts, "session_id": "s", "tool": tool, "input": inp, "prod_tier": "read"})


def task(type_, vmid):
    return {"type": type_, "id": str(vmid), "upid": f"UPID:pve-lab:...:{type_}:{vmid}:root@pam:"}


def test_pass_when_enough_lines_and_all_tasks_match():
    audit = [line("pveversion"), line("pct create 199 tmpl"), line("pct start 199"),
             line("pct stop 199"), line("pct destroy 199")]
    tasks = [task("vzcreate", 199), task("vzstart", 199), task("vzstop", 199), task("vzdestroy", 199)]
    r = evaluate(audit, tasks, SINCE, 5)
    assert r["audit_lines"] == 5
    assert r["pve_tasks"] == 4
    assert r["unmatched"] == []
    assert r["result"] == "PASS"


def test_fail_when_fewer_lines_than_min_count():
    r = evaluate([line("pveversion")], [], SINCE, 20)
    assert r["audit_lines"] == 1
    assert r["result"] == "FAIL"


def test_fail_when_destroy_has_no_matching_task():
    r = evaluate([line("pct destroy 199")], [], SINCE, 1)
    assert r["result"] == "FAIL"
    assert r["unmatched"] == ["pct destroy 199"]


def test_pct_set_needs_no_task():
    r = evaluate([line("pct set 199 -memory 512")], [], SINCE, 1)
    assert r["result"] == "PASS"


def test_pct_and_qm_use_different_task_types():
    r = evaluate([line("qm start 199")], [task("vzstart", 199)], SINCE, 1)
    assert r["unmatched"] == ["qm start 199"]
    assert r["result"] == "FAIL"
    r = evaluate([line("qm start 199")], [task("qmstart", 199)], SINCE, 1)
    assert r["result"] == "PASS"


def test_task_must_match_vmid():
    r = evaluate([line("pct start 199")], [task("vzstart", 200)], SINCE, 1)
    assert r["result"] == "FAIL"


def test_only_lines_since_timestamp_count_boundary_inclusive():
    audit = [line("ls", ts="2026-11-07T16:59:59Z"), line("ls", ts="2026-11-07T17:00:00Z"),
             line("ls", ts="2026-11-07T17:00:01Z")]
    assert evaluate(audit, [], SINCE, 1)["audit_lines"] == 2


def test_old_destroy_before_since_is_ignored():
    r = evaluate([line("pct destroy 5", ts="2026-11-07T10:00:00Z")], [], SINCE, 0)
    assert r["unmatched"] == [] and r["result"] == "PASS"


def test_malformed_lines_skipped_and_other_tools_counted_but_not_matched():
    audit = ["{not json", "", line("/etc/foo", tool="Edit"), line("pveversion")]
    r = evaluate(audit, [], SINCE, 2)
    assert r["audit_lines"] == 2
    assert r["result"] == "PASS"


def test_several_commands_in_one_line_each_need_a_task():
    r = evaluate([line("pct start 199 && pct stop 199")], [task("vzstart", 199)], SINCE, 1)
    assert r["unmatched"] == ["pct stop 199"]
    assert r["result"] == "FAIL"


def test_cli_prints_keys_and_exit_codes(tmp_path):
    a, t = tmp_path / "a.jsonl", tmp_path / "t.json"
    a.write_text(line("pct destroy 199") + "\n")
    t.write_text("[]")
    p = subprocess.run([sys.executable, str(TOOL), str(a), str(t), "2026-11-07T17:00:00Z", "1"],
                       capture_output=True, text=True)
    assert p.returncode == 1
    assert "AUDIT_LINES=1" in p.stdout and "PVE_TASKS=0" in p.stdout
    assert "UNMATCHED=pct destroy 199" in p.stdout and "RESULT=FAIL" in p.stdout
    t.write_text(json.dumps([task("vzdestroy", 199)]))
    p = subprocess.run([sys.executable, str(TOOL), str(a), str(t), "2026-11-07T17:00:00Z", "1"],
                       capture_output=True, text=True)
    assert p.returncode == 0 and "RESULT=PASS" in p.stdout
