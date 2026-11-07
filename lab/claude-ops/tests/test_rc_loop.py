import configparser
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RC_LOOP = HERE / "rc-loop.sh"
SERVICE = HERE / "claude-rc.service"


def run_loop(tmp_path, exit_code, iterations=2):
    workdir = tmp_path / "lab"
    workdir.mkdir()
    seen = tmp_path / "seen"
    fake = tmp_path / "claude"
    fake.write_text(f'#!/usr/bin/env bash\n{{ pwd; printf "%s|" "$@"; echo; }} >> "{seen}"\nexit {exit_code}\n')
    fake.chmod(0o755)
    log = tmp_path / "rc-loop.log"
    env = dict(os.environ, CLAUDE_BIN=str(fake), WORKDIR=str(workdir), LOG_FILE=str(log),
               SLEEP_S="0", MAX_ITERATIONS=str(iterations))
    p = subprocess.run(["bash", str(RC_LOOP)], env=env, capture_output=True, text=True, timeout=30)
    return p, log, seen, workdir


def test_restarts_after_every_exit_and_logs_exit_code(tmp_path):
    p, log, seen, _ = run_loop(tmp_path, exit_code=3, iterations=2)
    assert p.returncode == 0
    lines = log.read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ ", line)
        assert "exited with code 3" in line
    assert len(seen.read_text().splitlines()) == 4  # (cwd, args) per run


def test_clean_exit_is_also_restarted_and_logged(tmp_path):
    p, log, _, _ = run_loop(tmp_path, exit_code=0, iterations=2)
    lines = log.read_text().splitlines()
    assert len(lines) == 2 and all("exited with code 0" in line for line in lines)


def test_runs_remote_control_in_workdir_with_expected_args(tmp_path):
    _, _, seen, workdir = run_loop(tmp_path, exit_code=1, iterations=1)
    cwd, args = seen.read_text().splitlines()[:2]
    assert Path(cwd).resolve() == workdir.resolve()
    assert args == "remote-control|--name|HomeSVR Lab|--spawn|worktree|--permission-mode|bypassPermissions|"


def test_service_unit_matches_plan():
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read(SERVICE)
    svc = cp["Service"]
    assert svc["User"] == "claude"
    assert svc["Type"] == "forking"
    assert svc["ExecStart"] == "/usr/bin/tmux new-session -d -s rc /home/claude/rc-loop.sh"
    assert svc["ExecStop"] == "/usr/bin/tmux kill-session -t rc"
    assert svc["Restart"] == "always"
    assert svc["RestartSec"] == "30"
    assert cp["Install"]["WantedBy"] == "multi-user.target"
