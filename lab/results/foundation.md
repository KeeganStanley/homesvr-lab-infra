# Foundation test results

`LAB_IP`: _(record at PVE install; it is a LAN address, so keep it out of this public repo; note only that it was recorded)_

## Preflight

Run on the production host, 2026-11-08 (read-only).

```
NESTED=Y
MEM_AVAILABLE_GIB=18.2
ARC_SIZE_GIB=3.1
GUEST_RAM_ALLOC_GIB=44.5
LOCAL_LVM_FREE_GIB=644.3
RESULT=PASS
```

Reading: nested virtualisation is on; 18.2 GiB is available (above the 12 GiB warn line, so no WARN); `local-lvm` has 644.3 GiB free (above the 600 expected, far above the 128 needed). `GUEST_RAM_ALLOC_GIB` is the sum of configured `maxmem` over all guests, running or not, so 44.5 exceeding the 32 GB host is overcommit, not usage. One snapshot only: free RAM is re-checked during F1 and the runtime rule (stop lab guests below 4 GiB free or growing swap) still applies.

## Tests

| Test | Date | Result | Evidence | Notes |
|---|---|---|---|---|
| F1 Nested check, VM 900, baseline delta < 5% | 2026-11-09 | **Accepted by owner**; strict rule not met | `compare_baseline.py before.csv during.csv`: `cpu_busy_delta_pp` 0.2, `iowait_delta_pp` -6.2, `swap_growth_kib` 1536, `pass` false | See F1 notes below |
| F2 Phone on mobile data runs `pveversion` | 2026-11-09 | PASS | Phone screenshot (status bar: 5G, no Wi-Fi): prompt "Run pveversion on pve-lab over ssh" returned `pve-manager/8.4.21`, kernel `6.8.12-43-pve`. Screenshot not stored in the repo | See F2 notes below |
| F2b Re-confirm after > 18 h | 2026-11-10 | PASS | Owner report: steering from the phone worked after the 18 h trusted-device re-confirm | |
| F3 Reboot + 15 min network cut recover < 5 min | 2026-11-09 | PASS | Owner report: after `pct reboot 100` the session answered from the phone almost immediately; after a 15 min `link_down` on CT 100 the existing sessions answered almost immediately once the link was restored | See F3 notes below |
| F4 Credential boundary | 2026-11-10 | PASS | `f4-cred-boundary.sh <prod_ip>` run in CT 100 as `claude`: PASS (a), (b), (c), (d) | See F4 notes below |
| F5 Audit: 20 mixed commands logged | 2026-11-10 | PASS | `f5-audit-check.sh <ts> 20` on pve-lab: `AUDIT_LINES=20`, `PVE_TASKS=8`, `RESULT=PASS`; the `pct destroy 199` record has `prod_tier: destructive` | See F5 notes below |
| F6 Push notifications | 2026-11-09 | PASS | Owner report: test A ("run sleep 120 then echo done, notify me when finished", app backgrounded) and test B ("use the AskUserQuestion tool to ask me to pick between blue and green") both delivered pushes | See F6 notes below |
| F7 Usage per task | | | | see table below |
| F8 Kill switch < 2 min | | | | |

## F1 notes

- Setup: VM 900 created to spec (`qm config` verified: `cpu host`, 4 cores, 8192 MB, `balloon 0`, `cpuunits 50`, `mbps_rd/wr 100`, `onboot 0`, 128G on `local-lvm`). PVE 8.4 installed, matching prod. `10-post-install.sh` run, kernel upgraded, rebooted. `pveam available` lists `debian-13-standard_13.6-1_amd64.tar.zst`. ISO detached and deleted from `local`. The lab's address and credentials are recorded outside this repo.
- `before.csv` (2026-11-08) is **not a valid baseline**: it shows 6-7% iowait at near-zero CPU, caused by a slow drive in a production pool that has since been removed. The -6.2 pp iowait delta therefore compares the lab against a degraded host and means nothing.
- Owner's own IO-delay monitoring shows the iowait figure during the lab (about 0%) is accurate.
- Swap: flat inside each run (40448 KiB before, 41984 KiB during); the 1536 KiB difference arose in the 31 h between the runs, which include VM 900's creation and install. `free -m` agrees (41 MiB swap used, 8 GiB swap, 15.6 GiB available with the lab running).
- Ruling (owner, 2026-11-09): accept F1 on this evidence, although the plan's strict "swap growth <= 0" and a valid before/after pair were not satisfied. No paired rerun was taken.
- `vmstat` on the prod host reports an identical `free` value on every row. That is `vmstat` itself, not `baseline.sh`; use `free -m` or `/proc/meminfo` for memory checks.

## F2 notes

- `claude remote-control` asked a one-time `Enable Remote Control? (y/n)` on first start under systemd/tmux; answered `y` in the pane (`tmux send-keys`). After `systemctl restart claude-rc` it came back with no prompt and the same environment URL (the answer persists, so `rc-loop` is not blocked).
- The environment appears in the Claude app as `claude-ops` (claude.ai: `lab · claude-ops`, apparently working folder and hostname; derivation not documented). `--name "HomeSVR Lab"` is passed (checked with `ps` in CT 100: one `claude remote-control --name HomeSVR Lab --spawn worktree --permission-mode bypassPermissions` process, `rc-loop.sh` identical to the repo copy), but the name does not appear in the claude.ai session list or the app; a session started from the phone is titled from its prompt. Cause unknown; treated as cosmetic. claude.ai/code shows the environment as `lab` (working folder `/home/claude/lab`) on device `claude-ops` (hostname). `rc-loop.log` does not exist until the first restart (it only logs after an exit).
- F2b (> 18 h re-confirm) not yet done.

## F5 notes

- The 20 calls came from a fixed prompt (8 reads, 10 changes, 2 destructive, one command per Bash call). Two reads (`pveversion`, `pvesm status`) exited 127: the agent ran them in the CT instead of over `ssh pve-lab` (the prompt only said to ssh the pct/qm/zfs ones). The hook logs before the command runs, so they still count, and they make no PVE task so they don't affect matching. The agent reported the failure instead of hiding it.
- PVE task log agrees with the audit log: create + 3 starts + 3 stops + destroy = 8 tasks, all matched. `AUDIT_LINES` was exactly the 20 minimum, with no slack.
- Only the `pct destroy` tier was spot-checked so far.

## F4 notes

- Positive control (accidental): the script was first run with the *lab's* address instead of prod's. It reported FAIL (a) ssh succeeded, FAIL (b) HTTP 200 instead of 401, FAIL (c) address found in 4 files (`~/.ssh/known_hosts`, `~/.ssh/known_hosts.old`, `~/.ssh/config`, and a Claude Code session transcript under `~/.claude/projects/`), PASS (d). So each check does detect access, and the run against prod is meaningful.
- Run against prod: all four PASS. The HTTP 401 in (b) shows the address was right and reachable, so the PASS in (a) is a real authentication refusal and not a typo or timeout.
- Claude Code keeps session transcripts under `~/.claude/projects/` containing every command and prompt; the prod address must therefore never be typed into a lab session. Check (c) scans `/home/claude`, so it would catch that.

## F3 notes

- During the outage new sessions never started and existing ones stopped answering; the phone app kept showing stale "connected" statuses, even after an app restart. A "connected" badge therefore does not prove the lab is reachable; a reply to a prompt does.
- `/home/claude/rc-loop.log` does not exist after either test. The log is only written after `claude remote-control` exits, so the process never exited during the 15 min outage (the docs describe a give-up after roughly 10 minutes offline; not seen here), and the reboot kills the whole tmux session rather than letting the loop log an exit. The `rc-loop.sh` restart-after-exit path has been unit-tested with a fake `claude` but has not been exercised on the real server. The plan expected a log entry; it did not occur.
- The network cut used `pct set 100 --net0 ...,hwaddr=<existing MAC>,link_down=1` (MAC preserved; the plan's command without `hwaddr` would have generated a new one).

## F6 notes

- First attempt (plain "ask me which of two options" prompt, sent while the 120 s sleep was still running) was a bad test: the agent had no options to offer and asked for them. Replaced by tests A and B above, run one at a time in separate sessions.
- Pushes initially did not arrive on Haiku sessions, with the app in the foreground and in the background. After switching to Sonnet they arrived, and they kept arriving after switching back to Haiku; a later Haiku test (question, phone unlocked, another app in front) also delivered. `/config` never showed "No mobile registered" at any point, so push registration is ruled out. Battery optimisation (set to unrestricted) and a `claude-rc` restart were done before the failures stopped and did not fix it alone. Cause not isolated. Open hypotheses: (1) push is discretionary for "Push when Claude decides", and for test B the agent must use its question tool, so a smaller model may sometimes skip it; (2) the docs say pushes are skipped while the user is "focused on the connected terminal", which the app showing the session in the foreground might count as. Neither confirmed.
- Reliability not yet measured: F6 is recorded as a pass on the results above. A suggested follow-up is three runs each of tests A and B on Haiku with the phone unlocked and another app in front.
- Both push toggles ("Push when actions required", "Push when Claude decides") are on in the CT's `/config`.

## Usage (F7)

| Task | Usage before % | Usage after % | Notes |
|---|---|---|---|
| F2–F6 | | | |
