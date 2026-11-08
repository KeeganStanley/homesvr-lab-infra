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
| F1 Nested check, VM 900, baseline delta < 5% | | | | |
| F2 Phone on mobile data runs `pveversion` | | | | |
| F2b Re-confirm after > 18 h | | | | |
| F3 Reboot + 15 min network cut recover < 5 min | | | | |
| F4 Credential boundary | | | | |
| F5 Audit: 20 mixed commands logged | | | | |
| F6 Push notifications | | | | |
| F7 Usage per task | | | | see table below |
| F8 Kill switch < 2 min | | | | |

## Usage (F7)

| Task | Usage before % | Usage after % | Notes |
|---|---|---|---|
| F2–F6 | | | |
