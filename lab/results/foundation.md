# Foundation test results

`LAB_IP`: _(record at PVE install; it is a LAN address, so keep it out of this public repo; note only that it was recorded)_

## Preflight

_Paste `00-preflight.sh` output here (strip nothing sensitive: it prints no IPs)._

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
