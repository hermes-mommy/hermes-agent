# P0-001 Summary

**Status:** Completed
**Date:** 2026-05-31

## What was done
- Created dedicated Linux user `guinevere`.
- Created `/home/guinevere` with ownership `guinevere:guinevere`.
- Locked password login for `guinevere`; P0-002 will configure key-based SSH.
- Added limited sudoers rule allowing only `guinevere-*` systemd service management and journal reads.
- Validated sudoers syntax with `visudo`.
- Verified Aizanta remained healthy after the action.

## Files changed on VPS
- `/etc/passwd` / `/etc/shadow` / `/etc/group` via `useradd`
- `/home/guinevere/`
- `/etc/sudoers.d/guinevere`

## Security boundary
The `guinevere` user does not have broad sudo. It can only manage `guinevere-*` services and read `guinevere-*` journals. It cannot manage Aizanta services.

## Rollback
```bash
sudo userdel -r guinevere
sudo rm -f /etc/sudoers.d/guinevere
```
