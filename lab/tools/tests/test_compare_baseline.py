import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compare_baseline import compare_baseline  # noqa: E402

TOOL = Path(__file__).resolve().parents[1] / "compare_baseline.py"


def rows(us=5, sy=5, wa=1, swpd=0, n=3):
    return [
        {"ts": str(i), "us": us, "sy": sy, "id": 100 - us - sy - wa,
         "wa": wa, "free_kib": 1000, "swpd_kib": swpd}
        for i in range(n)
    ]


def test_identical_runs_pass():
    r = compare_baseline(rows(), rows())
    assert r["pass"] is True
    assert r["cpu_busy_delta_pp"] == 0
    assert r["iowait_delta_pp"] == 0
    assert r["swap_growth_kib"] == 0


def test_cpu_delta_5pp_fails():
    r = compare_baseline(rows(us=5, sy=5), rows(us=10, sy=5))  # 10 -> 15
    assert r["cpu_busy_delta_pp"] == 5.0
    assert r["pass"] is False


def test_iowait_4pp_passes():
    r = compare_baseline(rows(wa=1), rows(wa=5))
    assert r["iowait_delta_pp"] == 4.0
    assert r["pass"] is True


def test_swap_growth_beyond_tolerance_fails():
    r = compare_baseline(rows(swpd=0), rows(swpd=8192))
    assert r["swap_growth_kib"] == 8192
    assert r["pass"] is False


@pytest.mark.parametrize("growth", [256, 1536, 4096])
def test_small_swap_growth_within_default_tolerance_passes(growth):
    # Observed on the real host: +1536 KiB and +256 KiB with no real memory pressure.
    r = compare_baseline(rows(swpd=0), rows(swpd=growth))
    assert r["swap_growth_kib"] == growth
    assert r["pass"] is True


def test_swap_growth_one_kib_over_tolerance_fails():
    assert compare_baseline(rows(swpd=0), rows(swpd=4097))["pass"] is False


def test_tolerance_is_reported_and_overridable():
    assert compare_baseline(rows(), rows())["swap_tolerance_kib"] == 4096
    strict = compare_baseline(rows(swpd=0), rows(swpd=1024), swap_tolerance_kib=0)
    assert strict["swap_tolerance_kib"] == 0
    assert strict["pass"] is False


def test_swap_shrinking_passes():
    assert compare_baseline(rows(swpd=2048), rows(swpd=0))["pass"] is True


def write_csv(path, data):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)


def run_cli(tmp_path, before, after):
    b, a = tmp_path / "b.csv", tmp_path / "a.csv"
    write_csv(b, before)
    write_csv(a, after)
    return subprocess.run([sys.executable, str(TOOL), str(b), str(a)],
                          capture_output=True, text=True)


def test_cli_pass_exits_0_and_prints_json(tmp_path):
    p = run_cli(tmp_path, rows(), rows())
    assert p.returncode == 0
    assert json.loads(p.stdout)["pass"] is True


def test_cli_fail_exits_1(tmp_path):
    p = run_cli(tmp_path, rows(), rows(swpd=8192))
    assert p.returncode == 1
    assert json.loads(p.stdout)["pass"] is False


def test_cli_swap_tolerance_flag(tmp_path):
    p = run_cli(tmp_path, rows(), rows(swpd=2048))
    assert p.returncode == 0                         # within the default 4096 KiB
    b, a = tmp_path / "b.csv", tmp_path / "a.csv"
    strict = subprocess.run([sys.executable, str(TOOL), "--swap-tolerance-kib", "0", str(b), str(a)],
                            capture_output=True, text=True)
    assert strict.returncode == 1
    assert json.loads(strict.stdout)["swap_tolerance_kib"] == 0
