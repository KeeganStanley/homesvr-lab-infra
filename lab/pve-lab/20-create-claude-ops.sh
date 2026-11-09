#!/usr/bin/env bash
# Runs ON pve-lab (as root). Creates CT 100 "claude-ops" and gives it lab-only credentials:
#   - user `claude` in the CT, with an ed25519 key whose pubkey is added to pve-lab's root authorized_keys
#   - PVE API token claude@pve!ops (Administrator on /, privsep 0), stored in the CT at
#     /home/claude/.config/pve-lab/token (mode 0600) as `PVEAPIToken=claude@pve!ops=<secret>`
# The token secret is never printed and never appears in a command line.
# It also gives the agent a `Host pve-lab` ssh alias and pve-lab's host key (BatchMode ssh cannot
# answer an unknown-host prompt). LAB_IP is auto-detected from vmbr0; set it to override.
# Afterwards run: pct exec 100 -- bash /root/30-install.sh   (this script pushes it there).
# PCT / PVEAM / PVEUM / AUTH_KEYS / HOST_KEY_FILE overrides exist so the script can be exercised off-host.
set -euo pipefail

PCT=${PCT:-pct}
PVEAM=${PVEAM:-pveam}
PVEUM=${PVEUM:-pveum}
AUTH_KEYS=${AUTH_KEYS:-/root/.ssh/authorized_keys}
HOST_KEY_FILE=${HOST_KEY_FILE:-/etc/ssh/ssh_host_ed25519_key.pub}
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
INSTALL_SCRIPT=${INSTALL_SCRIPT:-$here/../claude-ops/30-install.sh}
ctid=100
token_user=claude@pve
token_name=ops

[ -f "$INSTALL_SCRIPT" ] || { echo "missing $INSTALL_SCRIPT" >&2; exit 1; }
if "$PCT" status "$ctid" >/dev/null 2>&1; then
  echo "CT $ctid already exists: refusing" >&2
  exit 1
fi
if "$PVEUM" user token list "$token_user" 2>/dev/null | grep -qw "$token_name"; then
  echo "token $token_user!$token_name already exists (its secret can't be re-read)." >&2
  echo "Remove it deliberately with: pveum user token remove $token_user $token_name" >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# No global umask: `pct create` of an unprivileged CT builds its rootfs dir under the caller's umask, and
# 077 makes it root-only so the container's mapped root cannot open it ("tar: .../rootfs: Permission denied").
# Secrets stay private because $tmp is a 0700 dir and the token file is created 0600 below.

echo "== template"
"$PVEAM" update
tmpl=$("$PVEAM" available --section system | awk '{ print $2 }' | grep '^debian-13-standard' | sort -V | tail -n 1)
[ -n "$tmpl" ] || { echo "no debian-13-standard template in pveam available" >&2; exit 1; }
"$PVEAM" list local | grep -qF "$tmpl" || "$PVEAM" download local "$tmpl"

echo "== creating CT $ctid from $tmpl"
"$PCT" create "$ctid" "local:vztmpl/$tmpl" \
  --hostname claude-ops \
  --unprivileged 1 \
  --features nesting=1 \
  --cores 2 \
  --memory 2048 \
  --swap 512 \
  --rootfs local-lvm:16 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --onboot 1
"$PCT" start "$ctid"

echo "== waiting for CT network"
for _ in $(seq 1 60); do
  "$PCT" exec "$ctid" -- getent hosts deb.debian.org >/dev/null 2>&1 && break
  sleep 2
done
"$PCT" exec "$ctid" -- getent hosts deb.debian.org >/dev/null || { echo "CT has no network/DNS" >&2; exit 1; }

echo "== user, ssh key"
"$PCT" exec "$ctid" -- bash -c 'id claude >/dev/null 2>&1 || useradd -m -s /bin/bash claude'
"$PCT" exec "$ctid" -- bash -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-client'
"$PCT" exec "$ctid" -- su - claude -c 'mkdir -p -m 700 ~/.ssh ~/.config/pve-lab && { [ -f ~/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N "" -C claude-ops -f ~/.ssh/id_ed25519; }'
pub=$("$PCT" exec "$ctid" -- cat /home/claude/.ssh/id_ed25519.pub)
mkdir -p "$(dirname "$AUTH_KEYS")"
touch "$AUTH_KEYS"
chmod 0600 "$AUTH_KEYS"
grep -qF -- "$pub" "$AUTH_KEYS" || printf '%s\n' "$pub" >> "$AUTH_KEYS"

echo "== ssh config + host key for pve-lab"
lab_ip=${LAB_IP:-$(ip -4 -o addr show vmbr0 2>/dev/null | awk '{ print $4 }' | cut -d/ -f1 | head -n 1)}
lab_ip=${lab_ip:-$(hostname -I | awk '{ print $1 }')}
[ -n "$lab_ip" ] || { echo "cannot determine pve-lab IP; set LAB_IP" >&2; exit 1; }
printf 'pve-lab,%s %s\n' "$lab_ip" "$(awk '{ print $1 " " $2 }' "$HOST_KEY_FILE")" > "$tmp/known_hosts"
printf 'Host pve-lab\n  HostName %s\n  User root\n' "$lab_ip" > "$tmp/ssh_config"
"$PCT" push "$ctid" "$tmp/known_hosts" /home/claude/.ssh/known_hosts --perms 0600
"$PCT" push "$ctid" "$tmp/ssh_config" /home/claude/.ssh/config --perms 0600
"$PCT" exec "$ctid" -- chown claude:claude /home/claude/.ssh/config /home/claude/.ssh/known_hosts

echo "== API token $token_user!$token_name"
"$PVEUM" user list | grep -qF "$token_user" || "$PVEUM" user add "$token_user" --comment "claude-ops lab agent"
"$PVEUM" acl modify / --users "$token_user" --roles Administrator
install -m 0600 /dev/null "$tmp/token"
"$PVEUM" user token add "$token_user" "$token_name" --privsep 0 --output-format json |
  python3 -c '
import json, sys
t = json.load(sys.stdin)
sys.stdout.write("PVEAPIToken=%s=%s\n" % (t["full-tokenid"], t["value"]))' > "$tmp/token"
grep -q '^PVEAPIToken=claude@pve!ops=.\+' "$tmp/token" || { echo "unexpected token output" >&2; exit 1; }
"$PCT" push "$ctid" "$tmp/token" /home/claude/.config/pve-lab/token --perms 0600
"$PCT" exec "$ctid" -- chown claude:claude /home/claude/.config/pve-lab/token
"$PCT" exec "$ctid" -- chmod 0600 /home/claude/.config/pve-lab/token

echo "== pushing installer"
"$PCT" push "$ctid" "$INSTALL_SCRIPT" /root/30-install.sh --perms 0700

echo "CT $ctid ready. Next: pct exec $ctid -- bash /root/30-install.sh"
