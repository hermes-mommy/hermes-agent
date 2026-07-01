# P23 Research — Mobile/Android Action (Deferred Gate)

> Status: RESEARCH ONLY — no runtime code, deployment, or restart.
> Date: 2026-06-25
> Scope: P23 Embodied Operations / Personal OS Action Layer — mobile/Android surfaces
> Classification: STRICTLY PRIVATE & CONFIDENTIAL

---

## 1. Objective

This document researches the **mobile/Android action layer** for P23 "Embodied Operations / Personal OS Action Layer", specifically to evaluate whether P23-010 (mobile/Android action execution) should be included in MVP or **explicitly deferred behind a gate**.

The research covers:

- Existing mobile infrastructure in the Guinevere repo (P14, P15, P11, P7 Tasker, P21 voice gates).
- Android action surfaces: ADB, Android Intent API, Tasker HTTP-intent automation, Termux SSH server, Accessibility Service.
- Official Android documentation sources and retrieval date (2026-06-25).
- Isolation, consent, and classification posture for phone-level control.
- **Recommendation: P23-010 should be DEFERRED** with a clearly defined seam and a research-backed safe subset (if any).

---

## 2. Sources Consulted

### 2.1 Local repository artifacts

| Path | What it contains |
|------|------------------|
| `android/HealthConnectExport/` | Existing Kotlin Android app for Health Connect data export (P14). Demonstrates Health Connect permissions, `Activity`/`Intent`, file export, runtime permission model. |
| `.env.wearable.example` | Configuration for P14 wearable sync: Mi Fitness Cloud, device IDs, sync intervals, Redis/Postgres, SOPS, encryption. |
| `src/wearable/` | Python wearable sync/normalizer/health-consent pipeline. |
| `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` | Tasker + AutoNotification/AutoInput surveillance setup (app usage, location, notifications, clipboard). HMAC-signed HTTP POST to Guinevere API. Consent scopes: `surveillance.app_usage`, `surveillance.location`, `surveillance.notifications`, `surveillance.clipboard`. |
| `docs/setup-evidence/P7/STEP-P7-017/hmac-sign.js` + `tasker-hmac-jslet.md` | Tasker JavaScriptlet for HMAC signing of outbound surveillance events. |
| `docs/setup-evidence/plans/p15-windows-daemon.md` | P15 Windows Daemon design: WebSocket over Tailscale, Redis pub/sub, consent gate, command protocol, NSSM service wrapper. |
| `research-reports/p11-expansion/` + `src/channels/whatsapp/` | P11 WhatsApp via Neonize on VPS (not phone-hosted). |
| `docs/setup-evidence/P21/research/p21-consent-surveillance-research.md` | P21 voice always-listening 8-gate model: hard reject for MVP, explicit consent, fail-closed cache, audit trail, device auth, visible indicator, retention policy, safe-word/hard-stop. |
| `docs/30-data/31-SurveillanceDataPolicy_v1.0.md` | Surveillance data policy, multi-user capture restrictions, retention classes. |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | Revocable, scoped, auditable, purpose-bound, default-deny, fail-closed, non-silently-reactivating consent. |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Persona safety, safe-word, distress/crisis handling, surveillance boundaries. |

### 2.2 Official Android documentation (retrieved 2026-06-25)

| Topic | URL | Retrieval date |
|-------|-----|----------------|
| Android Debug Bridge (adb) overview | https://developer.android.com/tools/adb | 2026-06-25 |
| adb shell commands | https://developer.android.com/studio/command-line/adb#shellcommands | 2026-06-25 |
| Run apps on a hardware device (USB/wireless debugging) | https://developer.android.com/studio/run/device | 2026-06-25 |
| Intents and intent filters | https://developer.android.com/guide/components/intents-filters | 2026-06-25 |
| Sending the user to another app | https://developer.android.com/training/basics/intents/sending | 2026-06-25 |
| Intent reference | https://developer.android.com/reference/android/content/Intent | 2026-06-25 |
| Activity reference | https://developer.android.com/reference/android/app/Activity | 2026-06-25 |
| Create an accessibility service | https://developer.android.com/guide/topics/ui/accessibility/service | 2026-06-25 |
| AccessibilityService reference | https://developer.android.com/reference/android/accessibilityservice/AccessibilityService | 2026-06-25 |
| SDK Platform Tools release notes | https://developer.android.com/tools/releases/platform-tools | 2026-06-25 |

### 2.3 Community / third-party documentation

| Topic | Source | Notes |
|-------|--------|-------|
| Termux SSH server | DEV Community, Super User, Medium, GitHub gists | `pkg install openssh`, `sshd` on port 8022, key or password auth. |
| Tasker HTTP webhook | Reddit /r/tasker, Tasker docs, Apilio community | Tasker can receive/send HTTP requests; native HTTP GET/POST triggers in beta. |
| ADB over Wi-Fi security | Stack Overflow, Trustwave SpiderLabs | Unauthenticated full phone access if ADB binds to all interfaces; requires trusted network. |

---

## 3. Findings

### 3.1 Existing mobile infrastructure map

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Mobile/Android surfaces                      │
├──────────────────────────────────────────────────────────────────────┤
│ P14 Wearable                                                          │
│   ├─ android/HealthConnectExport/ (Kotlin, Health Connect API)        │
│   ├─ .env.wearable / .env.wearable.example                            │
│   ├─ src/wearable/ (sync, normalizer, health_consent, anomaly)        │
│   └─ Data flow: phone Health Connect → JSON export → WebDAV           │
│       (Gadgetbridge) or Mi Fitness Cloud → VPS ingestion              │
├──────────────────────────────────────────────────────────────────────┤
│ P7 Android surveillance (read-only)                                   │
│   ├─ Tasker profiles: app usage, location, notifications, clipboard   │
│   ├─ AutoNotification / AutoInput plugins                             │
│   ├─ HMAC-signed HTTP POST → /surveillance/events                     │
│   └─ Consent scopes: surveillance.app_usage, .location, etc.          │
├──────────────────────────────────────────────────────────────────────┤
│ P15 Windows Daemon (nearby personal OS)                               │
│   ├─ WebSocket client on Windows → VPS over Tailscale                 │
│   ├─ Active window, idle, git context trackers                        │
│   ├─ Command protocol via Redis DB4 pub/sub                           │
│   └─ Consent gate + Discord /pc command                                 │
├──────────────────────────────────────────────────────────────────────┤
│ P11 WhatsApp                                                          │
│   └─ Neonize on VPS (not phone); bridges WhatsApp Web/Multi-Device    │
└──────────────────────────────────────────────────────────────────────┘
```

**Key insight:** Guinevere already has a rich mobile *read* layer (P7, P14) and a nearby personal-OS read layer (P15), but **no mobile *write/action* layer** exists. P23-010 would be the first phone-control surface.

### 3.2 Android action surfaces research table

| Surface | Mechanism | Level of control | Typical use cases | Consent/risk class |
|---------|-----------|------------------|-------------------|---------------------|
| **ADB (USB / wireless)** | `adb shell`, `adb shell input`, `adb shell am start`, `adb shell screencap`, `adb install` | Very high — shell-level access, can install/uninstall apps, inject input, read screen, run privileged commands with shell user | App launch, input injection, screenshot, logcat, package install, file push/pull | **CRITICAL** — full device control if RSA key accepted; over Wi-Fi can bind to all interfaces |
| **Android Intent API** | `am start -a android.intent.action.VIEW -d <uri>`, `startActivity()` | Medium — launches activities, sends broadcasts, starts services | Open app, share text, dial number, open settings, deep-link | **RESTRICTED/CRITICAL** depending on target action |
| **Tasker HTTP → intent** | Tasker receives HTTPS webhook, runs action (e.g., launch app, send SMS, set brightness) | Medium-high — depends on Tasker privileges and plugins | Notification mirror, app launch, toggles | **CRITICAL** if it reads notifications/SMS; **RESTRICTED** for app-launch/toggles |
| **Termux SSH server** | `sshd` in Termux; remote shell into Android | Very high if combined with root; medium as unprivileged Linux env | Run scripts, bridge tools, ADB over network | **CRITICAL** if shell access is automated |
| **Accessibility Service** | Custom service extends `AccessibilityService`; receives UI events, can perform actions | Very high — can read screen, click UI elements, intercept text | Automated UI actions, screen reading, assistive tech | **CRITICAL** — screen-reading and remote action enabler |

#### 3.2.1 ADB (Android Debug Bridge)

From the official Android docs (retrieved 2026-06-25):

> "Android Debug Bridge (adb) is a versatile command-line tool that lets you communicate with a device."
> — https://developer.android.com/tools/adb

Key capabilities relevant to P23:

- `adb shell` — run shell commands on the device.
- `adb shell input tap x y` / `input text` / `input keyevent` — inject touch, text, key events.
- `adb shell am start -n <package>/<activity>` — launch app component via Activity Manager.
- `adb shell screencap` / `screenrecord` — capture screen.
- `adb install <apk>` — install application packages.
- `adb shell pm ...` — package manager (list/install/disable packages).

**Connectivity modes:**

- **USB debugging:** requires enabling *Developer options → USB debugging* and accepting the host RSA key on the device.
- **Wireless debugging (Android 11+ / API 30+):** pair via QR code or pairing code; device and workstation must be on the same network; mDNS auto-discovery.

Official docs note the security model:

> "When you connect a device running Android 4.2.2 (API level 17) or higher, the system shows a dialog asking whether to accept an RSA key that allows debugging through this computer. This security mechanism protects user devices because it ensures that USB debugging and other adb commands cannot be executed unless you're able to unlock the device and acknowledge the dialog."
> — https://developer.android.com/tools/adb

**Blast radius:** An authorized ADB session grants shell-level access. Combined with a vulnerable or rooted device, it is equivalent to near-root remote control. ADB over Wi-Fi, if misconfigured, can expose the device to the local network.

#### 3.2.2 Android Intent API

From official Android docs (retrieved 2026-06-25):

> "Intents are messaging objects used in Android to request actions from other app components, enabling communication between activities, services, and broadcast receivers."
> — https://developer.android.com/guide/components/intents-filters

Relevant intent actions:

- `android.intent.action.MAIN` + `CATEGORY_LAUNCHER` — launch app.
- `android.intent.action.VIEW` — open URI in browser or app.
- `android.intent.action.SEND` — share content.
- `android.intent.action.DIAL` / `CALL` — dialer/phone.
- `android.settings.*` — open system settings.

Examples via `am start`:

```bash
# Open a URL
adb shell am start -a android.intent.action.VIEW -d "https://example.com"

# Launch a specific activity
adb shell am start -n com.example.app/.MainActivity

# Open settings
adb shell am start -a android.settings.SETTINGS
```

**Risk:** Lower than ADB shell because it is narrower, but still powerful. A malicious or buggy `am start` loop can disrupt the user. Calling `CALL` or `SEND` without consent can incur cost or leak data.

#### 3.2.3 Tasker HTTP → intent / notification mirror

Existing P7 already uses Tasker as a read-side surveillance collector. Tasker can also act as an **action executor**:

- Receive an HTTPS webhook via Tasker "HTTP Request" event/profile (beta in Tasker 6.2+).
- Trigger tasks that:
  - Launch apps (`App → Launch App`).
  - Send notifications (`Alert → Notify`).
  - Toggle settings (Wi-Fi, Bluetooth, brightness, volume).
  - Send SMS (requires SMS permission).
  - Read notifications (via AutoNotification).

**P23-010 seam idea:**

```
VPS Guinevere ──HTTPS webhook──→ Android Tasker ──→ Android Intent / Action
                                 (HMAC-signed,    (launch app, notification,
                                  consent-gated)    toggle setting)
```

Pros:
- Reuses existing HMAC + consent infrastructure from P7.
- No ADB required; works over normal network.
- Tasker runs in user space with explicit permissions.

Cons:
- Tasker is a third-party app with its own update/permission model.
- Notification reading is **Critical** surveillance data.
- App launching still touches the user's phone UI and can be disruptive.
- Battery optimization, Doze, and OEM killers can break reliability.

#### 3.2.4 Termux SSH server

Termux provides a Linux environment on Android with `openssh`, allowing an SSH server on a non-root port (default 8022).

Use cases for P23:
- Remote shell for debugging.
- Run Python/Node scripts on the phone.
- Bridge ADB or other tools from VPS → Termux → Android.

Risks:
- SSH into phone = remote code execution on personal device.
- Authentication (password/key) must be tightly managed.
- No sandbox separation from Android user data beyond Linux permissions.
- App can be killed by Android; server does not survive reboot.

This is **not recommended for P23-010 MVP**. It would be a high-risk dependency and a large operational burden.

#### 3.2.5 Accessibility Service

From official Android docs (retrieved 2026-06-25):

> "To create an accessibility service, you must extend the AccessibilityService class and declare the service in your app's manifest."
> — https://developer.android.com/guide/topics/ui/accessibility/service

Capabilities:
- Receive window/content change events.
- Read on-screen text.
- Perform gestures and UI actions programmatically.

Risks:
- This is the most privileged "regular" Android API for remote UI automation.
- Requires explicit user consent in Accessibility settings.
- Play Store policy heavily restricts accessibility-service usage to assistive functionality.
- **Critical classification** — reads screen content, can touch any app.

This is explicitly **out of scope for MVP** and should only be considered under the same 8-gate model as P21 always-listening.

### 3.3 Isolation and risk analysis

#### 3.3.1 Why mobile action is higher risk than existing read-only mobile infra

| Existing surface | Direction | Blast radius if misused |
|------------------|-----------|---------------------------|
| P14 Health Connect export | Read | Health data exposure |
| P7 Tasker surveillance | Read | Notification/location/clipboard exposure |
| P15 Windows daemon | Read + commands to Windows PC | PC app launch, system info |
| **P23 mobile action** | **Write/control phone** | **App launch, input injection, notification dismissal, call/SMS initiation, screen capture, settings changes, potential financial/data loss** |

Phone = personal/intimate device. Phone control = intimate surveillance + high blast radius + Android fragmentation (OEM-specific permission/battery behavior).

#### 3.3.2 Android fragmentation risks

- Different OEMs (Samsung, Xiaomi, Oppo, Vivo, etc.) apply aggressive battery optimization and background-kill logic.
- Permission dialogs and Accessibility settings vary by skin.
- Android version distribution affects availability of wireless ADB, foreground services, notification listener permissions.
- Play Store policy for accessibility services and background execution becomes stricter over time.

These factors make a reliable, safe, cross-device mobile action MVP **non-trivial** and **high-maintenance**.

### 3.4 DEFERRED-GATE recommendation for P23-010

**Verdict: P23-010 (mobile/Android action execution) is DEFERRED from MVP.**

Design the seam now, implement later.

#### 3.4.1 Rationale

1. **Intimate blast radius.** A phone is the most personal compute surface. Mis-automated app launch, notification dismissal, or input injection can disrupt Faiz's day, incur cost, or leak sensitive context.
2. **Surveillance-class data.** Reading notifications/SMS, screen content, or app state for action planning is **Critical** under `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`.
3. **High Android fragmentation.** Behavior across OEMs and Android versions is unpredictable; an MVP must not ship untested automation on the user's primary phone.
4. **Maturity of existing mobile infra.** P14 (wearable) and P15 (Windows daemon) read layers should mature first. P23 action should not precede a stable read/consent/audit foundation.
5. **Mirror P21 caution.** P21 always-listening is blocked with 8 explicit gates. Mobile action on a phone is at least as sensitive as always-listening voice capture. It should receive the same 8-gate treatment.

#### 3.4.2 Proposed seam design (non-implemented)

A future P23-010 implementation can use a **Tasker webhook receiver seam**:

```
VPS Guinevere action request
    │
    ▼
Consent gate (p23:mobile:notification or p23:mobile:app-launch)
    │
    ▼
HMAC-signed HTTPS POST to Tasker webhook URL
    │
    ▼
Tasker on Android
    │
    ├─ If action_class == "notification_mirror" and consent == granted:
    │      AutoNotification query → HMAC POST back to VPS (read-only, L1)
    │
    └─ If action_class == "app_launch" and consent == granted:
           Launch App intent via Tasker (L3)
```

**Webhook contract (draft, not implemented):**

```json
{
  "request_id": "uuid",
  "action_class": "app_launch | notification_mirror | toggle_setting",
  "scope": "p23:mobile:app-launch | p23:mobile:notification",
  "payload": {
    "package": "com.example.app",
    "intent_action": "android.intent.action.MAIN",
    "extras": {}
  },
  "consent_token": "ledger-nonce-or-token",
  "timestamp": 1719312000
}
```

Headers:

- `X-Signature`: HMAC-SHA256 of canonical signing string.
- `X-Timestamp`: Unix epoch seconds.
- `X-Nonce`: UUID v4.

**Required gates (mirror P21 8-gate model):**

| # | Gate | Requirement |
|---|------|-------------|
| 1 | Explicit Faiz consent | `p23:mobile:*` scope granted per action-class |
| 2 | Visible indicator | Tasker logs/actions visible to user; Discord/dashboard shows phone action state |
| 3 | Retention policy | Notification/action logs classified and bounded |
| 4 | HARD STOP honored | Phone action immediately pausable via safe-word / safe-mode |
| 5 | Audit trail | Every action request, consent check, and failure logged |
| 6 | Device authentication | HMAC + device ID + nonce; reject unsigned/unpaired requests |
| 7 | Purpose bound | Only approved action classes allowed (whitelist) |
| 8 | No silent reactivation | Revocation pauses action class; explicit restore required |

### 3.5 Safe subset if any

**MVP candidate (with explicit consent):** Tasker webhook → **notification mirror (read-only, L1)**

- Tasker uses AutoNotification to query existing notifications (not intercept live notifications).
- Sends HMAC-signed JSON to Guinevere API.
- Scope: `p23:mobile:notification` (read-only, L1).
- Classification: **CRITICAL** because notifications are intimate.
- Requires:
  - Explicit consent (`p23:mobile:notification`).
  - Fail-closed consent cache.
  - No automated response/dismissal without additional consent.
  - Retention max 7 days for non-critical, shorter for sensitive apps.

**NOT MVP:**

- App launch via ADB (`am start` or `input`) — L3, requires device-level trust.
- Input injection / UI automation — L4, Accessibility Service level.
- SMS / call actions — financial/privacy blast radius, CRITICAL.
- Termux SSH server for remote phone shell — CRITICAL, operational burden.

### 3.6 Consent and classification

Per `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` and `Guinevere_SurveillanceDataPolicy_v1.0.md`:

| Data / action | Classification | Rationale |
|---------------|----------------|-----------|
| Notification content (read) | **CRITICAL** | Intimate, may contain OTP, personal messages, financial alerts |
| App launch history / action log | **RESTRICTED** | Reveals behavior and interests |
| Screen content / screencap | **CRITICAL** | Highly intimate, possible credentials/private data |
| App launch action | **RESTRICTED/CRITICAL** | Can disrupt user, incur cost, or leak context |
| Settings toggle / input injection | **CRITICAL** | Direct phone control, possible cost or security impact |

**Consent scopes proposed:**

- `p23:mobile:notification` — read-only notification mirror.
- `p23:mobile:app-launch` — launch specified apps via Tasker/Intent.
- `p23:mobile:toggle` — toggle settings (future, not MVP).
- `p23:mobile:input` — input injection / UI automation (future, Accessibility Service, 8-gate).

All scopes default to **OFF**, are revocable, auditable, purpose-bound, and fail-closed.

### 3.7 Failure modes

| Failure | Cause | Mitigation |
|---------|-------|------------|
| ADB disconnect | USB unplugged, wireless ADB network change, RSA key revoked | Use Tasker webhook instead; do not rely on ADB for production actions |
| Permission denied | Android permission dialog not granted, Tasker permission removed | Fail-closed; action denied; audit log |
| App crash / ANR | Target app not installed, Intent malformed, OEM kills background app | Validate package before launch; catch exceptions; report failure |
| Consent withdrawn mid-action | Faiz revokes scope | Check consent cache immediately before action; deny and audit |
| Network timeout / HMAC mismatch | Tailscale/Wi-Fi issue, secret rotation, clock skew | Replay-protected HMAC; exponential backoff; alert |
| Battery optimization kills Tasker | OEM aggressive background kill | Document manual exemption; not rely on Tasker for safety-critical actions |
| Malicious/buggy action request | Logic error or prompt injection | Whitelist action classes; human confirmation for CRITICAL actions |

---

## 4. Implications for P23 Design

1. **Scope reduction.** P23 MVP should focus on *planning* and *reasoning* about actions, not executing phone actions. The executor seam is designed but not implemented.
2. **Consent infrastructure reuse.** Reuse `src/surveillance/consent_gate.py`, consent ledger, Redis cache, and audit patterns from P7/P15/P21.
3. **Action class whitelist.** Any future executor must accept only whitelisted action classes and reject everything else.
4. **No ADB dependency for MVP.** ADB is a development/debug tool, not a production remote-control mechanism.
5. **Notification read-only as the only safe subset.** If the planner insists on an MVP phone feature, notification mirror is the smallest, consent-gated, read-only candidate.

---

## 5. Risks / Open Questions

| ID | Risk / Open Question | Priority |
|----|----------------------|----------|
| R1 | Phone control has intimate blast radius; mis-automation can disrupt daily life or cause financial loss. | High |
| R2 | Android fragmentation means the same Tasker profile may behave differently across Samsung/Xiaomi/Oppo devices. | High |
| R3 | Accessibility Service and ADB require deep permissions that are hard to revoke granularly. | High |
| R4 | Tasker is a third-party paid app with its own update cadence and potential deprecation. | Medium |
| R5 | Notification reading is CRITICAL data; retention and minimization must be strictly enforced. | High |
| R6 | P23-010 could expand scope to include call/SMS actions, which should be explicitly banned from MVP. | High |
| R7 | How will the VPS authenticate to the phone without exposing credentials or ADB over network? (Answer: HMAC-signed Tasker webhook over HTTPS, device-bound secret.) | Medium |
| R8 | Should phone actions require real-time human confirmation for CRITICAL classes? (Recommendation: yes, until fully trusted.) | Medium |

---

## 6. Recommendations to Planner

1. **Defer P23-010 to post-MVP.** Mark it as "DEFERRED — design seam only" in the P23 enterprise plan.
2. **Design the seam now, implement later.** Document the Tasker webhook contract, consent scopes, HMAC signing, and action-class whitelist.
3. **Mirror P21 8-gate model.** Any future phone action must pass the same gates as always-listening voice.
4. **If an MVP phone feature is mandatory, choose notification read-only mirror.** It is the smallest, safest, consent-gated subset.
5. **Do not use ADB for production actions.** Restrict ADB to development and emergency debugging.
6. **Update policies.** Add `p23:mobile:*` scopes to the consent taxonomy and classify phone-control data/actions as CRITICAL/RESTRICTED.
7. **Plan future architecture.** After P14/P15 mature and Faiz explicitly consents per action-class, implement the Tasker webhook executor behind the 8 gates.

---

## 7. Verdict

**P23-010 Mobile/Android Action is DEFERRED from MVP.**

Phone-level control is intimate surveillance with high blast radius and severe Android fragmentation. The recommended seam is a Tasker webhook receiver with HMAC-signed requests and per-action-class consent scopes (`p23:mobile:notification`, `p23:mobile:app-launch`), but it should not be built until:

- P14 and P15 mobile/personal-OS infrastructure have matured,
- explicit Faiz consent per action-class is obtained,
- the P21 8-gate model is applied and verified, and
- a read-only notification mirror (L1) has been safely piloted.

No runtime code, deployment, or restart is authorized by this research document.

---

*End of research document.*
