# Lab scripts

Scripts and tests for the HomeSVR agent-ops lab: a nested Proxmox node (`pve-lab`, VM 900 on the production host) administered by Claude Code over Remote Control. Design: [`docs/superpowers/specs/2026-11-07-agent-ops-lab-design.md`](../docs/superpowers/specs/2026-11-07-agent-ops-lab-design.md). Plan: [`docs/superpowers/plans/2026-11-07-agent-ops-lab-phase0-foundation.md`](../docs/superpowers/plans/2026-11-07-agent-ops-lab-phase0-foundation.md). Status: [`docs/STATUS.md`](../docs/STATUS.md).

This repo is public: scripts take IPs and credentials as arguments or generate them on the box. Never commit either.

Fetch on a server:

```bash
curl -fsSL https://github.com/KeeganStanley/homesvr-lab-infra/archive/refs/heads/main.tar.gz | tar xz
```
