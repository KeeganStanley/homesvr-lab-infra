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
| F2b Re-confirm after > 18 h | | | | |
| F3 Reboot + 15 min network cut recover < 5 min | | | | |
| F4 Credential boundary | | | | |
| F5 Audit: 20 mixed commands logged | | | | |
| F6 Push notifications | | | | |
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
- The environment appears in the Claude app as `claude-ops` (claude.ai: `lab · claude-ops`, apparently working folder and hostname; derivation not documented). `--name "HomeSVR Lab"` did not show on a session started from the phone: that session was titled from the prompt. Per the Remote Control docs, `--name` sets the session title, and `--create-session-in-dir` (on by default) pre-creates one session at server start, which is probably the one that carries the name. Not yet confirmed. The session list should be checked for a pre-created "HomeSVR Lab" session.
- F2b (> 18 h re-confirm) not yet done.

## Usage (F7)

| Task | Usage before % | Usage after % | Notes |
|---|---|---|---|
| F2–F6 | | | |
