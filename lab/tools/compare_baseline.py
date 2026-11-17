#!/usr/bin/env python3
"""Compare two vmstat baseline CSVs (see lab/phase0/baseline.sh).

Pass = CPU-busy and iowait deltas both < 5.0 percentage points and swap growth <= a tolerance
(default 4096 KiB). The original rule was "swap growth <= 0", but on the real host two clean
comparisons showed harmless growth of +1536 KiB and +256 KiB (8 GiB swap, ~40 MiB used);
genuine memory pressure shows as tens of MiB or more.
CLI: compare_baseline.py [--swap-tolerance-kib N] before.csv after.csv -> JSON on stdout;
exit 0 on pass, 1 on fail.
"""
import csv
import json
import sys

MAX_DELTA_PP = 5.0
DEFAULT_SWAP_TOLERANCE_KIB = 4096


def _mean(values):
    values = list(values)
    return sum(values) / len(values)


def _busy(rows):
    return _mean(float(r["us"]) + float(r["sy"]) for r in rows)


def _iowait(rows):
    return _mean(float(r["wa"]) for r in rows)


def _swap(rows):
    return max(int(float(r["swpd_kib"])) for r in rows)


def compare_baseline(before, after, swap_tolerance_kib=DEFAULT_SWAP_TOLERANCE_KIB):
    cpu = _busy(after) - _busy(before)
    iow = _iowait(after) - _iowait(before)
    swap = _swap(after) - _swap(before)
    return {
        "cpu_busy_delta_pp": cpu,
        "iowait_delta_pp": iow,
        "swap_growth_kib": swap,
        "swap_tolerance_kib": swap_tolerance_kib,
        "pass": cpu < MAX_DELTA_PP and iow < MAX_DELTA_PP and swap <= swap_tolerance_kib,
    }


def _load(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path}: no samples")
    return rows


def main(argv):
    args = argv[1:]
    tolerance = DEFAULT_SWAP_TOLERANCE_KIB
    if args[:1] == ["--swap-tolerance-kib"]:
        try:
            tolerance = int(args[1])
        except (IndexError, ValueError):
            print("--swap-tolerance-kib needs an integer", file=sys.stderr)
            return 2
        args = args[2:]
    if len(args) != 2:
        print("usage: compare_baseline.py [--swap-tolerance-kib N] before.csv after.csv", file=sys.stderr)
        return 2
    result = compare_baseline(_load(args[0]), _load(args[1]), tolerance)
    print(json.dumps(result))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
