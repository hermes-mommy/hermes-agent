# P0-002 SSH Hardening Summary

Date: 2026-05-31
Step: P0-002 SSH Config Update

## What changed on the VPS

- Repaired `/home/guinevere/.ssh/authorized_keys` with the correct Ed25519 public key.
- Ensured `/home/guinevere/.ssh` is mode `700` and owned by `guinevere:guinevere`.
- Ensured `/home/guinevere/.ssh/authorized_keys` is mode `600` and owned by `guinevere:guinevere`.
- Preserved existing key-only SSH hardening from `/etc/ssh/sshd_config.d/99-aizanta-hardening.conf`.
- Updated the existing `AllowUsers` directive from `root aizanta` to `root aizanta guinevere` so the new isolated Guinevere user can authenticate.
- Created rollback backup `/etc/ssh/sshd_config.d/99-aizanta-hardening.conf.pre-p0-002` before editing the SSH drop-in.
- Validated SSH syntax with `sshd -t` and reloaded the `ssh` service.

## What changed locally

- Added the `guinevere-vps` host alias to `C:\Users\faizz\.ssh\config`.
- Tightened `C:\Users\faizz\.ssh\config` ACLs after Windows OpenSSH rejected an inherited stale unknown SID.

## Why root SSH was not fully disabled in this step

P0-002 requires key-based Guinevere access and SSH hardening, but `guinevere` currently has limited sudo rights only for `guinevere-*` systemd services and journals. It cannot edit SSH configuration or reload the `ssh` service. Fully disabling root access here would remove the available break-glass rollback path before later hardening/VPN steps establish equivalent recovery access.

Current effective root behavior is `PermitRootLogin without-password` via `PermitRootLogin prohibit-password`: password root login is blocked, key-only break-glass root login remains available.

This is a deliberate safety tradeoff aligned with the no-lockout rule: security hardening must not strand the operator outside the VPS.

## Validation

- `ssh guinevere-vps "whoami && hostname"` returns `guinevere` and `faiz-prod-01`.
- `PasswordAuthentication no` and `KbdInteractiveAuthentication no` are effective for `guinevere`.
- `PubkeyAuthentication yes` is effective.
- `AllowUsers` includes `root`, `aizanta`, and `guinevere`.
- Aizanta containers and protected ports are unchanged.
