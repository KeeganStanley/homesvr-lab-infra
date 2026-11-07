"""Off-host tests for f4-cred-boundary.sh and f5-audit-check.sh, using fake ssh/curl/pct/pvesh."""
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
F4 = HERE / "f4-cred-boundary.sh"
F5 = HERE / "f5-audit-check.sh"
PROD_IP = "192.0.2.77"  # documentation address; never a real one


def fake(path, body):
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)
    return path


def f4_env(tmp_path, ssh_rc=255, http="401"):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_text("k")
    (ssh_dir / "id_ed25519.pub").write_text("k")
    (ssh_dir / "known_hosts").write_text("lab only")
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "innocent.txt").write_text("nothing here")
    token = tmp_path / "token"
    token.write_text("PVEAPIToken=claude@pve!ops=secret")
    calls = tmp_path / "calls"
    ssh = fake(tmp_path / "ssh-bin", f'echo "$@" >> "{calls}"; exit {ssh_rc}\n')
    curl = fake(tmp_path / "curl-bin", f'echo "$@" >> "{calls}"; printf "{http}"\n')
    env = dict(os.environ, SSH=str(ssh), CURL=str(curl), SSH_DIR=str(ssh_dir),
               TOKEN_FILE=str(token), GREP_DIRS=str(scan))
    return env, ssh_dir, scan, calls


def run_f4(env):
    return subprocess.run(["bash", str(F4), PROD_IP], env=env, capture_output=True, text=True, timeout=30)


def test_f4_all_pass(tmp_path):
    env, _, _, calls = f4_env(tmp_path)
    p = run_f4(env)
    assert p.returncode == 0, p.stdout
    assert p.stdout.count("PASS") == 4 and "FAIL" not in p.stdout
    assert PROD_IP not in p.stdout + p.stderr  # output gets pasted into a public repo
    # ssh must not leave the prod IP in known_hosts
    assert "UserKnownHostsFile=/dev/null" in calls.read_text()
    assert "BatchMode=yes" in calls.read_text()


def test_f4_fails_if_ssh_to_prod_succeeds(tmp_path):
    env, *_ = f4_env(tmp_path, ssh_rc=0)
    p = run_f4(env)
    assert p.returncode == 1
    assert "FAIL" in p.stdout.splitlines()[0]


def test_f4_fails_if_api_does_not_return_401(tmp_path):
    env, *_ = f4_env(tmp_path, http="200")
    p = run_f4(env)
    assert p.returncode == 1
    assert "FAIL" in p.stdout.splitlines()[1]


def test_f4_fails_if_prod_ip_found_on_disk_without_printing_it(tmp_path):
    env, _, scan, _ = f4_env(tmp_path)
    (scan / "leak.conf").write_text(f"host={PROD_IP}\n")
    p = run_f4(env)
    assert p.returncode == 1
    assert "FAIL" in p.stdout.splitlines()[2]
    assert "leak.conf" in p.stdout
    assert PROD_IP not in p.stdout + p.stderr


def test_f4_fails_on_unexpected_ssh_dir_file(tmp_path):
    env, ssh_dir, _, _ = f4_env(tmp_path)
    (ssh_dir / "id_rsa").write_text("prod key?")
    p = run_f4(env)
    assert p.returncode == 1
    assert "FAIL" in p.stdout.splitlines()[3]


def test_f4_rejects_missing_argument(tmp_path):
    env, *_ = f4_env(tmp_path)
    p = subprocess.run(["bash", str(F4)], env=env, capture_output=True, text=True)
    assert p.returncode == 2


def test_f5_collects_data_and_reports(tmp_path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(json.dumps({"ts": "2026-11-07T17:05:00Z", "session_id": "s", "tool": "Bash",
                                 "input": {"command": "pct destroy 199"}, "prod_tier": "destructive"}) + "\n")
    calls = tmp_path / "calls"
    pct = fake(tmp_path / "pct", f'echo "pct $*" >> "{calls}"; cat "{audit}"\n')
    pvesh = fake(tmp_path / "pvesh",
                 f'echo "pvesh $*" >> "{calls}"; echo \'[{{"type":"vzdestroy","id":"199"}}]\'\n')
    env = dict(os.environ, PCT=str(pct), PVESH=str(pvesh), NODE="pve-lab")
    p = subprocess.run(["bash", str(F5), "2026-11-07T17:00:00Z", "1"], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "AUDIT_LINES=1" in p.stdout and "PVE_TASKS=1" in p.stdout and "RESULT=PASS" in p.stdout
    log = calls.read_text()
    assert "pct exec 100 -- cat /var/log/claude-audit/audit.jsonl" in log
    assert "/nodes/pve-lab/tasks" in log and "--since 1794070800" in log  # epoch of 2026-11-07T17:00:00Z


def test_f5_rejects_bad_arguments():
    p = subprocess.run(["bash", str(F5), "not-a-ts"], capture_output=True, text=True)
    assert p.returncode == 2
