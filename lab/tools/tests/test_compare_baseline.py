import csv
import json
import subprocess
import sys
from pathlib import Path

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


def test_swap_growth_fails():
    r = compare_baseline(rows(swpd=0), rows(swpd=1024))
    assert r["swap_growth_kib"] == 1024
    assert r["pass"] is False


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
    p = run_cli(tmp_path, rows(), rows(swpd=2048))
    assert p.returncode == 1
    assert json.loads(p.stdout)["pass"] is False
