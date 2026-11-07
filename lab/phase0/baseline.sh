#!/usr/bin/env bash
# Sample host CPU/iowait/swap with vmstat, one row per interval (default 60 s).
# Usage: baseline.sh <minutes> <out.csv>
# CSV header: ts,us,sy,id,wa,free_kib,swpd_kib. Read-only apart from the output file.
set -euo pipefail

if [ $# -ne 2 ] || ! [[ $1 =~ ^[1-9][0-9]*$ ]]; then
  echo "usage: baseline.sh <minutes> <out.csv>" >&2
  exit 2
fi
minutes=$1
out=$2
interval=${INTERVAL_S:-60}
[ ! -e "$out" ] || { echo "refusing to overwrite $out" >&2; exit 2; }

samples=$((minutes * 60 / interval))
[ "$samples" -ge 1 ] || samples=1

echo "ts,us,sy,id,wa,free_kib,swpd_kib" > "$out"
# vmstat's first report is the average since boot: ask for one extra and drop it.
# Columns: r b swpd free buff cache si so bi bo in cs us sy id wa st
# A read loop (not awk) so each row is timestamped as it arrives; awk may block-buffer its input.
n=0
while read -r _ _ swpd free _ _ _ _ _ _ _ _ us sy id wa _; do
  [[ $swpd =~ ^[0-9]+$ ]] || continue          # header lines
  n=$((n + 1))
  [ "$n" -gt 1 ] || continue                   # since-boot average
  printf '%(%Y-%m-%dT%H:%M:%SZ)T,%s,%s,%s,%s,%s,%s\n' -1 "$us" "$sy" "$id" "$wa" "$free" "$swpd" >> "$out"
done < <(TZ=UTC stdbuf -oL vmstat -n "$interval" $((samples + 1)))
