# homesvr-lab-infra

Scripts, config and tests for the **HomeSVR agent-ops lab**: a nested Proxmox node (`pve-lab`, VM 900 on the production host) where Claude Code, driven from the owner's phone via Remote Control, is tested as a Proxmox administrator.

## Read before doing anything

1. `docs/STATUS.md`: where things stand, rulings made, what's next. **Update it and commit it whenever a task completes or a decision is made.** It's the shared memory between sessions.
2. `docs/superpowers/specs/2026-11-07-agent-ops-lab-design.md`: the design (binding authority).
3. `docs/superpowers/plans/2026-11-07-agent-ops-lab-phase0-foundation.md`: the current implementation plan.

## Hard rules

- **Production host:** the only allowed changes are creating VM 900 (`onboot=0`), adding disks to VM 900, and uploading/deleting the PVE ISO in `local`. Anything else touching production needs the owner's explicit approval first.
- **Never commit** production IPs, hostnames, passwords, API tokens, SSH keys or any other secret. Scripts take IPs and credentials as arguments or generate them on the box. This repo is **public**.
- **T3 fault-injection scripts never go in this repo**, in any branch or history. The lab agent can read this repo.
- The lab agent (`claude-ops`) must never get write access to this repo. A lab agent able to edit its own audit hook defeats the audit.
- `homesvr-lab-site` is a separate repo reserved for task T1 (the fake customer site). Don't put lab infrastructure there.
- **Review gate:** after foundation tests F1–F8, stop. Each task test T1–T6 needs the owner's separate review and approval before its session runs.

## Who runs what

Code is written and unit-tested here (pytest, shellcheck). Scripts **run on the servers**, executed by the owner. This session has no LAN access. Servers fetch the repo with:

```bash
curl -fsSL https://github.com/KeeganStanley/homesvr-lab-infra/archive/refs/heads/main.tar.gz | tar xz
```

## Layout

```
lab/phase0/     runs on the production host (read-only checks, baseline, create VM 900)
lab/pve-lab/    runs on the nested pve-lab host
lab/claude-ops/ runs inside the claude-ops agent container
lab/tools/      helpers + their tests
lab/tests/      foundation test scripts (F4, F5)
lab/results/    recorded test results
docs/           spec, plans, STATUS.md
```

## Conventions

- Bash: `set -euo pipefail`, must pass `shellcheck` cleanly. LF line endings (enforced by `.gitattributes`).
- Python: stdlib only unless the plan says otherwise; tests with `pytest`.
- Commit messages: `lab: <what>`.

## Working with the owner

- Be brief and precise. The owner's vocabulary is wide, so don't simplify.
- Don't flatter. Say plainly when something is wrong and why.
- Ask clarifying questions before long answers. Say "I don't know" when unsure.
- The owner often reads from a phone: put the decision or result first.
