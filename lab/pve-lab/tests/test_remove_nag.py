"""Off-host test of 15-remove-nag.sh using DEST_ROOT and a sample proxmoxlib.js."""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "15-remove-nag.sh"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "tests"))
from test_patch_nag import SAMPLE  # noqa: E402


def run(tmp_path, js_text=SAMPLE, host="pve-lab"):
    js = tmp_path / "proxmoxlib.js"
    js.write_text(js_text)
    root = tmp_path / "root"
    env = dict(os.environ, DEST_ROOT=str(root), PROXMOXLIB_JS=str(js), HOSTNAME_OVERRIDE=host)
    p = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    return p, js, root


def test_patches_and_installs_reapply_hook(tmp_path):
    p, js, root = run(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "void({ //Ext.Msg.show({" in js.read_text()
    tool = root / "usr/local/sbin/pve-nag-patch"
    assert tool.is_file() and os.access(tool, os.X_OK)
    conf = (root / "etc/apt/apt.conf.d/99-pve-nag-patch").read_text()
    assert "DPkg::Post-Invoke" in conf and "/usr/local/sbin/pve-nag-patch" in conf
    assert "|| true" in conf  # a failed re-patch must never break apt


def test_rerun_is_harmless(tmp_path):
    p, js, root = run(tmp_path)
    assert p.returncode == 0
    before = js.read_bytes()
    p2 = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True,
                        env=dict(os.environ, DEST_ROOT=str(root), PROXMOXLIB_JS=str(js), HOSTNAME_OVERRIDE="pve-lab"))
    assert p2.returncode == 0
    assert js.read_bytes() == before


def test_refuses_to_run_on_any_other_host(tmp_path):
    p, js, root = run(tmp_path, host="aklypta")
    assert p.returncode == 1
    assert "pve-lab" in p.stderr
    assert js.read_text() == SAMPLE
    assert not (root / "usr/local/sbin/pve-nag-patch").exists()


def test_unrecognised_js_installs_no_hook(tmp_path):
    p, js, root = run(tmp_path, js_text="var x = 1;\n")
    assert p.returncode == 1
    assert js.read_text() == "var x = 1;\n"
    assert not (root / "etc/apt/apt.conf.d/99-pve-nag-patch").exists()
