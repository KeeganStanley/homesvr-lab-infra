"""Off-host test of 20-create-claude-ops.sh with fake pct / pveam / pveum."""
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "20-create-claude-ops.sh"
LAB_IP = "10.9.8.7"  # private example address


def fake(path, body):
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


def setup(tmp_path):
    (tmp_path / "push").mkdir()
    fake(tmp_path / "pct", '''echo "pct $*" >> "$LOG"
case "$1" in
  status) [ -f "$STATE" ];;
  create) echo "umask=$(umask)" >> "$LOG"; touch "$STATE";;
  exec) shift 2; [ "$1" = -- ] && shift
        if [ "$1" = cat ]; then echo "ssh-ed25519 AAAAFAKEKEY claude-ops"; fi;;
  push) echo "pushmode=$(stat -c %a "$3") $4" >> "$LOG"; cp "$3" "$PUSHDIR/$(echo "$4" | tr / _)";;
  *) true;;
esac
''')
    fake(tmp_path / "pveam", '''case "$1" in
  available) printf 'system  debian-13-standard_13.0-1_amd64.tar.zst\\nsystem  debian-13-standard_13.2-1_amd64.tar.zst\\n';;
  list) ;;
  *) echo "pveam $*" >> "$LOG";;
esac
''')
    fake(tmp_path / "pveum", '''echo "pveum $*" >> "$LOG"
if [ "$1 $2 $3" = "user token add" ]; then
  echo '{"full-tokenid":"claude@pve!ops","value":"SECRET-123"}'
fi
''')
    (tmp_path / "inst.sh").write_text("#!/bin/true\n")
    (tmp_path / "host_key.pub").write_text("ssh-ed25519 AAAAHOSTKEY root@pve-lab\n")
    return dict(os.environ, LOG=str(tmp_path / "log"), STATE=str(tmp_path / "state"),
                PCT=str(tmp_path / "pct"), PVEAM=str(tmp_path / "pveam"), PVEUM=str(tmp_path / "pveum"),
                AUTH_KEYS=str(tmp_path / "authorized_keys"), INSTALL_SCRIPT=str(tmp_path / "inst.sh"),
                PUSHDIR=str(tmp_path / "push"), HOST_KEY_FILE=str(tmp_path / "host_key.pub"),
                LAB_IP=LAB_IP)


def run(env):
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60,
                          preexec_fn=lambda: os.umask(0o022))


def test_creates_ct_with_plan_settings(tmp_path):
    env = setup(tmp_path)
    p = run(env)
    assert p.returncode == 0, p.stdout + p.stderr
    log = (tmp_path / "log").read_text()
    create = next(line for line in log.splitlines() if line.startswith("pct create"))
    for want in ("100 local:vztmpl/debian-13-standard_13.2-1_amd64.tar.zst", "--unprivileged 1",
                 "--features nesting=1", "--cores 2", "--memory 2048", "--swap 512",
                 "--rootfs local-lvm:16", "--net0 name=eth0,bridge=vmbr0,ip=dhcp", "--onboot 1"):
        assert want in create


def test_token_and_key_provisioned_without_leaking_secret(tmp_path):
    env = setup(tmp_path)
    assert run(env).returncode == 0
    token = (tmp_path / "push/_home_claude_.config_pve-lab_token").read_text()
    assert token == "PVEAPIToken=claude@pve!ops=SECRET-123\n"
    assert "SECRET-123" not in (tmp_path / "log").read_text()
    assert "ssh-ed25519 AAAAFAKEKEY claude-ops" in (tmp_path / "authorized_keys").read_text()


def test_agent_can_ssh_to_pve_lab_without_prompts(tmp_path):
    # Plan Task 4 step 3 runs `ssh -o BatchMode=yes root@<LAB_IP>`: BatchMode fails on an unknown host key.
    env = setup(tmp_path)
    assert run(env).returncode == 0
    known = (tmp_path / "push/_home_claude_.ssh_known_hosts").read_text()
    assert known == f"pve-lab,{LAB_IP} ssh-ed25519 AAAAHOSTKEY\n"
    config = (tmp_path / "push/_home_claude_.ssh_config").read_text()
    assert "Host pve-lab" in config and f"HostName {LAB_IP}" in config and "User root" in config
    log = (tmp_path / "log").read_text()
    assert "chown claude:claude /home/claude/.ssh/config /home/claude/.ssh/known_hosts" in log


def test_refuses_when_ct_exists(tmp_path):
    env = setup(tmp_path)
    (tmp_path / "state").write_text("")
    p = run(env)
    assert p.returncode == 1
    assert "already exists" in p.stderr


def test_pct_create_runs_with_a_normal_umask(tmp_path):
    # An unprivileged CT's rootfs dir is created under the caller's umask. With umask 077 it is 0700
    # root-only and the container's mapped root cannot open it: "tar: .../rootfs: Cannot open: Permission denied".
    env = setup(tmp_path)
    assert run(env).returncode == 0
    umask = int(next(line for line in (tmp_path / "log").read_text().splitlines()
                     if line.startswith("umask=")).split("=")[1], 8)
    assert umask & 0o055 == 0, f"group/other r-x masked out: umask {umask:04o}"


def test_secret_files_are_still_private(tmp_path):
    env = setup(tmp_path)
    assert run(env).returncode == 0
    log = (tmp_path / "log").read_text()
    assert "pushmode=600 /home/claude/.config/pve-lab/token" in log
    assert oct((tmp_path / "authorized_keys").stat().st_mode & 0o777) == "0o600"
