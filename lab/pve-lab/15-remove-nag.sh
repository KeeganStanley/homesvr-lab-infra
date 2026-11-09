#!/usr/bin/env bash
# Runs ON pve-lab (lab only). Removes the "No valid subscription" login popup from the web UI and
# installs an apt hook that re-applies the patch after package upgrades overwrite proxmoxlib.js.
# Refuses to run on any host not named pve-lab: it edits a PVE system file, and prod must not be touched.
# Revert: rm /etc/apt/apt.conf.d/99-pve-nag-patch && apt-get install --reinstall proxmox-widget-toolkit
# Reload the web UI with a hard refresh (Ctrl+F5) afterwards.
# DEST_ROOT / PROXMOXLIB_JS / HOSTNAME_OVERRIDE overrides exist so the script can be tested off-host.
set -euo pipefail

host=${HOSTNAME_OVERRIDE:-$(hostname -s)}
if [ "$host" != pve-lab ]; then
  echo "refusing: this host is '$host', not 'pve-lab' (lab only; never run on production)" >&2
  exit 1
fi

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=${DEST_ROOT:-}
js=${PROXMOXLIB_JS:-/usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js}

# Patch first: if the dialog code isn't recognised, install nothing.
python3 "$here/../tools/patch_nag.py" "$js"

install -D -m 0755 "$here/../tools/patch_nag.py" "$root/usr/local/sbin/pve-nag-patch"
install -d -m 0755 "$root/etc/apt/apt.conf.d"
cat > "$root/etc/apt/apt.conf.d/99-pve-nag-patch" <<'CONF'
// Re-apply the lab-only subscription popup patch after dpkg runs. Must never break apt.
DPkg::Post-Invoke { "if [ -x /usr/local/sbin/pve-nag-patch ]; then /usr/local/sbin/pve-nag-patch --quiet || true; fi"; };
CONF
chmod 0644 "$root/etc/apt/apt.conf.d/99-pve-nag-patch"
echo "nag removed; hard-refresh the web UI (Ctrl+F5)"
