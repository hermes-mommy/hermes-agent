# P0-002 Summary

**Status:** Completed
**Date:** 2026-05-31

## What was done

- Enabled key-based SSH login for the dedicated `guinevere` Linux user.
- Added the local Windows OpenSSH alias `guinevere-vps` pointing to the VPS Tailscale IP `100.94.104.22` as user `guinevere`.
- Repaired local SSH config ACLs so Windows OpenSSH accepts `C:\Users\faizz\.ssh\config`.
- Preserved existing SSH password hardening and added `guinevere` to the existing `AllowUsers` list.
- Kept key-only root break-glass access available because `guinevere` cannot yet reload or repair SSH configuration.
- Verified Aizanta containers and protected ports remained unchanged after the SSH changes.

## Files changed locally

- `C:\Users\faizz\.ssh\config` — added `Host guinevere-vps` and repaired ACLs.
- `docs/setup-evidence/P0/STEP-P0-002/ssh-test.log`
- `docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt`
- `docs/setup-evidence/P0/STEP-P0-002/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-002/ssh-hardening-summary.md`
- `docs/setup-evidence/P0/STEP-P0-002/p0-002-summary.md`
- `docs/setup-evidence/P0/STEP-P0-002/verification.md`

## Files changed on VPS

- `/home/guinevere/.ssh/authorized_keys` — replaced malformed content with the correct Ed25519 public key.
- `/etc/ssh/sshd_config.d/99-aizanta-hardening.conf` — updated `AllowUsers root aizanta` to `AllowUsers root aizanta guinevere`.
- `/etc/ssh/sshd_config.d/99-aizanta-hardening.conf.pre-p0-002` — rollback backup created before SSH drop-in edit.

## Security boundary

Password login remains disabled. Keyboard-interactive login remains disabled. Public-key login is enabled. Root password login remains disabled; root key-only break-glass access is intentionally preserved until later recovery/VPN hardening steps provide an equivalent rollback path.

## Rollback

1. Keep the existing root SSH session/access open.
2. Restore the SSH drop-in backup:

```bash
sudo cp -a /etc/ssh/sshd_config.d/99-aizanta-hardening.conf.pre-p0-002 /etc/ssh/sshd_config.d/99-aizanta-hardening.conf
sudo sshd -t
sudo systemctl reload ssh
```

3. Remove the local alias block from `C:\Users\faizz\.ssh\config` if needed.
4. Only remove `/home/guinevere/.ssh/authorized_keys` if another valid Guinevere access path exists.
