# Status

**Updated:** 2026-11-07
**Phase:** Phase 0 + Foundation — plan approved, implementation not started.
**Next:** Plan Task 1 (scaffold + read-only preflight). Execute the plan inline (owner's choice), then do one whole-branch review at the end.

## Progress

| Plan task | State | Commits | Notes |
|---|---|---|---|
| 1 Scaffold + preflight | not started | | |
| 2 Baseline + compare | not started | | |
| 3 VM 900 + pve-lab (F1) | not started | | owner runs on prod |
| 4 claude-ops CT + creds | not started | | |
| 5 Audit hook + settings | not started | | |
| 6 Remote Control (F2, F3, F6) | not started | | |
| 7 F4, F5, F7, F8 + go/no-go | not started | | then stop for owner review |

## Rulings

- **Repo location:** lab code lives in this repo under `lab/` (public), not in a `git init` of `C:\Coding\HomeSVR` as plan Task 1 Step 1 says. Servers fetch it as a tarball, which keeps the owner's PC out of the loop. *Cost if wrong:* moving files.
- **Plan version:** the owner's first local copy of the plan was stale (old F5 matching rule). The committed plan is the current version.

## Open decisions

- Phase 0 preflight's RAM/ARC reading decides whether 8 GB for the lab is safe, or whether the Win10 VM must be off during lab sessions.

## Owner decisions on record

- Test node: nested PVE VM 900 on prod, standalone (not clustered). Disks on `local-lvm`.
- Agent has full admin on pve-lab. Isolation comes from holding no prod credentials, with the lab on the LAN.
- Architecture: `claude-ops` LXC + Claude Code Remote Control server mode. Plan: Claude Pro. Host RAM 32 GB.
- T3 reuses the CT 102 vzdump. The owner runs the fault scripts.
- A review gate applies before each task test T1–T6.
