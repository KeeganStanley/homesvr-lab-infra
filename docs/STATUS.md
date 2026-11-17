# Status

**Updated:** 2026-11-17
**Phase:** Phase 0 + Foundation complete: F1-F8 recorded in `lab/results/foundation.md` (F1 and the loaded-lab baseline accepted by the owner, F7 partial). Review gate reached.
**Next (owner):** run the approved T4 (Tailscale) session from the phone; record results. T1-T3, T5, T6 still each need separate review and approval before their sessions run.

## Progress

| Plan task | Code | Owner-run steps | Notes |
|---|---|---|---|
| 1 Scaffold + preflight | done; **preflight run 2026-11-08: PASS** | none left | |
| 2 Baseline + compare | done | `baseline.sh 10 before.csv` on prod (lab not yet created) | |
| 3 VM 900 + pve-lab (F1) | done; **VM 900 + PVE 8.4 installed, F1 accepted by owner 2026-11-09** (see ruling) | upload ISO; `01-create-vm900.sh`; install PVE; `10-post-install.sh`; `qm set 900 --delete ide2`; delete ISO; `baseline.sh 10 during.csv` + `compare_baseline.py` | the one prod change |
| 4 claude-ops CT + creds | done; **run on pve-lab 2026-11-09, all three verification checks passed** (CT 100 created from the Debian 13 template on PVE 8.4; ssh, API token and `claude --version` all work). An early run failed on a `umask 077` bug in `20-`, fixed | `20-create-claude-ops.sh` on pve-lab, then `pct exec 100 -- bash /root/30-install.sh`; verify per plan step 3. The script also gives the agent a `Host pve-lab` ssh alias and pve-lab's host key (BatchMode ssh failed without them) | |
| 5 Audit hook + settings | done; **deployed and live check passed 2026-11-09** (Claude Code 2.1.321 in CT 100: one `claude -p` ssh `pveversion` call wrote exactly one record, `tool: Bash`, `prod_tier: read`). `/hooks` does NOT list the managed hook, but it fires; use the log as the check | `pct exec 100 -- bash <repo>/lab/claude-ops/40-deploy.sh`; one `claude -p` run; `tail -1` the log **as root** (the log is `root:claude 0620`: the agent can append, not read) | |
| 6 Remote Control (F2, F3, F6) | done; **service enabled, F2, F3 and F6 passed 2026-11-09, F2b passed 2026-11-10** ( `rc-loop` restart path not exercised live, see results; F6 pushes initially failed on Haiku, then worked; registration ruled out, cause not isolated, reliability not measured, see results; the `--name` flag is passed but the UI doesn't show it: cosmetic, closed) | **swap plan steps 2 and 3:** turn on Require trusted devices first, then `claude auth login` (or re-run it after), then trust prompts, push settings, `systemctl enable --now claude-rc`, then F2/F2b/F3/F6 from the phone | |
| 7 F4, F5, F7, F8 + go/no-go | done; **done 2026-11-17: F4, F5, F8 passed; F7 partial; loaded-lab baseline accepted by owner (CPU +2.6 pp, iowait +0.2 pp, swap +256 KiB); go/no-go summary written, stopped at the review gate** | F4 (`lab/tests/f4-cred-boundary.sh <prod_ip>` in CT, then `history -c` and delete), F5 (`f5-audit-check.sh <ts> 20` on pve-lab), F7, F8 | then stop for owner review |

Repo layout note: to run a script on a server, fetch the repo tarball (see `lab/README.md`); `20-` and `f5-` use sibling files, so run them from the extracted tree.

## Rulings

- **Repo location:** lab code lives in this repo under `lab/` (public), not in a `git init` of `C:\Coding\HomeSVR` as plan Task 1 Step 1 says. Servers fetch it as a tarball, which keeps the owner's PC out of the loop. *Cost if wrong:* moving files.
- **Plan version:** the owner's first local copy of the plan was stale (old F5 matching rule). The committed plan is the current version.

- **Classifier scope:** the audit hook tags more than the plan lists (`pvesh delete` destructive; `pvesh create/set`, `rm`, `mv`, `chmod`, `chown`, `kill`, `reboot`, `poweroff` change). Under-tagging is the unsafe direction for a draft prod policy. The review widened it further (`lvremove`, `pvesm free`, `pct/qm rollback`, `zpool create/replace`, `curl -X DELETE/POST`, `find -delete`, `git clean`, options before subcommands such as `apt-get -y install` and `git -C x push`, interpreters with `-c/-e`). It is regex-based and advisory: anything unrecognised still reads as `read`, so spot-check `read` lines before drafting a prod policy. *Cost if wrong:* revert `audit_hook.py` patterns.
- **Extra files:** `lab/claude-ops/40-deploy.sh` (installs hook, settings, rc-loop, service; does not enable the service) and `lab/tools/f5_match.py` (F5 matching logic, tested). Not in the plan.
- **Managed settings (owner decision, 2026-11-08):** the audit hook is registered in root-owned `/etc/claude-code/managed-settings.json` (`40-deploy.sh` installs it); the user `settings.json` only sets `bypassPermissions` (the hook is kept out of it so there is one source of truth). Docs confirm (code.claude.com managed-settings and hooks pages, per the reviewer): the Linux path is `/etc/claude-code/managed-settings.json`, hook entries merge across scopes, and user settings cannot disable managed hooks. Tamper hardening: the installed hook has a fixed log path (no env override), the log directory is root-owned, and the log is `root:claude 0620` (append, no read; `claude` can still truncate it). *Limit:* the agent has root SSH on pve-lab, and root there can `pct exec`/`pct push` into CT 100 as root, so this stops accidents and prompt-level edits, not a deliberate bypass. *Not confirmed from docs:* that PreToolUse hooks fire in `bypassPermissions` mode (expected). *To verify on the box:* `/hooks` lists the managed hook, and `claude -p` writes one log line per call.
- **F4 output:** never prints the prod IP, and ssh uses `UserKnownHostsFile=/dev/null`, so results can be pasted into this public repo.

- **F1 accepted by owner (2026-11-09):** `compare_baseline.py` returned `pass: false` on swap (+1536 KiB). Swap was flat inside each run; the growth arose in the 31 h between runs. The `before.csv` baseline was invalid (a slow drive in a prod pool inflated iowait; since removed), and the owner's own IO-delay monitoring shows the lab's iowait is about 0. No paired rerun was done. *Cost if wrong:* F1 was never measured on a clean before/after pair; a rerun needs the lab off for the `before` half.
- **Subscription popup (owner request, 2026-11-09):** `lab/pve-lab/15-remove-nag.sh` (optional, lab only) patches `proxmoxlib.js` via `lab/tools/patch_nag.py` and installs an apt hook that re-applies it after upgrades. It refuses to run unless the host is named `pve-lab`. The dialog pattern comes from the community patch and was *not* verified against a real PVE 8.4 file (git.proxmox.com is not reachable from this session); it fails closed (exit 1, nothing changed) if the pattern isn't found. Revert: remove `/etc/apt/apt.conf.d/99-pve-nag-patch`, then `apt-get install --reinstall proxmox-widget-toolkit`.
- **PVE version:** the lab runs PVE 8.4 (ISO `proxmox-ve_8.4-1`) to match prod, which also runs 8.4. Debian 13 container template is available (`debian-13-standard_13.6-1`); whether PVE 8.4 can start it is untested until Task 4.

- **Swap tolerance (owner decision, 2026-11-17):** `compare_baseline.py` passes swap growth up to 4096 KiB instead of requiring <= 0 (override with `--swap-tolerance-kib N`). Two clean runs showed harmless +1536 KiB and +256 KiB; real memory pressure is tens of MiB or more. The plan's "<= 0" is superseded. *Cost if wrong:* edit `DEFAULT_SWAP_TOLERANCE_KIB`.
- **Prod and tooling (owner, 2026-11-17):** prod stability is good enough to proceed with the tests; `tmux` is installed on prod and safe to use in runbooks; the owner can push files into the lab if needed. Push reliability and F7 usage are monitored by the owner through T1-T6.

## Incident, 2026-11-09 (closed for this repo)

- The prod host hung and was rebooted. Afterwards some CTs failed to start and the media drive's filesystem needed `xfs_repair`. Both were host-side problems, fixed by the owner outside this repo.
- The hang's cause is not established (the logs were lost). Nothing found implicates VM 900 (stopped for that boot) or this repo's scripts: their only prod writes are `qm create 900` and the baseline CSV (checked by grep).
- `tmux` was installed on prod by the owner at the time. Runbooks must not assume extra packages on prod.
- Tasks 5 and 6 are no longer on hold. VM 900 is stopped (`onboot=0`): run `qm start 900` on prod before continuing Task 5.

- **T4 draft (2026-11-17):** `docs/superpowers/plans/2026-11-17-t4-tailscale-review.md`. Owner decided D1-D5 on 2026-11-17: Tailscale on the host, tag the phone, interactive login, PC untagged as the denied device, Sonnet (medium) with Haiku subagents allowed. Key expiry on tagged devices is now verified from the Tailscale docs: off by default, can be re-enabled per device in the admin console, so tags stay. The CT `/dev/net/tun` point is moot (D1-a). Owner setup done: account with MFA, phone app installed (pending device approval), device approval on, ACL reviewed. **T4 session approved by the owner 2026-11-17.** Usage before: 9% session, 3% week.

## Open decisions

- (none open from the hook/settings review; see rulings)

## Known minor issues (reviewer, deferred)

- `vmstat` on the prod host shows a constant `free` column (not a `baseline.sh` bug; unused by the pass rule). Use `free -m` for memory checks.

- `baseline.sh`: `ts` is local time with a `Z` suffix (wrong if prod isn't on UTC).
- `20-create-claude-ops.sh`: if no `debian-13-standard` template exists the script exits silently (`pipefail` + `grep`); `pveam list | grep -q` can SIGPIPE.
- `40-deploy.sh` re-run overwrites `~/.claude/settings.json`, which can undo `/config` push settings from Task 6. Deploy once, before `/config`.
- F4 (a) passes on any ssh failure (timeout, typo, no route), not only auth failure; (c) doesn't scan `/var/log` or `/tmp` and uses substring matching.
- F5 counts failed commands (e.g. "CT 199 already running") as UNMATCHED.
- Hook records over ~4 KB (large `Write` inputs) could interleave across concurrent sessions.
- `rc-loop.sh` keeps running `claude` in the wrong directory if `cd` fails. `rc-loop.sh` and the service stay `claude`-owned (they cannot switch off the managed hook).
- `30-install.sh` omits `uv` (spec lists it; plan's package list doesn't).
- Reviewer could not verify on real hardware: `pvesh`/`pveum`/`pveam` output formats, `pct push` ownership in an unprivileged CT, task-log entries per `pct`/`qm` command, `Type=forking` tmux under the CT's systemd, procps 4 `vmstat` columns.

- **RAM (resolved on one reading, 2026-11-08):** preflight shows 18.2 GiB available (no WARN), ARC 3.1 GiB. On that reading 8 GB for the lab is safe with the Win10 VM left on. It is a single snapshot: re-check free RAM and swap during F1, and keep the runtime rule (stop lab guests below 4 GiB free or growing swap). Owner may overrule.

## Owner decisions on record

- Test node: nested PVE VM 900 on prod, standalone (not clustered). Disks on `local-lvm`.
- Agent has full admin on pve-lab. Isolation comes from holding no prod credentials, with the lab on the LAN.
- Architecture: `claude-ops` LXC + Claude Code Remote Control server mode. Plan: Claude Pro. Host RAM 32 GB.
- T3 reuses the CT 102 vzdump. The owner runs the fault scripts.
- A review gate applies before each task test T1–T6.
