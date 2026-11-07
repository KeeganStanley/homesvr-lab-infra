# Status

**Updated:** 2026-11-07
**Phase:** Phase 0 + Foundation: all code written and unit-tested (80 pytest pass, shellcheck clean). Nothing has run on a server yet.
**Next (owner):** run the server-side steps below in order. Stop after F8 for go/no-go; T1-T6 each need separate approval.

## Progress

| Plan task | Code | Owner-run steps | Notes |
|---|---|---|---|
| 1 Scaffold + preflight | done | `00-preflight.sh` on prod; paste into `results/foundation.md`; stop on FAIL | |
| 2 Baseline + compare | done | `baseline.sh 10 before.csv` on prod (lab not yet created) | |
| 3 VM 900 + pve-lab (F1) | done | upload ISO; `01-create-vm900.sh`; install PVE; `10-post-install.sh`; `qm set 900 --delete ide2`; delete ISO; `baseline.sh 10 during.csv` + `compare_baseline.py` | the one prod change |
| 4 claude-ops CT + creds | done | `20-create-claude-ops.sh` on pve-lab, then `pct exec 100 -- bash /root/30-install.sh`; verify per plan step 3 | |
| 5 Audit hook + settings | done | `pct exec 100 -- bash <repo>/lab/claude-ops/40-deploy.sh`; one `claude -p` run; `tail -1` the log | |
| 6 Remote Control (F2, F3, F6) | done | `claude auth login`, trust prompts, push settings, trusted devices, `systemctl enable --now claude-rc`, then F2/F2b/F3/F6 from the phone | |
| 7 F4, F5, F7, F8 + go/no-go | done | F4 (`lab/tests/f4-cred-boundary.sh <prod_ip>` in CT, then `history -c` and delete), F5 (`f5-audit-check.sh <ts> 20` on pve-lab), F7, F8 | then stop for owner review |

Repo layout note: to run a script on a server, fetch the repo tarball (see `lab/README.md`); `20-` and `f5-` use sibling files, so run them from the extracted tree.

## Rulings

- **Repo location:** lab code lives in this repo under `lab/` (public), not in a `git init` of `C:\Coding\HomeSVR` as plan Task 1 Step 1 says. Servers fetch it as a tarball, which keeps the owner's PC out of the loop. *Cost if wrong:* moving files.
- **Plan version:** the owner's first local copy of the plan was stale (old F5 matching rule). The committed plan is the current version.

- **Classifier scope:** the audit hook tags more than the plan lists (`pvesh delete` destructive; `pvesh create/set`, `rm`, `mv`, `chmod`, `chown`, `kill`, `reboot`, `poweroff` change). Under-tagging is the unsafe direction for a draft prod policy. *Cost if wrong:* delete three regex lines.
- **Extra files:** `lab/claude-ops/40-deploy.sh` (installs hook, settings, rc-loop, service; does not enable the service) and `lab/tools/f5_match.py` (F5 matching logic, tested). Not in the plan.
- **F4 output:** never prints the prod IP, and ssh uses `UserKnownHostsFile=/dev/null`, so results can be pasted into this public repo.

## Open decisions

- The agent can edit its own `~/.claude/settings.json` (removing the audit hook) and write the audit log. A root-owned `/etc/claude-code/managed-settings.json` would prevent that. Plan and spec accept the weakness for the lab. Your call before T1.

- Phase 0 preflight's RAM/ARC reading decides whether 8 GB for the lab is safe, or whether the Win10 VM must be off during lab sessions.

## Owner decisions on record

- Test node: nested PVE VM 900 on prod, standalone (not clustered). Disks on `local-lvm`.
- Agent has full admin on pve-lab. Isolation comes from holding no prod credentials, with the lab on the LAN.
- Architecture: `claude-ops` LXC + Claude Code Remote Control server mode. Plan: Claude Pro. Host RAM 32 GB.
- T3 reuses the CT 102 vzdump. The owner runs the fault scripts.
- A review gate applies before each task test T1–T6.
