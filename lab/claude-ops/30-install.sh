#!/usr/bin/env bash
# Runs INSIDE the claude-ops CT as root. Installs tooling and Claude Code (as user `claude`).
# Idempotent. Holds no secrets and no production addresses.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git gh tmux jq curl python3 python3-pytest openssh-client ca-certificates

id claude >/dev/null 2>&1 || useradd -m -s /bin/bash claude

# Claude Code, native installer, as the unprivileged user.
su - claude -c 'command -v claude >/dev/null 2>&1 || [ -x ~/.local/bin/claude ] || { curl -fsSL https://claude.ai/install.sh | bash; }'
# shellcheck disable=SC2016  # $HOME must expand later, in claude's profile
su - claude -c 'grep -qs ".local/bin" ~/.profile || printf "\nexport PATH=\"\$HOME/.local/bin:\$PATH\"\n" >> ~/.profile'

# Workdir must be a git repo with a commit (Remote Control --spawn worktree needs one).
su - claude -c '
set -e
mkdir -p ~/lab ~/.ssh ~/.config/pve-lab
chmod 700 ~/.ssh ~/.config/pve-lab
cd ~/lab
[ -d .git ] || git init -q
git config user.name "claude-ops"
git config user.email "claude-ops@pve-lab.invalid"
git rev-parse --verify -q HEAD >/dev/null || git commit -q --allow-empty -m "init lab workdir"
'

su - claude -c 'claude --version'
echo "install done"
