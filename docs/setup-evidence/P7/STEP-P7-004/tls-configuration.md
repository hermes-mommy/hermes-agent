# TLS Configuration Guide: Surveillance Webhook Endpoint

> **Task**: P7-004
> **Scope**: TLS/SSL setup for the surveillance webhook endpoint (`POST /surveillance/events`)
> **Last Updated**: 2026-06-02

## 1. Overview

The Guinevere Core API listens on port 8000 and accepts surveillance event data from external sources, primarily an Android device running Tasker. That internal port must never face the public internet directly. Instead, TLS termination happens at one of two layers before traffic reaches the API:

| Access Method | URL Pattern | TLS Provider | Best For |
|---|---|---|---|
| Cloudflare Tunnel | `https://surveillance.<your-domain>` | Cloudflare edge certificates | Public internet access from any device |
| Tailscale HTTPS | `https://<hostname>.<tailnet>.ts.net` | Let's Encrypt via Tailscale | Private mesh access between enrolled devices |

Both options give you valid, automatically renewed TLS certificates with zero manual certificate management. The API itself only ever sees plain HTTP on localhost. The encryption boundary sits at the edge (Cloudflare) or the Tailscale node.

### When to Use Which

Pick **Cloudflare Tunnel** when the Android device might connect from arbitrary networks (mobile data, public WiFi, friend's house). The tunnel gives you a stable public URL with Cloudflare's DDoS protection on top.

Pick **Tailscale HTTPS** when both the VPS and Android device are enrolled in the same tailnet. This keeps all traffic on a private mesh with no public surface at all. You can run both simultaneously. They don't conflict.

## 2. Network Architecture

```
                          +---------------------------+
                          |     CLOUDFLARE EDGE       |
                          |  (TLS termination, WAF)   |
                          +-------------+-------------+
                                        |
                  HTTPS                 |  HTTP (tunnel)
                  :443                  |  :8000
                                        |
    +------------+        +-------------+-------------+        +------------+
    |  Android   | -----> |        VPS HOST           | -----> | Guinevere  |
    |  (Tasker)  | HTTPS  |                           | :8000  | Core API   |
    +------------+        |  +---------------------+  |        | (localhost)|
         |                |  |  cloudflared        |  |        +------------+
         |                |  |  (tunnel daemon)    |  |
         |                |  +---------------------+  |
         |                |                           |
         |                |  +---------------------+  |
         +--------------->|  |  Tailscale          |  |
           Tailscale      |  |  (HTTPS servfail)   |  |
           HTTPS :443     |  +---------------------+  |
                          +---------------------------+
```

### Traffic Flow

**Cloudflare Tunnel path:**

1. Android Tasker sends `POST https://surveillance.<your-domain>/surveillance/events`
2. Cloudflare edge terminates TLS, validates the certificate, applies WAF rules.
3. `cloudflared` on the VPS receives the request over the tunnel (encrypted by Cloudflare's tunnel protocol, not raw TLS).
4. `cloudflared` forwards to `http://localhost:8000/surveillance/events` as plain HTTP.
5. The API validates the HMAC-SHA256 signature in the request header.

**Tailscale HTTPS path:**

1. Android Tasker sends `POST https://<hostname>.<tailnet>.ts.net/surveillance/events`
2. Tailscale on the VPS terminates TLS using a Let's Encrypt certificate.
3. The request reaches the API on `http://localhost:8000` as plain HTTP.
4. The API validates the HMAC-SHA256 signature.

In both cases, port 8000 never binds to a public interface. It listens on `127.0.0.1:8000` or `0.0.0.0:8000` behind a firewall that blocks inbound 8000 from all external sources.

## 3. Cloudflare Tunnel Setup

### 3.1 Prerequisites

- A Cloudflare account with a domain added and DNS managed by Cloudflare
- `cloudflared` installed on the VPS
- The Guinevere API running on port 8000

### 3.2 Install cloudflared

```bash
# Debian/Ubuntu
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared

# Verify
cloudflared --version
```

### 3.3 Authenticate

```bash
cloudflared tunnel login
```

This opens a browser. Select the domain you want to use. A certificate file gets saved to `~/.cloudflared/cert.pem`.

### 3.4 Create a Tunnel

```bash
cloudflared tunnel create guinevere-surveillance
```

Note the tunnel UUID this command prints. You'll need it for DNS and the config file.

### 3.5 Configure the Tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /home/<user>/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: surveillance.<your-domain>
    service: http://localhost:8000
    originRequest:
      noTLSVerify: false
  - service: http_status:404
```

The `service: http_status:404` catch-all at the end is required. Without it, cloudflared rejects the config.

### 3.6 Set Up DNS

```bash
cloudflared tunnel route dns guinevere-surveillance surveillance.<your-domain>
```

This creates a CNAME record pointing `surveillance.<your-domain>` to `<TUNNEL_UUID>.cfargotunnel.com`.

### 3.7 Start the Tunnel

```bash
# Test run first
cloudflared tunnel run guinevere-surveillance

# Install as a system service
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### 3.8 Cloudflare SSL/TLS Settings

In the Cloudflare dashboard, navigate to **SSL/TLS** for your domain:

- Set encryption mode to **Full (strict)**. This ensures Cloudflare validates origin certificates when connecting to your server. Since the tunnel handles transport internally, this setting mainly affects Cloudflare's edge behavior.
- Enable **Always Use HTTPS**.
- Enable **Automatic HTTPS Rewrites**.
- Set **Minimum TLS Version** to **TLS 1.2**.

### 3.9 Verify

```bash
# From any external machine
curl -v https://surveillance.<your-domain>/health

# Check the certificate
echo | openssl s_client -connect surveillance.<your-domain>:443 -servername surveillance.<your-domain> 2>/dev/null | openssl x509 -noout -dates
```

You should see a valid Cloudflare-issued certificate with future expiry dates.

## 4. Tailscale HTTPS Configuration

### 4.1 Prerequisites

- Tailscale installed and authenticated on the VPS
- Tailscale installed and authenticated on the Android device
- MagicDNS enabled in the Tailscale admin console

### 4.2 Enable HTTPS Certificates

In the Tailscale admin console:

1. Go to **DNS** settings.
2. Enable **MagicDNS** if not already active.
3. Under **HTTPS Certificates**, click **Enable HTTPS**.

Tailscale will now automatically provision Let's Encrypt certificates for any node in your tailnet that requests one.

### 4.3 Configure Tailscale Serve

Tailscale Serve lets you expose a local service over HTTPS on your tailnet.

```bash
# Expose port 8000 over Tailscale HTTPS
tailscale serve https / http://localhost:8000

# Verify the serve config
tailscale serve status
```

This makes the API available at `https://<hostname>.<tailnet>.ts.net/`. All paths, including `/surveillance/events`, are forwarded automatically.

### 4.4 Persist the Serve Configuration

Tailscale Serve config survives restarts in recent versions (1.36+). Verify with:

```bash
tailscale serve status
```

If the config doesn't persist on your version, add it to a startup script:

```bash
# /etc/systemd/system/tailscale-serve.service
[Unit]
Description=Tailscale Serve for Guinevere API
After=tailscaled.service
Requires=tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/bin/tailscale serve https / http://localhost:8000
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl enable tailscale-serve
sudo systemctl start tailscale-serve
```

### 4.5 Verify

```bash
# From the Android device or another tailnet node
curl -v https://<hostname>.<tailnet>.ts.net/health

# Check certificate details
echo | openssl s_client -connect <hostname>.<tailnet>.ts.net:443 -servername <hostname>.<tailnet>.ts.net 2>/dev/null | openssl x509 -noout -issuer -dates
```

The issuer should show Let's Encrypt. The certificate auto-renews before expiry.

## 5. Certificate Management and Renewal

### Cloudflare Tunnel

Cloudflare manages edge certificates automatically. You don't need to do anything. Certificates are issued, renewed, and rotated by Cloudflare without intervention. Typical validity is 90 days with automatic renewal well before expiry.

If you ever need to check status:

```bash
# Via Cloudflare API (requires API token)
curl -s https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/ssl/universal/settings \
  -H "Authorization: Bearer <API_TOKEN>" | jq .result
```

### Tailscale HTTPS

Tailscale handles Let's Encrypt certificate provisioning and renewal automatically. Certificates are valid for 90 days. Tailscale checks and renews them well before expiry, typically when less than 30 days remain.

Monitor certificate status:

```bash
# Check current certificate expiry
echo | openssl s_client -connect <hostname>.<tailnet>.ts.net:443 \
  -servername <hostname>.<tailnet>.ts.net 2>/dev/null | openssl x509 -noout -dates

# Check Tailscale logs for cert-related events
journalctl -u tailscaled --grep="cert" --since="7 days ago"
```

### Renewal Failures

If a certificate fails to renew:

1. Check DNS resolution. The domain must resolve to a Cloudflare or Tailscale address.
2. Verify the tunnel or Tailscale service is running.
3. Check logs: `journalctl -u cloudflared` or `journalctl -u tailscaled`.
4. For Tailscale, ensure port 443 is not blocked by a local firewall. Let's Encrypt needs to reach the node for the ACME challenge.

## 6. Security Considerations

### Port 8000 Isolation

The API port must remain internal-only. Enforce this with firewall rules:

```bash
# UFW example: block external access to 8000
sudo ufw deny from 0.0.0.0/0 to any port 8000
sudo ufw allow from 127.0.0.1 to any port 8000

# Or with iptables
sudo iptables -A INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
```

Verify the port is not externally reachable:

```bash
# From an external machine, this should time out or be refused
nc -zv <vps-public-ip> 8000
```

### No Plaintext HTTP for External Access

Never configure the surveillance webhook to use `http://` over the internet. Both Cloudflare Tunnel and Tailscale HTTPS give you valid certificates automatically. There is no reason to skip TLS.

If you see `http://` in any external-facing configuration, that's a bug. Fix it.

### HMAC-SHA256 Is Independent of TLS

TLS encrypts the transport layer. HMAC-SHA256 authenticates the application payload. They serve different purposes and both are required:

- **TLS** prevents eavesdropping and MITM attacks on the wire.
- **HMAC-SHA256** proves the request came from a holder of the shared secret, even if TLS is somehow compromised or terminated at a proxy.

Never remove HMAC validation just because TLS is active. Never remove TLS just because HMAC is active.

### Cloudflare WAF (Optional Hardening)

If you use Cloudflare Tunnel, you can add WAF rules for extra protection:

- Rate limiting on `/surveillance/events`
- IP allowlisting (if the Android device has a stable IP range)
- Request body size limits
- Bot detection

These are configured in the Cloudflare dashboard under **Security > WAF**.

## 7. Verification Steps

Run these checks after setting up either or both TLS paths.

### 7.1 Cloudflare Tunnel Verification

```bash
# 1. Tunnel is running
systemctl status cloudflared
# Expected: active (running)

# 2. HTTPS responds
curl -s -o /dev/null -w "%{http_code}" https://surveillance.<your-domain>/health
# Expected: 200

# 3. Certificate is valid
echo | openssl s_client -connect surveillance.<your-domain>:443 \
  -servername surveillance.<your-domain> 2>/dev/null | openssl x509 -noout -verify
# Expected: verify OK

# 4. Plaintext HTTP is rejected
curl -s -o /dev/null -w "%{http_code}" http://surveillance.<your-domain>/health
# Expected: 301 redirect to HTTPS, or connection refused

# 5. Webhook endpoint accepts POST with valid HMAC
curl -s -X POST https://surveillance.<your-domain>/surveillance/events \
  -H "Content-Type: application/json" \
  -H "X-Signature: sha256=<valid_hmac>" \
  -d '{"test": true}'
# Expected: 200 or 202
```

### 7.2 Tailscale HTTPS Verification

```bash
# 1. Tailscale serve is configured
tailscale serve status
# Expected: https://<hostname>.<tailnet>.ts.net/ -> http://localhost:8000

# 2. HTTPS responds from a tailnet node
curl -s -o /dev/null -w "%{http_code}" https://<hostname>.<tailnet>.ts.net/health
# Expected: 200

# 3. Certificate is valid (Let's Encrypt)
echo | openssl s_client -connect <hostname>.<tailnet>.ts.net:443 \
  -servername <hostname>.<tailnet>.ts.net 2>/dev/null | openssl x509 -noout -issuer
# Expected: issuer contains "Let's Encrypt"

# 4. Webhook endpoint accepts POST with valid HMAC
curl -s -X POST https://<hostname>.<tailnet>.ts.net/surveillance/events \
  -H "Content-Type: application/json" \
  -H "X-Signature: sha256=<valid_hmac>" \
  -d '{"test": true}'
# Expected: 200 or 202
```

### 7.3 Port Isolation Verification

```bash
# Port 8000 is not externally accessible
nmap -p 8000 <vps-public-ip>
# Expected: port 8000 filtered or closed

# Port 8000 is accessible locally
curl -s http://localhost:8000/health
# Expected: 200
```

## 8. Troubleshooting

### Cloudflare Tunnel Issues

**Tunnel won't start:**

```bash
journalctl -u cloudflared -n 50 --no-pager
```

Common causes:
- `credentials-file` path is wrong in `config.yml`
- The tunnel was deleted from the Cloudflare dashboard but `cloudflared` still references it
- DNS record conflicts with an existing A/AAAA record

**502 Bad Gateway:**

The tunnel is running but can't reach the origin. Check:
- The API is actually listening on port 8000: `ss -tlnp | grep 8000`
- The `service:` line in `config.yml` matches the API's actual bind address
- Firewall allows localhost connections on 8000

**Certificate errors:**

If `curl` reports certificate issues despite Cloudflare managing them:
- Make sure the domain's DNS is proxied through Cloudflare (orange cloud icon)
- Check SSL/TLS mode is "Full (strict)" in the Cloudflare dashboard
- Purge the Cloudflare cache for the domain

### Tailscale HTTPS Issues

**Certificate not issued:**

```bash
tailscale status
tailscale cert <hostname>.<tailnet>.ts.net
```

Common causes:
- MagicDNS is not enabled
- HTTPS certificates are not enabled in the admin console
- The node name doesn't match what you're requesting

**Connection refused from Android:**

- Verify the Android device is on the same tailnet: check the Tailscale app on the phone
- Make sure `tailscale serve` is configured: `tailscale serve status`
- Check that the API is running: `curl http://localhost:8000/health`

**Stale certificate:**

```bash
# Force certificate renewal
tailscale cert --force <hostname>.<tailnet>.ts.net
```

### General Issues

**HMAC validation fails over TLS but works locally:**

This usually means a proxy is modifying the request body. Check:
- Cloudflare isn't stripping or modifying headers
- Content-Type matches between what Tasker sends and what the API expects
- The HMAC is computed on the raw body, not a re-serialized version

**Intermittent timeouts:**

- Cloudflare Tunnel: check `cloudflared` logs for reconnect events
- Tailscale: check if the DERP relay is being used instead of a direct connection (`tailscale status` shows relay info)
- Both: verify the API isn't blocking on slow operations before responding

## 9. Quick Reference

| Item | Value |
|---|---|
| Internal API port | 8000 (localhost only) |
| Cloudflare Tunnel URL | `https://surveillance.<your-domain>` |
| Tailscale HTTPS URL | `https://<hostname>.<tailnet>.ts.net` |
| Webhook endpoint path | `/surveillance/events` |
| TLS version minimum | TLS 1.2 |
| Certificate provider (Cloudflare) | Cloudflare Universal SSL |
| Certificate provider (Tailscale) | Let's Encrypt |
| Certificate renewal | Automatic (both providers) |
| Application auth | HMAC-SHA256 (independent of TLS) |
| Port 8000 external access | Blocked by firewall |

---

*Document created for task P7-004. No real domain names, IP addresses, or credentials appear in this guide. Replace all `<placeholder>` values with your actual configuration.*
