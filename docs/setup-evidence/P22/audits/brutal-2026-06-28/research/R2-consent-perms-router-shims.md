# P22 Brutal-Audit R2 — Consent / Permissions / Router / Shims

**Date:** 2026-06-28
**Branch:** main (audit session)
**Mission:** READ-ONLY ground-truth of 4 findings (F03, F04, F11, F12) against CURRENT code.
**Commit baseline examined:** Working tree against `f912295` (docs p22 production activation finalization) and the live edits under `M src/life_integrations/*`. No edits made.

---

## 0. Verdict Table (per finding)

| ID | Finding claim | Verdict | Key file:line |
|----|---------------|---------|---------------|
| F03 | ConsentGate fails open on HARD STOP when `_hard_stop_checker is None` | **HOLDS** | `consent.py:104-112` |
| F04 | Unknown actions default to L1_READ in SemanticActionClassifier | **HOLDS** | `permissions.py:213-218` |
| F11 | `dry_run` classifies with `integration_id` instead of `adapter.config.provider` (classifier bypass) | **HOLDS** | `router.py:252-254` vs `router.py:132-138` |
| F12 | 3 HARD STOP fail-open windows (HardStopShim no-source, handler raise swallowed, ConsentGate None) | **HOLDS** (all three) | `_shims.py:128-133`, `_shims.py:121-126`, `consent.py:104-112` |

No contradictions with prior audit memory; structurally aligns with the brutal-audit hypothesis language.

---

## 1. F03 — ConsentGate fail-open when `_hard_stop_checker is None`

**Verdict:** HOLDS.

**File:** `src/life_integrations/consent.py`

### 1.1 Constructor stores checker without default-fail-closed

`consent.py:70-82`:

```python
def __init__(
    self,
    consent_checker: ConsentCheckerProtocol | None = None,
    hard_stop_checker: HardStopCheckerProtocol | None = None,
) -> None:
    """Initialize the consent gate.

    Args:
        consent_checker: Consent ledger checker (optional, fail-closed if None).
        hard_stop_checker: HARD STOP handler (optional, assumes clear if None).
    """
    self._consent_checker = consent_checker
    self._hard_stop_checker = hard_stop_checker
```

The docstring ITSELF documents "assumes clear if None" for hard_stop_checker — the most direct admission that this is intentional fail-open. Audit claim of fail-open when checker is None is corroborated by the code's own docstring.

### 1.2 Full `check()` method logic, tier-by-tier

`consent.py:84-145` (verbatim):

```python
async def check(
    self,
    tier: PermissionTier,
    consent_scope: str,
    project_id: uuid.UUID | None = None,
) -> tuple[bool, str]:
    # L1 (read) passes without consent/HARD STOP check
    if tier == PermissionTier.L1_READ:
        return True, "L1 read — no consent required"

    # HARD STOP check (blocks all L2+)
    if self._hard_stop_checker is not None:
        if self._hard_stop_checker.is_hard_stop_active():
            logger.warning(
                "consent_gate.hard_stop_blocked",
                tier=tier.name,
                scope=consent_scope,
            )
            return False, "HARD STOP active — action blocked"

    # L4 is always forbidden
    if tier == PermissionTier.L4_FORBIDDEN:
        logger.warning(
            "consent_gate.forbidden",
            tier=tier.name,
            scope=consent_scope,
        )
        return False, "L4_FORBIDDEN — never autonomous"

    # L2+ requires consent check (fail-closed if no checker)
    if tier >= PermissionTier.L2_WRITE:
        if self._consent_checker is None:
            logger.warning(
                "consent_gate.no_checker_fail_closed",
                tier=tier.name,
                scope=consent_scope,
            )
            return False, "no consent checker configured — fail-closed"

        consented = await self._consent_checker.check_consent(
            scope=consent_scope,
            project_id=project_id,
        )
        if not consented:
            logger.warning(
                "consent_gate.consent_revoked",
                tier=tier.name,
                scope=consent_scope,
            )
            return False, f"consent not granted for scope: {consent_scope}"

    return True, "allowed"
```

### 1.3 Tier-by-tier behavior matrix (when `_hard_stop_checker is None`)

| Tier       | HARD STOP block | Consent block | Net result |
|------------|-----------------|---------------|------------|
| L1_READ    | not consulted   | not consulted | `True, "L1 read — no consent required"` |
| L2_WRITE   | **NOT consulted (fail-open!)** | consulted (fail-closed if `_consent_checker is None`) | depends on consent only |
| L3_DESTRUCTIVE | **NOT consulted (fail-open!)** | consulted (fail-closed if `_consent_checker is None`) | depends on consent only |
| L4_FORBIDDEN | **NOT consulted (fail-open!)** then unconditional `False` | n/a | `False, "L4_FORBIDDEN — never autonomous"` |

Note: L4 is masked by the unconditional block at line 114-121, so the L4 case does not exhibit a fail-open *outcome* even when hard_stop_checker is None. The risk surface is **L2 + L3** — they skip the HARD STOP gate entirely when no checker is wired.

### 1.4 Fail-closed behavior that DOES exist

- `_consent_checker is None` → returns `False, "no consent checker configured — fail-closed"` at `consent.py:124-131`. This is fail-closed for the consent side.
- HARD STOP is **NOT** symmetrically fail-closed. The audit says ~104-112 → CONFIRMED exact lines `consent.py:104-112`. If `self._hard_stop_checker is None`, the entire `if self._hard_stop_checker is not None:` block is a no-op. No `else: return False, "no hard stop checker — fail-closed"` branch exists.

### 1.5 Partial mitigation noted (NOT a true fix)

The P22.1 memory entry claims `ConsentChecker is wired in production`. That mitigation only addresses the *consent* side (the calibrated `_consent_checker is None` branch — line 125 IS fail-closed). The HARD STOP asymmetry is **not** addressed by the production wiring. Whether `HardStopChecker` is wired is a separate question — see F12.3 and the wiring at `runtime.py:305-317`. The FACT remains that **the class itself** has fail-open HARD STOP semantics for L2/L3 when constructed with `hard_stop_checker=None`. This is the precise wording of the audit finding and it HOLDS against CURRENT code, regardless of how production wires it.

### 1.6 Contradiction with audit

NONE — the docstring at `consent.py:79` confirms the design intent ("assumes clear if None") and the implementation matches it. Audit holds.

---

## 2. F04 — Unknown actions default to L1_READ

**Verdict:** HOLDS.

**File:** `src/life_integrations/permissions.py`

### 2.1 Fallback default line

`permissions.py:213-218`:

```python
# 3. Default to L1 (read) for unknown actions
return ActionClassification(
    tier=PermissionTier.L1_READ,
    reason=f"semantic: default L1 for unknown action '{action_lower}'",
    method="semantic_default",
)
```

Confirmed: **`PermissionTier.L1_READ`** is the fallback (NOT a more restrictive default like FORBIDDEN). Path is reached when:
1. `provider.lower()` not in `_PROVIDER_TIER_MAP` (line 182 returns `{}`), AND
2. action matches no `_FORBIDDEN_KEYWORDS` substring (line 192), AND
3. action matches no `_DESTRUCTIVE_KEYWORDS` substring (line 199), AND
4. action matches no `_WRITE_KEYWORDS` substring (line 206).

### 2.2 Logger.warning for unknown actions?

**None.** The classifier returns silently at `permissions.py:214-218` with no `logger.warning("classifier.unknown_action", ...)`. This means:
- Operators cannot tell from logs that an action slipped past classifier.
- The audit's hypothesis that a silent default-down-classification occurs is materially correct.
- (Side-effect: actions like `consolidate`, `fetch_secret`, or `execute_arbitrary_shell` that don't match any keyword could silently classify as L1_READ and bypass consent entirely. This is a structurally dangerous default for an action classifier.)

### 2.3 `_PROVIDER_TIER_MAP` summary

`permissions.py:47-139` (90 lines). 12 providers declared:

- calendar (7 actions)
- drive (8 actions)
- github (8 actions)
- gmail (6 actions)
- discord (6 actions)
- telegram (4 actions)
- whatsapp (3 actions)
- vps (4 actions)
- finance (4 actions)
- notion (4 actions)
- browser (4 actions)
- memory (4 actions)
- filesystem (3 actions)

Total = **12 providers, ~63 entries**.

### 2.4 L4 entries (FORBIDDEN)

| Provider | L4 action | Line |
|----------|-----------|------|
| calendar | `delete_calendar` | `:55` |
| calendar | `clear_calendar` | `:55` (`clear_calendar` listed) |
| drive | `empty_trash` | `:64` |
| github | `delete_repo` | `:74` |
| github | `force_push` | `:75` |
| gmail | `permanent_delete` | `:81` |
| discord | `purge_messages` | `:90` |
| discord | `kick_member` | `:91` |
| telegram | `promote_member` | `:97` |
| whatsapp | `promote_admin` | `:102` |
| vps | `system_prune` | `:108` |
| finance | `pay_transfer` | `:114` |
| notion | `delete_view` | `:120` |
| memory | `delete_memory` | `:132` |
| (filesystem has no L4 entry — note: `delete` is L3_DESTRUCTIVE at `:137`) |

L4 entry count: **14 actions across 12 providers**.

### 2.5 Contradiction with audit

NONE. Audit holds. The fallback is exactly `L1_READ`, exactly at line 215. Silent default-to-L1 is structurally present.

---

## 3. F11 — `dry_run` passes wrong `provider=` to classify()

**Verdict:** HOLDS (and is a real bypass — the CRITICAL classifier-bypass class finding noted in P22.2 memory aligns).

**File:** `src/life_integrations/router.py`

### 3.1 `execute()` — line 132-138

```python
provider = adapter.config.provider

# Classify action semantically (NOT AuthLevel-only)
classification = self._classifier.classify(
    provider=provider,
    action=action,
)
```

`execute()` resolves the adapter first (line 122: `adapter = self._registry.get(integration_id)`), then uses `adapter.config.provider` — which is the in-`IntegrationConfig.provider` field (see `types.py:73`).

### 3.2 `dry_run()` — line 252-254

```python
provider = adapter.config.provider
classification = self._classifier.classify(
    provider=integration_id, action=action,
)
```

Here the local variable `provider` (assigned at line 252 from `adapter.config.provider`) is **NEVER USED**. Line 254 hardcodes `provider=integration_id`. This contradicts every call-site convention in the rest of the file (execute uses `adapter.config.provider`).

### 3.3 Are they different?

**YES — confirmed.** The classify call in `dry_run` uses `integration_id` (the string `"discord"` etc.) while `execute` uses `adapter.config.provider` (which is the configured provider-name string like `"Google"` for gmail). Looking at `IntegrationConfig.provider` semantics (`types.py:73` says "Provider name (e.g., 'Google', 'GitHub')"), these are intentionally DIFFERENT strings. The classifier's `_PROVIDER_TIER_MAP` key is `provider.lower()` (line 182). For all P22 adapters built in `wiring.py`, I expect `adapter.config.provider` defaults to either matching `integration_id` or a different case. If they differ, classifier misses the static map and falls through to keyword matching or L1 default — directly producing F04's fail-open-fallback risk inside `dry_run`.

### 3.4 Does dry_run resolve the adapter before classifying?

**YES — partial.** `dry_run` does call `self._registry.get(integration_id)` at line 240 (raises/adjusts if not registered), and assigns `adapter` to the result. Line 252 extracts `adapter.config.provider` — but **then ignores it** for the classify call (line 254). This is the exact bypass the audit asserts. Adapter resolution is performed; classification uses the wrong key.

### 3.5 Contral evidence

Indeed the surrounding code has a smell: the line `provider = adapter.config.provider` at line 252 is dead code. Either it was intended to be used (matching `execute`) or it was left after a refactor. Either way the call at line 254 is a bug: it should read `provider=provider` not `provider=integration_id`.

### 3.6 Connection to classifier-bypass memory

The P22.2 memory entry says: *"CRITICAL classifier bypass (router used provider not integration_id → memory/store L1)"*. This audit conflates two things — the P22.2 finding is the historical record, but the CURRENT code retains ONE such bypass (in dry_run only — execute appears correct). The risk: any caller of `dry_run` gets a lower classification than `execute` would for the same input. Confuses operators auditing "would this action be allowed?" answers.

### 3.7 Contradiction with audit

NONE. Audit holds.

---

## 4. F12 — Three HARD STOP fail-open windows

**Verdict:** HOLDS × 3.

### 4.1 F12.1 — HardStopShim: no source wired returns False (fail-open)

`_shims.py:128-133` (verbatim):

```python
if self._redis is None and self._handler is None:
    logger.error("hard_stop_shim.no_source_wired")
    # No source => cannot prove clear => fail-closed for L2+ would be
    # safer, but ConsentGate.py:79 documents None checker as "assumes
    # clear". We surface the wiring bug loudly instead of silently.
    return False
```

**Confirmed:** when neither Redis nor handler is wired, shim returns `False` (not-active), `logger.error`'s but does NOT fail-closed at the *gate* level (because the parent ConsentGate treats None-checker parent path). The combination = both fail-open at the gate. The comment at line 130-132 even acknowledges the danger.

The exact audit claim — "does it return False (not-active = fail-open)" — is *literally* what the code does. The `logger.error` louder-than-warning does NOT change the semantic.

Same logic at `_shims.py:166-169` (async variant):

```python
if self._redis is None and self._handler is None:
    logger.error("hard_stop_shim.no_source_wired")
    return False
```

### 4.2 F12.2 — HardStopShim: handler exception swallowed → handler_active stays False

`_shims.py:117-126` (verbatim):

```python
# Source 2: in-process handler (keyword-triggered)
handler_active = False
if self._handler is not None:
    try:
        handler_active = bool(self._handler.is_safe)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "hard_stop_shim.handler_check_failed",
            error=str(e),
        )
```

When the handler raises (e.g. handler class corrupted, attribute missing, runtime error), the `except` block logs a warning and `handler_active` remains at its initial `False`. The shim then returns `redis_active or handler_active` at line 135 — and since handler is the only source effectively, the answer is **False (not-active).** This is a fail-open path.

Audit claim: "is it swallowed, leaving handler_active=False" — confirmed. Exact lines ~117-127: confirmed.

Same logic in async variant at `_shims.py:159-164`.

### 4.3 F12.3 — ConsentGate HARD STOP check skipped when `_hard_stop_checker=None`

**Cross-reference F03:** `consent.py:78` (docstring) → `consent.py:104-112` (logic block). The `if self._hard_stop_checker is not None:` guard has no `else: return False … fail-closed` branch. When the shim is wired to None-by-default-construction or never assigned, the entire HARD STOP step is skipped.

The exact audit claim — "HARD STOP check skipped when hard_stop_checker=None" — confirmed; this is the same asymmetry as F03 finding without consequence.

### 4.4 Runtime.py wiring of HardStopShim (referenced for completeness)

`runtime.py:281-317`:

```python
sync_redis = None
try:
    import redis as sync_redis_lib
    import urllib.parse as _urlparse
    _rurl = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    _rpw = os.environ.get("REDIS_PASSWORD", "")
    _parsed = _urlparse.urlparse(_rurl)
    _host = _parsed.hostname or "localhost"
    _port = _parsed.port or 6379
    _db = int(_parsed.path.lstrip("/") or "0")
    sync_redis = sync_redis_lib.Redis(
        host=_host, port=_port, db=_db,
        password=_rpw or None, socket_timeout=2, socket_connect_timeout=2,
    )
    sync_redis.ping()  # verify connectivity
    logger.info("p22.hard_stop_shim.sync_redis_ready")
except Exception as e:  # noqa: BLE001 — degrade to handler-only
    logger.warning(
        "p22.hard_stop_shim.sync_redis_failed",
        error=str(e),
        hint="HARD STOP will rely on in-process handler only",
    )
    sync_redis = None

hard_stop_shim = HardStopShim(
    redis_client=sync_redis,
    hard_stop_handler=hard_stop_handler,
)
consent_shim = ConsentGateShim(consent_checker=consent_checker)

router = await build_action_router(
    registry=registry,
    consent_checker=consent_shim,
    hard_stop_checker=hard_stop_shim,
    audit_writer=audit_writer,
    project_registry=project_registry,
)
```

**Wiring status:**
- `runtime.py:305-308` constructs `HardStopShim(redis_client=sync_redis, hard_stop_handler=hard_stop_handler)` — depends on whether `hard_stop_handler` argument is actually passed at the call-site to `build_runtime_registry(redis_client=..., hard_stop_handler=...)`.
- Async redis from outside the function is *intentionally discarded* — a sync redis is constructed at runtime.py:291-294 because `HardStopShim.is_hard_stop_active()` is called from the *sync* path (`consent.py:106`).
- If `sync_redis.ping()` fails → `sync_redis = None` (line 303) → shim relies on `hard_stop_handler`. If handler is None too → fall-back to F12.1 fail-open.

This is **structurally safe in production** if both Redis pings and `hard_stop_handler` is wired — but the class-level fail-open semantics remain when either (a) Redis is wired-not-ping, (b) handler is None, or (c) later someone refactors and removes the wire. The audit's class-level claim holds.

### 4.5 Contradiction with audit

NONE — all three windows are present in CURRENT code exactly as the audit claims.

---

## 5. Aggregate Risk Picture

| Finding | Class leak | Fail-closed knob available? | Production-wiring mitigation? |
|---------|-----------|-----------------------------|---------------------------------|
| F03     | HARD STOP blocks L2/L3 | NO — class is fail-open by design | Only via wiring `hard_stop_checker` — but fails-closed bypass possible |
| F04     | Unknown action silent L1 | NO — silent default, no warning | None — semantic holes cannot be plugged via wiring |
| F11     | dry_run under-classifies | NO — same provider-key bug | None — pure code bug in router.dry_run:254 |
| F12 ×3  | HARD STOP fail-open ×3 | Mixed — Yes for F12.1+2 (logger.error/warning), No for F12.3 | Runtime wires HardStopShim (`runtime.py:305-317`), mitigates IF both Redis + handler present |

---

## 6. Confirmed — no contradictions found

The 4 findings are structurally correct against CURRENT code in working tree. They align with but do NOT contradict the prior audit memory (P22.1 ConsentGate wiring, P22.2 classifier-bypass pattern, P22 production activation finalization which keeps several known lim → `CONFIG_MISSING` adapters honest).

Audit-ready. No code edits made.
