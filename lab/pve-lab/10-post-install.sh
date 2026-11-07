#!/usr/bin/env bash
# Runs ON pve-lab after install: disable enterprise repos, enable no-subscription, upgrade.
# Idempotent. ETC_APT_DIR / OS_RELEASE_FILE / APT_GET / PVEAM overrides exist for off-host tests.
set -euo pipefail

apt_dir=${ETC_APT_DIR:-/etc/apt}
os_release=${OS_RELEASE_FILE:-/etc/os-release}
APT_GET=${APT_GET:-apt-get}
PVEAM=${PVEAM:-pveam}

# shellcheck source=/dev/null
codename=$(. "$os_release" && echo "${VERSION_CODENAME:?no VERSION_CODENAME}")
src_dir=$apt_dir/sources.list.d
mkdir -p "$src_dir"

# Disable enterprise repos (both the legacy .list and the deb822 .sources forms).
for f in "$src_dir"/pve-enterprise.list "$src_dir"/ceph.list; do
  [ -f "$f" ] && sed -i 's/^deb /# deb /' "$f"
done
for f in "$src_dir"/pve-enterprise.sources "$src_dir"/ceph.sources; do
  [ -f "$f" ] || continue
  grep -q '^Enabled:' "$f" && sed -i 's/^Enabled:.*/Enabled: no/' "$f" || printf 'Enabled: no\n' >> "$f"
done

# Enable the no-subscription repo.
if [ "$codename" = bookworm ]; then
  printf 'deb http://download.proxmox.com/debian/pve %s pve-no-subscription\n' "$codename" \
    > "$src_dir/pve-no-subscription.list"
else
  cat > "$src_dir/pve-no-subscription.sources" <<SRC
Types: deb
URIs: http://download.proxmox.com/debian/pve
Suites: $codename
Components: pve-no-subscription
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
SRC
fi

"$APT_GET" update
DEBIAN_FRONTEND=noninteractive "$APT_GET" -y full-upgrade
"$PVEAM" update
echo "post-install done ($codename)"
