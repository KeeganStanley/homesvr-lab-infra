# Agent-Ops Lab: Phase 0 + Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the nested `pve-lab` node and the `claude-ops` agent, reachable from the phone via Remote Control, and prove foundation tests F1–F8 so the task tests (T1–T6) can be reviewed one by one.

**Architecture:** One VM (900) on prod runs a standalone Proxmox VE. Inside it, an unprivileged Debian LXC `claude-ops` runs Claude Code in Remote Control server mode under tmux + systemd, as a non-root user. It has root SSH and an API token for pve-lab only, and a PreToolUse hook audits every tool call. All scripts live in `C:\Coding\HomeSVR\lab\`.

**Tech Stack:** Proxmox VE (current ISO), Debian 13 LXC template, Claude Code (native installer), bash, Python 3 + pytest (audit hook and baseline comparison only), tmux, systemd.

**Spec:** `docs/superpowers/specs/2026-11-07-agent-ops-lab-design.md`

**Who runs what:** prod and lab shell steps are run **by you** (prod web shell or SSH). I write the scripts and run the pytest suites on your PC's workspace. Once `claude-ops` is live, the F-tests run from your phone.

## Global Constraints

- Production changes are limited to: create VM 900 (`onboot=0`); add disks to VM 900; upload/delete the PVE ISO in `local`. Any other prod change → abort.
- VM 900: `cpu host`, 4 cores, 8192 MB, `balloon 0`, `cpuunits 50`, disk `local-lvm:128` with `mbps_rd=100,mbps_wr=100`, `net0 virtio,bridge=vmbr0`.
- Preflight aborts if `/sys/module/kvm_intel/parameters/nested` ≠ `Y` or `MemAvailable` < 8 GiB. It warns if < 12 GiB, in which case plan to shut the Win10 VM during lab sessions.
- Runtime rule: host free RAM < 4 GiB or growing swap while the lab runs → stop lab guests / Win10 VM.
- `claude-ops` never holds prod credentials (SSH keys, tokens, passwords, or the prod IP in any config).
- Claude Code runs as user `claude`, never root. Auth uses `claude auth login` (`setup-token` / `CLAUDE_CODE_OAUTH_TOKEN` can't do Remote Control).
- The audit hook must never block a tool call (always exits 0).
- No GitHub PAT or Proxmox MCP in this plan: they belong to T1 and to optional use later.

## Review Focus

1. **Prod host reboots** (power cut, kernel update): prod should come up normally and the lab should stay off. → Task 3 checks `onboot` is 0.
2. **Audit log not writable** (disk full, permissions): Claude should keep working and the hook should log nothing. → Task 5 `test_main_returns_0_when_log_unwritable`.
3. **Malformed or unexpected hook input** (non-Bash tools, junk JSON): it should never crash or block. → Task 5 `test_main_returns_0_on_malformed_json`, `test_unknown_tool_is_change`.
4. **Remote Control exits after a network outage**: the session should come back on its own. → Task 6 F3.
5. **Phone sign-in ages out (trusted device, ~18 h)**: after a Face ID re-confirm the session should be steerable again. → Task 6 F2b.

---

### Task 1: Repo scaffold + read-only preflight

**Files:**
- Create: `lab/README.md` (one paragraph + link to spec), `lab/phase0/00-preflight.sh`, `lab/results/foundation.md`

**Interfaces:**
- Produces: `00-preflight.sh` → prints `KEY=value` lines (`NESTED`, `MEM_AVAILABLE_GIB`, `ARC_SIZE_GIB`, `GUEST_RAM_ALLOC_GIB`, `LOCAL_LVM_FREE_GIB`) then `RESULT=PASS|WARN|FAIL`. Exit code 0/0/1.
- Produces: `lab/results/foundation.md`, a table with rows F1–F8, columns `Date | Result | Evidence | Notes`, plus a "Usage (F7)" table `Task | Usage before % | after % | Notes`.

- [ ] **Step 1:** `git init` in `C:\Coding\HomeSVR`; `.gitignore` excludes `lab/secrets/`, `lab/faults/`, `*.csv`.
- [ ] **Step 2:** Write `00-preflight.sh`. It is read-only: `cat`, `/proc/meminfo`, `/proc/spl/kstat/zfs/arcstats` (`size`), `pvesh get /nodes/$(hostname)/qemu` and `/lxc` (sum `maxmem`), and `pvesh get /nodes/$(hostname)/storage/local-lvm/status` (`avail`). It must also fail if VMID 900 already exists. `set -euo pipefail`; it changes nothing.
- [ ] **Step 3:** `shellcheck lab/phase0/00-preflight.sh` → no warnings.
- [ ] **Step 4 (you, prod):** `bash 00-preflight.sh | tee` → expected `NESTED=Y`, `LOCAL_LVM_FREE_GIB` ≥ 600, `RESULT=PASS` or `WARN`. Paste the output into `results/foundation.md` under "Preflight". **On FAIL, stop.**
- [ ] **Step 5:** Commit `lab: scaffold + preflight`.

### Task 2: Baseline capture + comparison (supports F1)

**Files:**
- Create: `lab/phase0/baseline.sh`, `lab/tools/compare_baseline.py`, `lab/tools/tests/test_compare_baseline.py`

**Interfaces:**
- Produces: `baseline.sh <minutes> <out.csv>` samples `vmstat 60` and writes CSV header `ts,us,sy,id,wa,free_kib,swpd_kib`.
- Produces: `compare_baseline(before: list[dict], after: list[dict]) -> dict` returning `{"cpu_busy_delta_pp": float, "iowait_delta_pp": float, "swap_growth_kib": int, "pass": bool}`. Pass = both deltas < 5.0 and swap growth ≤ 0. CLI: `python compare_baseline.py before.csv after.csv` prints JSON; exit 0 on pass, 1 on fail.

- [ ] **Step 1: Failing tests:** `test_identical_runs_pass` (delta 0 → pass); `test_cpu_delta_5pp_fails` (before us+sy=10, after 15.0 → fail); `test_iowait_4pp_passes`; `test_swap_growth_fails` (swpd 0 → 1024).
- [ ] **Step 2:** `pytest lab/tools/tests -q` → 4 failures (module missing).
- [ ] **Step 3:** Implement `compare_baseline` (mean of `us+sy` and `wa` per file) and `baseline.sh`.
- [ ] **Step 4:** `pytest lab/tools/tests -q` → 4 passed; `shellcheck lab/phase0/baseline.sh` clean.
- [ ] **Step 5 (you, prod):** `bash baseline.sh 10 before.csv` (lab not yet created).
- [ ] **Step 6:** Commit `lab: baseline capture + compare`.

### Task 3: Create VM 900 and install pve-lab (the one prod change) — F1

**Files:**
- Create: `lab/phase0/01-create-vm900.sh`, `lab/pve-lab/10-post-install.sh`

**Interfaces:**
- Consumes: `00-preflight.sh` (must exit 0 first; the create script runs it itself).
- Produces: `01-create-vm900.sh <iso_volid>` (e.g. `local:iso/proxmox-ve_9.x.iso`) → VM 900 with the Global Constraints values plus `name pve-lab`, `ostype l26`, `scsihw virtio-scsi-single`, `scsi0 ...,iothread=1,discard=on`, `onboot 0`, `boot order=scsi0;ide2`. It refuses if 900 exists.
- Produces: pve-lab host reachable at a static LAN IP (you choose it at install; record it as `LAB_IP` in `results/foundation.md`) with hostname `pve-lab`.

- [ ] **Step 1:** Write both scripts. `10-post-install.sh` (runs on pve-lab): disable the enterprise repos, add the no-subscription repo, `apt update && apt -y full-upgrade`, `pveam update`. `shellcheck` both → clean.
- [ ] **Step 2 (you, prod):** Upload the PVE ISO to `local` (web UI). Run `bash 01-create-vm900.sh local:iso/<file>.iso`.
- [ ] **Step 3 (you, prod):** Verify `qm config 900`. It must show `cpu: host`, `memory: 8192`, `balloon: 0`, `cpuunits: 50`, `mbps_rd=100`, `mbps_wr=100`, `onboot: 0`. Any mismatch → `qm destroy 900` and fix the script.
- [ ] **Step 4 (you):** Install PVE via the VM 900 console (static IP, hostname `pve-lab`, ext4 or ZFS-single on the 128 GB disk). Then `bash 10-post-install.sh` on pve-lab, and `qm set 900 --delete ide2` on prod. Delete the ISO from `local`.
- [ ] **Step 5 (you): F1.** Wait until pve-lab is idle. Run `bash baseline.sh 10 during.csv` on prod, then `python compare_baseline.py before.csv during.csv` → `"pass": true`. Record in F1.
- [ ] **Step 6:** Commit `lab: VM 900 + pve-lab install`.

### Task 4: `claude-ops` container + tooling + lab credentials

**Files:**
- Create: `lab/pve-lab/20-create-claude-ops.sh`, `lab/claude-ops/30-install.sh`

**Interfaces:**
- Produces: CT 100 `claude-ops` on pve-lab: unprivileged, `features nesting=1`, 2 cores, 2048 MB, swap 512, `rootfs local-lvm:16`, `net0 name=eth0,bridge=vmbr0,ip=dhcp`, `onboot 1`. Template = newest `debian-13-standard` from `pveam available`.
- Produces in CT 100: user `claude`; packages `git gh tmux jq curl python3 python3-pytest openssh-client`; Claude Code installed with `curl -fsSL https://claude.ai/install.sh | bash` as `claude`. Workdir `/home/claude/lab` (a git repo, needed for `--spawn worktree`). SSH key `/home/claude/.ssh/id_ed25519` (no passphrase); its pubkey appended to pve-lab `/root/.ssh/authorized_keys`. PVE token `claude@pve!ops` (Administrator on `/`, `--privsep 0`) stored at `/home/claude/.config/pve-lab/token` mode 0600, format `PVEAPIToken=claude@pve!ops=<secret>`.

- [ ] **Step 1:** Write both scripts (`20-` runs on pve-lab and creates the CT, user, `pveum` token and authorized_keys entry; `30-` runs inside the CT). `shellcheck` → clean.
- [ ] **Step 2 (you, pve-lab):** Run `20-create-claude-ops.sh`, then `pct exec 100 -- bash /root/30-install.sh` (after `pct push`).
- [ ] **Step 3: Verify:** `pct exec 100 -- su - claude -c 'ssh -o BatchMode=yes root@<LAB_IP> pveversion'` prints the PVE version. `su - claude -c 'curl -sk -H "Authorization: $(cat ~/.config/pve-lab/token)" https://<LAB_IP>:8006/api2/json/version'` returns JSON with `"version"`. `su - claude -c 'claude --version'` prints a version.
- [ ] **Step 4:** Commit `lab: claude-ops container + lab-only creds`.

### Task 5: Audit hook (TDD) + Claude Code settings — supports F5

**Files:**
- Create: `lab/claude-ops/audit_hook.py`, `lab/claude-ops/tests/test_audit_hook.py`, `lab/claude-ops/settings.json`

**Interfaces:**
- Produces: `classify(tool_name: str, tool_input: dict) -> str` returning `"read" | "change" | "destructive"`.
  - Bash, destructive if the command matches any of: `rm -r`/`rm -rf`, `pct destroy`, `qm destroy`, `zfs destroy`, `zpool (destroy|detach|offline|labelclear)`, `mkfs`, `wipefs`, `dd `, `pvesm remove`.
  - Bash, change if it matches: `(pct|qm) (set|start|stop|shutdown|reboot|create|restore|resize)`, `systemctl (start|stop|restart|enable|disable)`, `apt(-get)? (install|remove|purge|upgrade|full-upgrade)`, `git (push|commit|merge|reset)`, `zfs (set|create|snapshot|rollback)`, `sed -i`, output redirection `>`/`>>` or `tee` to a path.
  - Everything else in Bash is read.
  - `Edit`/`Write`/`NotebookEdit` → change. `Read`/`Grep`/`Glob`/`WebSearch`/`WebFetch` → read. Any other tool → change.
- Produces: `build_record(payload: dict, now: datetime) -> dict` with keys `ts` (ISO-8601 UTC), `session_id`, `tool`, `input`, `prod_tier`.
- Produces: `main(stdin_text: str, log_path: str) -> int` appends one JSON line and **always returns 0**. Installed as `/usr/local/bin/claude-audit-hook` (reads stdin, logs to `/var/log/claude-audit/audit.jsonl`, owned by `claude`).
- Produces: `settings.json` → `/home/claude/.claude/settings.json`: `permissions.defaultMode = "bypassPermissions"`; `hooks.PreToolUse = [{"matcher": "*", "hooks": [{"type": "command", "command": "/usr/local/bin/claude-audit-hook"}]}]`.
- Note: the classifier is advisory. Its job is to draft a prod approval policy from real usage, not to enforce anything.

- [ ] **Step 1: Failing tests:**
  - `test_classify_read`: `pveversion`, `pct list`, `zpool status -v`, `journalctl -u jellyfin -n 50` → read.
  - `test_classify_change`: `pct set 101 -memory 512`, `systemctl restart jellyfin`, `apt install -y jq`, `git push origin feature/x`, `echo x > /etc/foo` → change.
  - `test_classify_destructive`: `pct destroy 105`, `zfs destroy tank/media`, `rm -rf /var/lib/x`, `zpool detach tank sdb` → destructive.
  - `test_edit_tool_is_change`; `test_unknown_tool_is_change` (`"mcp__x__y"`).
  - `test_main_appends_jsonl`: 2 calls → 2 lines, each with all 5 keys.
  - `test_main_returns_0_on_malformed_json`: `"{not json"` → 0, nothing written.
  - `test_main_returns_0_when_log_unwritable`: log path in a read-only dir → 0.
- [ ] **Step 2:** `pytest lab/claude-ops/tests -q` → all fail.
- [ ] **Step 3:** Implement `audit_hook.py` (stdlib only) and `settings.json`.
- [ ] **Step 4:** `pytest lab/claude-ops/tests -q` → all pass.
- [ ] **Step 5 (you):** Deploy to CT 100 (hook to `/usr/local/bin`, mode 0755; log dir; `settings.json`). Run `su - claude -c 'claude -p "run: pveversion via ssh root@<LAB_IP>"'` once, then `tail -1 /var/log/claude-audit/audit.jsonl` → a record with `"tool": "Bash"`, `"prod_tier": "read"`.
- [ ] **Step 6:** Commit `lab: audit hook + claude settings`.

### Task 6: Remote Control service, phone pairing, push — F2, F3, F6

**Files:**
- Create: `lab/claude-ops/rc-loop.sh`, `lab/claude-ops/claude-rc.service`

**Interfaces:**
- Produces: `rc-loop.sh` loops forever: `cd /home/claude/lab && claude remote-control --name "HomeSVR Lab" --spawn worktree --permission-mode bypassPermissions`, then `sleep 30` after any exit, logging the exit code with a timestamp to `/home/claude/rc-loop.log`.
- Produces: `claude-rc.service` (`User=claude`, `Type=forking`, `ExecStart=/usr/bin/tmux new-session -d -s rc /home/claude/rc-loop.sh`, `ExecStop=/usr/bin/tmux kill-session -t rc`, `Restart=always`, `RestartSec=30`, enabled).

- [ ] **Step 1:** Write both; `shellcheck rc-loop.sh` → clean.
- [ ] **Step 2 (you, interactive in CT 100 as `claude`):**
  1. Run `claude auth login`; open the URL on your phone and approve.
  2. In `/home/claude/lab`, run `claude` once and accept workspace trust plus the bypass-permissions confirmation.
  3. In `/config`, enable **Push when actions required** and **Push when Claude decides**.
  4. Exit.
- [ ] **Step 3 (you, phone):** Turn on **Require trusted devices** (claude.ai → Account). Make sure the Claude app has notification permission.
- [ ] **Step 4 (you):** Install and enable the service. `systemctl status claude-rc` → active. `tmux capture-pane -pt rc` shows a session URL.
- [ ] **Step 5: F2.** Phone on **mobile data** (Wi-Fi off) → Claude app → Code → "HomeSVR Lab" → prompt "run pveversion on pve-lab over ssh". Pass = version returned. **F2b:** repeat after > 18 h; pass = works after a Face ID / passkey confirm.
- [ ] **Step 6: F3.** Run `pct reboot 100`; pass = session reachable from the phone within 5 min of boot. Then on pve-lab run `pct set 100 --net0 name=eth0,bridge=vmbr0,ip=dhcp,link_down=1`, wait 15 min, and set it back without `link_down`. Pass = reachable within 5 min. `rc-loop.log` should show the exit and restart.
- [ ] **Step 7: F6.** From the phone: "sleep 120 then echo done, notify me when finished", then "ask me which of two options to pick before continuing". Pass = both pushes arrive.
- [ ] **Step 8:** Record F2, F2b, F3 and F6 in `results/foundation.md`. Commit `lab: remote control service`.

### Task 7: Boundary, audit, usage and kill-switch tests — F4, F5, F7, F8

**Files:**
- Create: `lab/tests/f4-cred-boundary.sh`, `lab/tests/f5-audit-check.sh`

**Interfaces:**
- Consumes: `PROD_IP` passed as an argument at run time only. It is never written into CT 100.
- Produces: `f4-cred-boundary.sh <prod_ip>` (runs in CT 100 as `claude`) checks four things and prints `PASS`/`FAIL` for each, exiting 0 only if all pass:
  - (a) `ssh -o BatchMode=yes -o ConnectTimeout=5 root@<prod_ip> true` fails;
  - (b) `curl -sk -H "Authorization: $(cat token)" https://<prod_ip>:8006/api2/json/nodes` returns HTTP 401;
  - (c) `grep -rIl <prod_ip>` over `/home/claude`, `/etc` and `/root` finds nothing outside this script's own run;
  - (d) no file under `~/.ssh` other than `id_ed25519*`, `known_hosts*` and `config`.
- Produces: `f5-audit-check.sh <since_iso_ts> <min_count>` (runs on pve-lab) counts audit lines in CT 100 since the timestamp (`pct exec`) and lists pve-lab tasks since then (`pvesh get /nodes/pve-lab/tasks --since <epoch>`). It prints `AUDIT_LINES=`, `PVE_TASKS=` and `RESULT=PASS` if audit lines ≥ min_count and every `pct`/`qm` `create|start|stop|shutdown|destroy` in the audit log has a matching PVE task. `pct set` is excluded because it doesn't produce a task entry.

- [ ] **Step 1:** Write both; `shellcheck` → clean.
- [ ] **Step 2: F4 (you, CT 100):** `bash f4-cred-boundary.sh <prod_ip>` → 4× PASS. Delete the script afterwards so the IP doesn't linger in history: `history -c`, `rm`.
- [ ] **Step 3: F5 (phone):** Note the time, then send a prompt asking Claude to run 20 mixed commands. Include 5 reads, 5 changes (start/stop a throwaway CT 199 it creates) and 2 destructive (`pct destroy 199`). Then on pve-lab: `bash f5-audit-check.sh <ts> 20` → `RESULT=PASS`. Spot-check that `prod_tier` matches expectations for the destroy lines.
- [ ] **Step 4: F7:** Record the claude.ai usage % before and after F2–F6 in the Usage table, and do the same for every later task session.
- [ ] **Step 5: F8:** At home on Wi-Fi, use the phone browser → prod web UI → VM 900 → **Stop**. Time it from unlock to "stopped": pass < 2 min. Confirm the phone shows the session offline. Restart VM 900. Also check that removing the phone from Trusted Devices blocks steering, then re-enrol.
- [ ] **Step 6: Go/no-go:** Fill in `results/foundation.md` and run `compare_baseline.py before.csv during.csv` once more with the lab under F5 load. Summarise and present the results to you, **then stop**: each task test (T1–T6) needs your separate approval.
- [ ] **Step 7:** Commit `lab: foundation tests complete`.
