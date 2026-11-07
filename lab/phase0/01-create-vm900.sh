#!/usr/bin/env bash
# Create VM 900 "pve-lab" on the production host. This is the one production change.
# Usage: 01-create-vm900.sh <iso_volid>     e.g. local:iso/proxmox-ve_9.0-1.iso
# Runs 00-preflight.sh first and refuses unless it exits 0. Refuses if VMID 900 exists.
# QM / PVESM / PREFLIGHT overrides exist so the script can be exercised off-host.
set -euo pipefail

if [ $# -ne 1 ] || ! [[ $1 =~ ^[A-Za-z0-9_-]+:iso/[A-Za-z0-9._+-]+\.iso$ ]]; then
  echo "usage: 01-create-vm900.sh <storage:iso/file.iso>" >&2
  exit 2
fi
iso=$1
QM=${QM:-qm}
PVESM=${PVESM:-pvesm}
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PREFLIGHT=${PREFLIGHT:-$here/00-preflight.sh}
vmid=900

echo "== preflight"
bash "$PREFLIGHT" || { echo "preflight failed: not creating VM $vmid" >&2; exit 1; }

"$PVESM" path "$iso" >/dev/null || { echo "ISO not found: $iso" >&2; exit 1; }
if "$QM" status "$vmid" >/dev/null 2>&1; then
  echo "VM $vmid already exists: refusing" >&2
  exit 1
fi

echo "== creating VM $vmid"
"$QM" create "$vmid" \
  --name pve-lab \
  --ostype l26 \
  --cpu host \
  --cores 4 \
  --memory 8192 \
  --balloon 0 \
  --cpuunits 50 \
  --scsihw virtio-scsi-single \
  --scsi0 local-lvm:128,iothread=1,discard=on,mbps_rd=100,mbps_wr=100 \
  --net0 virtio,bridge=vmbr0 \
  --ide2 "$iso,media=cdrom" \
  --boot 'order=scsi0;ide2' \
  --onboot 0

echo "== verifying config"
cfg=$("$QM" config "$vmid")
echo "$cfg"
ok=1
for want in 'cpu: host' 'memory: 8192' 'balloon: 0' 'cpuunits: 50' 'mbps_rd=100' 'mbps_wr=100' 'onboot: 0'; do
  grep -qF -- "$want" <<<"$cfg" || { echo "MISMATCH: missing '$want'" >&2; ok=0; }
done
if [ "$ok" != 1 ]; then
  echo "Config mismatch: run 'qm destroy $vmid' and fix this script." >&2
  exit 1
fi
echo "VM $vmid created. Next: install PVE from the console (hostname pve-lab, static IP)."
