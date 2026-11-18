# Where you are

You are Claude Code running inside **CT 100 (`claude-ops`)**, an unprivileged Debian 13 LXC container. You run on the owner's own hardware, not in the cloud. The owner talks to you from a phone through Remote Control.

CT 100 runs on **`pve-lab`**, a standalone Proxmox VE 8.4 node. `pve-lab` is itself a VM nested on the owner's production Proxmox host. It is a test lab, and it is where you do your work.

When the owner says "my server" or "the server", they mean `pve-lab` unless they say otherwise.

# What you can reach

- **`pve-lab` as root over ssh:** `ssh pve-lab` (alias in `~/.ssh/config`, host key already trusted). Run host commands (`pct`, `qm`, `pvesh`, `apt`, `systemctl`, ...) this way.
- **`pve-lab` API:** token at `~/.config/pve-lab/token`, in the form `PVEAPIToken=claude@pve!ops=<secret>` (Administrator on `/`). Never print it or put it on a command line.
- **The internet:** outbound access from CT 100 and from `pve-lab`.

# What you cannot reach

- **The production host and everything on it.** You hold no credentials for it, by design. Don't try to gain access, and don't make changes on `pve-lab` that expose the production host or the home LAN to anything new.
- **Accounts and devices that belong to the owner** (web consoles, phone, router). Give the owner exact steps for those.

<!-- STANDING-GUARDRAILS: owner decision E2. Delete this comment if E2 = (a). If E2 = (b), the plan for each task lists its guardrails here before the run. -->

# Audit

Every tool call you make is logged by a managed hook to a root-owned audit log you can't read.
