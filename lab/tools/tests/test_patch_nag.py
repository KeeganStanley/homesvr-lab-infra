import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patch_nag import patch_text  # noqa: E402

TOOL = Path(__file__).resolve().parents[1] / "patch_nag.py"

SAMPLE = """\
	    if (res === null || res === undefined || !res || res
		.data.status.toLowerCase() !== 'active') {
		Ext.Msg.show({
		    title: gettext('No valid subscription'),
		    icon: Ext.Msg.WARNING,
		    message: Proxmox.Utils.getNoSubKeyHtml(res.data.url),
		    buttons: Ext.Msg.OK,
		    callback: function(btn) {
			if (btn !== 'ok') {
			    return;
			}
			orig_cmd();
		    },
		});
	    } else {
		orig_cmd();
	    }
"""


def run(path, *extra):
    return subprocess.run([sys.executable, str(TOOL), *extra, str(path)], capture_output=True, text=True)


def test_patch_text_disables_the_nag_dialog_and_keeps_the_rest():
    out, changed = patch_text(SAMPLE)
    assert changed is True
    assert "void({ //Ext.Msg.show({" in out
    assert "title: gettext('No valid subscription')" in out  # becomes a harmless object literal
    assert "} else {\n\t\torig_cmd();" in out
    assert out.count("Ext.Msg.show(") == 1                    # only the commented one remains


def test_patch_text_is_idempotent():
    once, _ = patch_text(SAMPLE)
    twice, changed = patch_text(once)
    assert changed is False
    assert twice == once


def test_unrecognised_text_is_reported_not_guessed():
    out, changed = patch_text("var x = 1;\n")
    assert changed is False
    assert out is None


def test_cli_patches_file_in_place_and_preserves_mode(tmp_path):
    f = tmp_path / "proxmoxlib.js"
    f.write_text(SAMPLE)
    f.chmod(0o644)
    p = run(f)
    assert p.returncode == 0, p.stderr
    assert "void({ //Ext.Msg.show({" in f.read_text()
    assert oct(f.stat().st_mode & 0o777) == "0o644"


def test_cli_second_run_changes_nothing(tmp_path):
    f = tmp_path / "proxmoxlib.js"
    f.write_text(SAMPLE)
    assert run(f).returncode == 0
    before = f.read_bytes()
    p = run(f)
    assert p.returncode == 0
    assert f.read_bytes() == before
    assert "already" in p.stdout


def test_cli_unrecognised_file_exits_1_and_is_untouched(tmp_path):
    f = tmp_path / "proxmoxlib.js"
    f.write_text("var x = 1;\n")
    p = run(f)
    assert p.returncode == 1
    assert f.read_text() == "var x = 1;\n"
    assert "not recognised" in p.stderr


def test_cli_missing_file_exits_nonzero_without_traceback(tmp_path):
    p = run(tmp_path / "nope.js")
    assert p.returncode == 2
    assert "Traceback" not in p.stderr


def test_quiet_suppresses_normal_output(tmp_path):
    f = tmp_path / "proxmoxlib.js"
    f.write_text(SAMPLE)
    p = run(f, "--quiet")
    assert p.returncode == 0 and p.stdout == ""
