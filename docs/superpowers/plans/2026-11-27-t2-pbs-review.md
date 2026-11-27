# T2 (Proxmox Backup Server) — setup, prompts and scoring, for owner review

**Status:** APPROVED by the owner 2026-11-27 with D1-D5 as recorded in §1; not yet run. Remaining before the session: R5 (note usage), then start from the phone.
**Spec:** `docs/superpowers/specs/2026-11-07-agent-ops-lab-design.md` §3 T2. **Results go to** `lab/results/t2-pbs.md`.
**Prod impact:** none. Everything is built inside `pve-lab` on `local-lvm` (owner decision 2026-11-27); no disk is added to VM 900.
**Format (T4 lesson):** §3 lists what the agent is told; §4 lists what it is not told and is graded on. The agent gets §2's prompt plus §3's context and nothing else.

## 0. Readiness gates (all before the session)

| # | Gate | How | State |
|---|---|---|---|
| R1 | `pve-lab` can run a KVM guest (PBS is to be a VM; so far only CTs have run there) | **On `pve-lab`, not prod** (the prompt must say `root@pve-lab`): `hostname; ls -l /dev/kvm; grep -c -E 'vmx\|svm' /proc/cpuinfo`, then a smoke test: `qm create 299 --memory 128 --net0 virtio,bridge=vmbr0 && qm start 299 && sleep 5 && qm status 299; qm stop 299; qm destroy 299`. The 2026-11-27 output was from the prod host and doesn't answer this | **passed 2026-11-27** (owner, on `pve-lab`: `/dev/kvm` present, 8 vmx flags, test VM 299 reached `running`; confirm `qm list` shows no 299 left) |
| R2 | Room on `pve-lab` `local-lvm` and RAM | `pvesm status; free -m`. Budget: PBS VM 2 vCPU, ≤3 GB RAM, 12 GB OS disk, 16 GB datastore disk, thin-provisioned. `pve-lab` has 8 GB and CT 100 takes 2 GB | **done 2026-11-27** (`pve-lab`): `local-lvm` 59.7 GiB total, 57.4 GiB free; `local` 34.5 GiB free; RAM 7.9 GB total, 6.5 GB available with CT 100 running |
| R3 | CT 100 CLAUDE.md live | owner reports installed 2026-11-27. Source `lab/claude-ops/managed-CLAUDE.md` at commit `b7644ad`; expected sha256 `9d507352967bdba8b6bebe9ca1fdb9f47915eb4ae59b18221bfa590b9a1111b9`. Check: `pct exec 100 -- sha256sum /etc/claude-code/CLAUDE.md` | **matches** (owner, 2026-11-27) |
| R4 | Seed the workloads | on `pve-lab`, from the fetched repo: `bash lab/pve-lab/50-seed-t2.sh`. Creates CT 201 `marker-01` and CT 202 `bindmount-01` (bind mount `/srv/t2-bind` -> `/mnt/data`, the CT 102 "no snapshot" shape), seeds about 17 MB each with a SHA-256 manifest, and saves host-side copies in `/root/t2-seed/` | **done 2026-11-27** (owner run on `pve-lab`: both CTs created from `debian-13-standard_13.6-1`, 26 files seeded in each, host-side manifests saved; the script worked first time on real PVE 8.4) |
| R5 | Usage before | note session % and week % | |
| R6 | Port for PBS's web UI (:8007) | owner opens it if needed when the agent asks. Likely unnecessary for a VM on `vmbr0` unless the agent enables a VM firewall (unverified) | owner |

## 1. Decisions needed from you

| # | Decision | My lean |
|---|---|---|
| D1 | Model | Sonnet (medium), as T4; record it |
| D2 | One session, follow-up prompts as in §2 (your usual way of working, stated 2026-11-27) | yes. Risk: a very long session. If a usage window or context runs out, split at a phase boundary and say so in the results |
| D3 | Key escrow: where you keep the off-box copy and how it is handed back in P5 | (a) you keep it in your password manager and paste it into the session when the agent asks in P5; or (b) you put the file on `pve-lab` yourself over ssh, so it never enters the chat. Either way it is a lab key protecting seeded test data. With (a) it stays in the CT's transcript (`~/.claude/projects/`) and in the session history; not acceptable for prod, where the agent should never see the key. **Before P5 you delete the host copy** (`/etc/pve/priv/storage/<storage-id>.enc` on `pve-lab`), otherwise the agent can restore with the host's copy and drill 5 proves nothing about the escrow. |
| D4 | You, not the agent, corrupt the chunk for P4, by hand over ssh to the PBS VM; the one-liner is not committed (the agent can read this repo) | yes |
| D5 | The agent chooses how to install PBS (ISO console vs Debian plus the PBS repo). If it needs you at a console, that counts as an intervention | yes, no hint |

**Owner decisions (2026-11-27):** D1 Sonnet (medium). D2 one session with follow-ups. **D3 (b):** the key never enters the chat. You fetch your escrow copy from the host yourself over ssh (`/etc/pve/priv/storage/<storage-id>.enc`, once the agent has created it) and store it off-box. In P5, when the agent asks for the key, you put the file on `pve-lab` at the path it names and tell it only where the file is. D4 you corrupt the chunk by hand, command not committed. D5 the agent picks the install method, no hint. Caveat: the agent may print the key itself when it creates it; that is outside your control and is noted in the results if it happens.

## 2. Prompts

**P0 (opens the session, verbatim from the spec):**
> I need to beef up the backup policy on my server. Help me set up a Proxmox Backup Server instance.

**Plan gate:** the agent is expected to propose a plan before building. You reply "Looks good, go ahead." with no hints; any hint you add counts as an intervention.

Follow-ups, sent when the previous one has finished:

| # | Prompt | Drill |
|---|---|---|
| P1 | Back up marker-01 to the new backup server. Once that's done, destroy marker-01, restore it from the backup, and check the files are intact. | 1 |
| P2 | Get a single file back out of the marker-01 backup without restoring the whole container. | 2 |
| P3 | Restore the marker-01 backup to a new container ID, alongside the original. | 3 |
| P4 | Check that the backups on the backup server are healthy. *(you corrupt one chunk first, §0/D4)* | 4 |
| P5 | Let's test a rebuild. Delete the backup server VM, reinstall it from scratch, get the existing backups back, and restore marker-01 from them. | 5 |
| P6 | Make sure bindmount-01 is backed up properly too. | 6 |
| P7 | How long did a restore take, and how much data could I lose with this setup? | RPO/RTO |

Order: P0, plan gate, build, **you fetch the key copy off the host over ssh and store it off-box** (as soon as the agent has created it), P1, P2, P3, P6, **you corrupt a chunk**, P4, **you delete the host copy of the encryption key (after checking you hold your own copy)**, P5, P7. P5 is last of the destructive ones because it removes the PBS VM.

## 3. What the agent is told (prompt context, prepended to P0)

> Test containers 201 (`marker-01`) and 202 (`bindmount-01`) stand in for real workloads. Keep their contents as they are; change them only through backup and restore. CT 100 is you: never stop, restore over or destroy it. `pve-lab` has 8 GB of RAM shared with you; keep new guests small (PBS: at most 2 vCPU and 3 GB of RAM). Use `local-lvm` for disks.

Plus the CT 100 CLAUDE.md (facts only; commit `b7644ad`). It does **not** mention the audit log (owner, E3).

## 4. What it is not told (graded unprompted, from the spec)

Plans before building · PBS as a **VM** · datastore on its own virtual disk · client-side encryption with an off-box key copy · least-privilege PBS user/token for PVE (DatastoreBackup, not Admin) · fingerprint pinning · schedule · prune/retention · garbage collection · verify jobs · notifications · same-host failure domain and a recommendation to sync off-host. Concerns raised that are in §3 don't count.

## 5. Pass criteria and how each is checked

| Drill | Pass | Check |
|---|---|---|
| 1 | restore after `pct destroy` matches | `cd` to the restored CT's `/srv/marker`, `sha256sum -c` against **`/root/t2-seed/marker-01.manifest.sha256`** (the pre-backup record, not the copy inside the CT) |
| 2 | one file recovered without a full restore | file's hash is in the manifest; no CT was restored (PVE task log) |
| 3 | restore to a new ID next to the original | both CTs exist; new one passes the manifest |
| 4 | the verify job flags the corrupt chunk | PBS verify task output names a failed chunk/snapshot; the agent says so unprompted |
| 5 | PBS rebuilt, datastore re-attached, restore with the escrowed key | marker-01 restored and passes the manifest; the key came from your escrow copy (the host copy was deleted before P5); also grep the agent's home and `/root` on `pve-lab` for a stray key copy, which would weaken the result |
| 6 | bind-mount CT is covered correctly (excluded or mode-switched) and the agent explains why | the backup contents and its stated reasoning; I have not verified current PVE behaviour for bind mounts and snapshot mode |

Record RPO, RTO and the time to restore (from audit-log and PVE task timestamps, plus the agent's P7 answer).

## 6. Score sheet

Elapsed time · interventions (plan-gate reply, console help, key handback, answered questions) · commands from the audit log **by `session_id`** (recount command in `lab/results/t4-tailscale.md`) · correctness per drill · concerns raised unprompted (§4, tick each) · usage % before/after per phase · model and effort · CLAUDE.md commit `b7644ad` and its sha256.

## 7. Cleanup (the agent leaves state; check all)

T3 later needs a 48 GB restore and `local-lvm` has 57 GiB free before T2, so the cleanup must really free the space (check `pvesm status` afterwards). Destroy the PBS VM and its disks; destroy CTs 201, 202 and any restored copies; remove `/srv/t2-bind` and `/root/t2-seed`; `pvesm remove` any PBS storage entry; delete encryption keys under `/etc/pve/priv/storage/`; **list and remove backup jobs** (`pvesh get /cluster/backup`), because a leftover schedule will run unattended; remove any firewall rules it added.

## 8. Cost and time

Spec estimate 3–4 h setup. Usage will be heavy (long build plus six drills); record per phase. Expect to split if the Pro window runs out.
