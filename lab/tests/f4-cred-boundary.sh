#!/usr/bin/env bash
# F4: credential boundary. Runs INSIDE the claude-ops CT as user `claude`.
# Usage: f4-cred-boundary.sh <prod_ip>
# The prod IP is an argument only: it is never written to disk by this script and never printed
# (the output is meant to be pasted into the public results file). Afterwards: `history -c`, delete this script.
# Prints one PASS/FAIL line per check (a)-(d), then details; exits 0 only if all four pass.
# SSH / CURL / SSH_DIR / TOKEN_FILE / GREP_DIRS overrides exist so it can be tested off-host.
set -euo pipefail

if [ $# -ne 1 ] || [ -z "$1" ]; then
  echo "usage: f4-cred-boundary.sh <prod_ip>" >&2
  exit 2
fi
prod_ip=$1
SSH=${SSH:-ssh}
CURL=${CURL:-curl}
SSH_DIR=${SSH_DIR:-$HOME/.ssh}
TOKEN_FILE=${TOKEN_FILE:-$HOME/.config/pve-lab/token}
read -r -a grep_dirs <<<"${GREP_DIRS:-/home/claude /etc /root}"

fails=0
details=()
check() { # check <label> <PASS|FAIL> <text>
  echo "$2 ($1) $3"
  [ "$2" = PASS ] || fails=$((fails + 1))
}

# (a) SSH to prod must fail. Host-key checking is off so the test reaches authentication, and
# known_hosts is /dev/null so the attempt leaves no copy of the IP behind.
if "$SSH" -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null "root@$prod_ip" true >/dev/null 2>&1; then
  check a FAIL "ssh root@prod succeeded"
else
  check a PASS "ssh root@prod refused"
fi

# (b) The lab API token must be rejected by prod's API with HTTP 401.
code=none
if [ -r "$TOKEN_FILE" ]; then
  code=$("$CURL" -sk -o /dev/null -w '%{http_code}' --max-time 10 \
    -H "Authorization: $(cat "$TOKEN_FILE")" "https://$prod_ip:8006/api2/json/nodes" || true)
fi
if [ "$code" = 401 ]; then
  check b PASS "prod API rejected the lab token (HTTP 401)"
else
  check b FAIL "expected HTTP 401 from prod API, got '$code'"
fi

# (c) The prod IP must not appear in any file the agent can read.
hits=$(grep -rIlF -- "$prod_ip" "${grep_dirs[@]}" 2>/dev/null || true)
if [ -z "$hits" ]; then
  check c PASS "prod IP not found under ${grep_dirs[*]}"
else
  check c FAIL "prod IP found in $(wc -l <<<"$hits") file(s)"
  details+=("files containing the prod IP:" "$hits")
fi

# (d) ~/.ssh holds only id_ed25519*, known_hosts* and config.
extra=$(find "$SSH_DIR" -mindepth 1 ! -type d ! -name 'id_ed25519*' ! -name 'known_hosts*' ! -name config 2>/dev/null || true)
if [ -z "$extra" ]; then
  check d PASS "no unexpected files in $SSH_DIR"
else
  check d FAIL "unexpected files in $SSH_DIR"
  details+=("unexpected ssh files:" "$extra")
fi

[ "${#details[@]}" -eq 0 ] || printf '%s\n' "${details[@]}"
[ "$fails" -eq 0 ]
