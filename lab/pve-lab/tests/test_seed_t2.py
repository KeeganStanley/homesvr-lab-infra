"""Off-host tests for the T2 seed scripts (seed-marker-data.sh and 50-seed-t2.sh)."""
import os
import subprocess
from pathlib import Path

PVE_LAB = Path(__file__).resolve().parents[1]
DATA = PVE_LAB / "seed-marker-data.sh"
SEED = PVE_LAB / "50-seed-t2.sh"


def fake(path, body):
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


# ---- seed-marker-data.sh -------------------------------------------------------------------

def run_data(target, *extra):
    return subprocess.run(["bash", str(DATA), str(target), *extra], capture_output=True, text=True)


def test_data_script_creates_files_and_a_valid_manifest(tmp_path):
    target = tmp_path / "marker"
    p = run_data(target)
    assert p.returncode == 0, p.stderr
    files = [f for f in target.rglob("*") if f.is_file() and f.name != "MANIFEST.sha256"]
    assert len(files) >= 20
    assert len({f.parent for f in files}) >= 3                   # nested directories
    assert any(" " in f.name for f in files)                     # awkward names survive the manifest
    ok = subprocess.run(["sha256sum", "-c", "MANIFEST.sha256", "--quiet"], cwd=target,
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr


def test_manifest_does_not_list_itself_and_has_one_line_per_file(tmp_path):
    target = tmp_path / "marker"
    assert run_data(target).returncode == 0
    lines = (target / "MANIFEST.sha256").read_text().splitlines()
    files = [f for f in target.rglob("*") if f.is_file() and f.name != "MANIFEST.sha256"]
    assert len(lines) == len(files)
    assert not any("MANIFEST.sha256" in line for line in lines)


def test_manifest_detects_corruption(tmp_path):
    target = tmp_path / "marker"
    assert run_data(target).returncode == 0
    victim = sorted(f for f in target.rglob("*") if f.is_file() and f.name != "MANIFEST.sha256")[0]
    victim.write_bytes(victim.read_bytes() + b"x")
    ok = subprocess.run(["sha256sum", "-c", "MANIFEST.sha256", "--quiet"], cwd=target,
                        capture_output=True, text=True)
    assert ok.returncode != 0


def test_data_total_size_is_modest(tmp_path):
    target = tmp_path / "marker"
    assert run_data(target).returncode == 0
    total = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    assert 8 * 2**20 <= total <= 64 * 2**20


def test_data_script_refuses_a_non_empty_directory(tmp_path):
    target = tmp_path / "marker"
    target.mkdir()
    (target / "existing").write_text("x")
    p = run_data(target)
    assert p.returncode == 1
    assert (target / "existing").read_text() == "x"


def test_data_script_needs_a_target_argument():
    assert subprocess.run(["bash", str(DATA)], capture_output=True, text=True).returncode == 2


# ---- 50-seed-t2.sh ---------------------------------------------------------------------------

def seed_env(tmp_path, existing=None, template=True):
    (tmp_path / "bin").mkdir(exist_ok=True)
    fake(tmp_path / "bin/pct", '''echo "pct $*" >> "$LOG"
case "$1" in
  status) if [ "$2" = "${EXISTING:-none}" ]; then echo "status: stopped"; exit 0; fi
          [ -f "$TMP/started-$2" ] && { echo "status: running"; exit 0; }
          exit 2;;
  create) touch "$TMP/created-$2";;
  start) touch "$TMP/started-$2";;
  pull) printf 'abc  ./f\\n' > "$4";;
esac
''')
    listing = "Name Size\\nlocal:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst 1G\\nlocal:vztmpl/debian-13-standard_13.2-1_amd64.tar.zst 1G\\nlocal:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst 1G\\n" if template else "Name Size\\n"
    fake(tmp_path / "bin/pveam", f'printf "{listing}"\n')
    fake(tmp_path / "bin/chown", 'echo "chown $*" >> "$LOG"\n')
    return dict(os.environ, TMP=str(tmp_path), LOG=str(tmp_path / "log"), PCT=str(tmp_path / "bin/pct"),
                PVEAM=str(tmp_path / "bin/pveam"), CHOWN=str(tmp_path / "bin/chown"),
                BIND_DIR=str(tmp_path / "t2-bind"), SEED_DIR=str(tmp_path / "t2-seed"),
                EXISTING=existing or "none")


def run_seed(env):
    return subprocess.run(["bash", str(SEED)], env=env, capture_output=True, text=True, timeout=60)


def test_seed_creates_both_cts_with_plan_settings(tmp_path):
    env = seed_env(tmp_path)
    p = run_seed(env)
    assert p.returncode == 0, p.stdout + p.stderr
    log = (tmp_path / "log").read_text()
    creates = [line for line in log.splitlines() if line.startswith("pct create")]
    assert len(creates) == 2
    assert any(line.startswith("pct create 201 local:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst")
               and "--hostname marker-01" in line for line in creates)       # newest template
    assert any(line.startswith("pct create 202") and "--hostname bindmount-01" in line for line in creates)
    for line in creates:
        for want in ("--unprivileged 1", "--rootfs local-lvm:4", "--onboot 0",
                     "--net0 name=eth0,bridge=vmbr0,ip=dhcp"):   # explicit NIC: the loaded run's lesson
            assert want in line


def test_bind_mount_ct_gets_a_host_directory_owned_by_the_mapped_root(tmp_path):
    env = seed_env(tmp_path)
    assert run_seed(env).returncode == 0
    log = (tmp_path / "log").read_text()
    assert f"pct set 202 -mp0 {tmp_path / 't2-bind'},mp=/mnt/data" in log
    assert f"chown 100000:100000 {tmp_path / 't2-bind'}" in log
    assert (tmp_path / "t2-bind").is_dir()


def test_seed_generates_data_in_each_ct_and_keeps_a_host_side_manifest(tmp_path):
    env = seed_env(tmp_path)
    assert run_seed(env).returncode == 0
    log = (tmp_path / "log").read_text()
    assert "pct exec 201 -- bash /root/seed-marker-data.sh /srv/marker" in log
    assert "pct exec 202 -- bash /root/seed-marker-data.sh /mnt/data" in log
    assert (tmp_path / "t2-seed/marker-01.manifest.sha256").is_file()
    assert (tmp_path / "t2-seed/bindmount-01.manifest.sha256").is_file()


def test_seed_refuses_when_a_ct_already_exists_and_changes_nothing(tmp_path):
    env = seed_env(tmp_path, existing="202")
    p = run_seed(env)
    assert p.returncode == 1
    assert "already exists" in p.stderr
    assert not any(line.startswith("pct create") for line in (tmp_path / "log").read_text().splitlines())


def test_seed_reports_a_missing_template_instead_of_exiting_silently(tmp_path):
    env = seed_env(tmp_path, template=False)
    p = run_seed(env)
    assert p.returncode == 1
    assert "template" in p.stderr
