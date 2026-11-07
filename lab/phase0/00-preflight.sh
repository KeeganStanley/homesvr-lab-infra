#!/usr/bin/env bash
# Read-only preflight for the production host. Changes nothing.
# Prints KEY=value lines, then RESULT=PASS|WARN|FAIL. Exit 0 on PASS/WARN, 1 on FAIL.
# The *_FILE / PVESH overrides exist so the script can be exercised off-host.
set -euo pipefail

NESTED_FILE=${NESTED_FILE:-/sys/module/kvm_intel/parameters/nested}
MEMINFO_FILE=${MEMINFO_FILE:-/proc/meminfo}
ARCSTATS_FILE=${ARCSTATS_FILE:-/proc/spl/kstat/zfs/arcstats}
PVESH=${PVESH:-pvesh}
LAB_VMID=900
MIN_MEM_GIB=8
WARN_MEM_GIB=12
MIN_LVM_GIB=128

node=${NODE:-$(hostname)}
result=PASS
reasons=()

fail() { result=FAIL; reasons+=("$1"); }
warn() { [ "$result" = FAIL ] || result=WARN; reasons+=("$1"); }
gib() { awk -v b="$1" 'BEGIN { printf "%.1f", b / 1073741824 }'; }
lt() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a < b) }'; }

# Nested virtualisation
nested=$(cat "$NESTED_FILE" 2>/dev/null || echo missing)
echo "NESTED=$nested"
[ "$nested" = Y ] || fail "nested virtualisation is '$nested', not Y"

# Memory
mem_kib=$(awk '/^MemAvailable:/ { print $2 }' "$MEMINFO_FILE")
mem_gib=$(awk -v k="${mem_kib:-0}" 'BEGIN { printf "%.1f", k / 1048576 }')
echo "MEM_AVAILABLE_GIB=$mem_gib"
if lt "$mem_gib" "$MIN_MEM_GIB"; then
  fail "MemAvailable ${mem_gib} GiB < ${MIN_MEM_GIB} GiB"
elif lt "$mem_gib" "$WARN_MEM_GIB"; then
  warn "MemAvailable ${mem_gib} GiB < ${WARN_MEM_GIB} GiB: plan to shut the Win10 VM during lab sessions"
fi

# ZFS ARC (0 if ZFS is not loaded)
arc_bytes=$(awk '$1 == "size" { print $3 }' "$ARCSTATS_FILE" 2>/dev/null || true)
echo "ARC_SIZE_GIB=$(gib "${arc_bytes:-0}")"

# Guest RAM allocated, and VMID 900 collision
qemu_json=$("$PVESH" get "/nodes/$node/qemu" --output-format json)
lxc_json=$("$PVESH" get "/nodes/$node/lxc" --output-format json)
read -r alloc_bytes lab_vmid_taken < <(
  printf '%s\n%s\n' "$qemu_json" "$lxc_json" | python3 -c '
import json, sys
total, taken = 0, 0
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    for g in json.loads(line):
        total += int(g.get("maxmem", 0))
        if int(g.get("vmid", -1)) == '"$LAB_VMID"':
            taken = 1
print(total, taken)')
echo "GUEST_RAM_ALLOC_GIB=$(gib "$alloc_bytes")"
[ "$lab_vmid_taken" = 0 ] || fail "VMID $LAB_VMID already exists"

# local-lvm free space
lvm_bytes=$("$PVESH" get "/nodes/$node/storage/local-lvm/status" --output-format json |
  python3 -c 'import json, sys; print(int(json.load(sys.stdin)["avail"]))')
lvm_gib=$(gib "$lvm_bytes")
echo "LOCAL_LVM_FREE_GIB=$lvm_gib"
lt "$lvm_gib" "$MIN_LVM_GIB" && fail "local-lvm free ${lvm_gib} GiB < ${MIN_LVM_GIB} GiB"

for r in "${reasons[@]}"; do echo "REASON=$r"; done
echo "RESULT=$result"
[ "$result" != FAIL ]
