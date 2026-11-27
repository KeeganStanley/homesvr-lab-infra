#!/usr/bin/env bash
# Runs ON pve-lab (as root). Seeds the T2 (Proxmox Backup Server) test workloads:
#   CT 201 marker-01      files + SHA-256 manifest (the restore-integrity target)
#   CT 202 bindmount-01   same data on a host bind mount, mirroring prod CT 102's "no snapshot" case
# A copy of each manifest is kept on the host (SEED_DIR) so a restored CT can be checked against a record
# that predates the backup. The CTs are left running. Refuses if either CT ID already exists.
# PCT / PVEAM / CHOWN / MARKER_ID / BIND_ID / BIND_DIR / SEED_DIR overrides exist for tests and reruns.
set -euo pipefail

PCT=${PCT:-pct}
PVEAM=${PVEAM:-pveam}
CHOWN=${CHOWN:-chown}
MARKER_ID=${MARKER_ID:-201}
BIND_ID=${BIND_ID:-202}
BIND_DIR=${BIND_DIR:-/srv/t2-bind}
SEED_DIR=${SEED_DIR:-/root/t2-seed}
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
data_script=$here/seed-marker-data.sh
[ -f "$data_script" ] || { echo "missing $data_script" >&2; exit 1; }

for id in "$MARKER_ID" "$BIND_ID"; do
  if "$PCT" status "$id" >/dev/null 2>&1; then
    echo "CT $id already exists: refusing (nothing changed)" >&2
    exit 1
  fi
done

templates=$("$PVEAM" list local)
tmpl=$(awk '{ print $1 }' <<<"$templates" | sed -n 's|^local:vztmpl/||p' | grep '^debian-13-standard' | sort -V | tail -n 1 || true)
[ -n "$tmpl" ] || { echo "no debian-13-standard template in local storage (run: pveam download local <name>)" >&2; exit 1; }

mkdir -p "$BIND_DIR" "$SEED_DIR"
# Root inside an unprivileged CT is uid 100000 on the host; the bind-mounted directory must be theirs.
"$CHOWN" 100000:100000 "$BIND_DIR"

create() { # create <id> <hostname>
  "$PCT" create "$1" "local:vztmpl/$tmpl" \
    --hostname "$2" \
    --unprivileged 1 \
    --rootfs local-lvm:4 \
    --memory 256 \
    --swap 0 \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --onboot 0
}

echo "== creating CTs from $tmpl"
create "$MARKER_ID" marker-01
create "$BIND_ID" bindmount-01
"$PCT" set "$BIND_ID" -mp0 "$BIND_DIR,mp=/mnt/data"

echo "== starting"
for id in "$MARKER_ID" "$BIND_ID"; do
  "$PCT" start "$id"
  for _ in $(seq 1 30); do
    "$PCT" status "$id" | grep -q running && break
    sleep 1
  done
  "$PCT" status "$id" | grep -q running || { echo "CT $id did not start" >&2; exit 1; }
done

seed() { # seed <id> <target dir in CT> <host manifest name>
  "$PCT" push "$1" "$data_script" /root/seed-marker-data.sh --perms 0700
  "$PCT" exec "$1" -- bash /root/seed-marker-data.sh "$2"
  "$PCT" pull "$1" "$2/MANIFEST.sha256" "$SEED_DIR/$3.manifest.sha256"
  "$PCT" exec "$1" -- rm -f /root/seed-marker-data.sh
}

echo "== seeding data"
seed "$MARKER_ID" /srv/marker marker-01
seed "$BIND_ID" /mnt/data bindmount-01

echo "seeded: CT $MARKER_ID marker-01 (/srv/marker), CT $BIND_ID bindmount-01 (bind mount $BIND_DIR -> /mnt/data)"
echo "host-side manifests: $SEED_DIR/marker-01.manifest.sha256, $SEED_DIR/bindmount-01.manifest.sha256"
