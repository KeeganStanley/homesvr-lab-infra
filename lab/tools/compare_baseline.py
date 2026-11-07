#!/usr/bin/env python3
"""Compare two vmstat baseline CSVs (see lab/phase0/baseline.sh).

Pass = CPU-busy and iowait deltas both < 5.0 percentage points and swap did not grow.
CLI: compare_baseline.py before.csv after.csv -> JSON on stdout; exit 0 on pass, 1 on fail.
"""
import csv
import json
import sys

MAX_DELTA_PP = 5.0


def _mean(values):
    values = list(values)
    return sum(values) / len(values)


def _busy(rows):
    return _mean(float(r["us"]) + float(r["sy"]) for r in rows)


def _iowait(rows):
    return _mean(float(r["wa"]) for r in rows)


def _swap(rows):
    return max(int(float(r["swpd_kib"])) for r in rows)


def compare_baseline(before, after):
    cpu = _busy(after) - _busy(before)
    iow = _iowait(after) - _iowait(before)
    swap = _swap(after) - _swap(before)
    return {
        "cpu_busy_delta_pp": cpu,
        "iowait_delta_pp": iow,
        "swap_growth_kib": swap,
        "pass": cpu < MAX_DELTA_PP and iow < MAX_DELTA_PP and swap <= 0,
    }


def _load(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path}: no samples")
    return rows


def main(argv):
    if len(argv) != 3:
        print("usage: compare_baseline.py before.csv after.csv", file=sys.stderr)
        return 2
    result = compare_baseline(_load(argv[1]), _load(argv[2]))
    print(json.dumps(result))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
