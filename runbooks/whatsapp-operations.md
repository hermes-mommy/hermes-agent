# WhatsApp Operations Runbook

## 1. Initial QR Setup
1. Stop the service: `sudo systemctl stop guinevere-whatsapp`
2. Clear old auth state if needed: `rm -rf /opt/guinevere/.neonize_auth/*`
3. Start foreground test mode: `sudo -u guinevere /opt/guinevere/.venv/bin/python -m src.channels.whatsapp.service --qr-mode=terminal`
4. Scan the QR from WhatsApp > Linked Devices.
5. Wait for connected confirmation, stop foreground mode, then `sudo systemctl start guinevere-whatsapp`.
6. Verify with `sudo systemctl status guinevere-whatsapp`.

## 2. Session Recovery (Expired Session)
1. Check reconnect flag: `redis-cli -p 6380 --user guinevere_core GET guinevere:wa:reconnect:needs_manual`
2. Stop service: `sudo systemctl stop guinevere-whatsapp`
3. Clear auth state: `rm -rf /opt/guinevere/.neonize_auth/*`
4. Clear reconnect flag: `redis-cli -p 6380 --user guinevere_core DEL guinevere:wa:reconnect:needs_manual`
5. Re-pair using the QR setup procedure.

## 3. Protocol Break Recovery
1. Check Neonize release notes.
2. Upgrade: `uv pip install --upgrade neonize`.
3. Test: `sudo -u guinevere /opt/guinevere/.venv/bin/python -m src.channels.whatsapp.service --test-connect`.
4. If successful, restart the service. If not, rollback to the previous Neonize version and document the issue.

## 4. Ban Recovery
### Temporary ban
1. Do not reconnect during the ban window.
2. Set a manual flag to prevent churn.
3. After expiry, clear the flag and re-run the session recovery path.

### Permanent ban
1. Stop and disable the service.
2. Document the incident and appeal through WhatsApp support.
3. Only re-enable after a successful appeal and fresh pairing.

## 5. Phone Offline Handling
1. Keep the phone online at least once every 12 days.
2. Monitor `whatsapp_session_age_seconds`.
3. If the phone is replaced or unavailable long-term, expect session expiry and follow Session Recovery.
