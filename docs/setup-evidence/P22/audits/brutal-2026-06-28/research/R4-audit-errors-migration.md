# P22 Brutal-Audit Research — Audit/Errors/Migration (Round 4)

**Date:** 2026-06-28
**Scope:** Read-only verification of findings F21, F22, F24, F25, F29, F32, F13 from the P22 brutal audit.
**Files inspected:**
- `src/life_integrations/audit.py` (300 lines)
- `src/life_integrations/audit_db_writer.py` (128 lines)
- `src/life_integrations/errors.py` (72 lines)
- `alembic/versions/p22_001_integration_schema.py` (167 lines)

---

## Per-Finding Verdicts

| #     | Finding                                                                  | Verdict | Headline                                                                                  |
|-------|--------------------------------------------------------------------------|---------|--------------------------------------------------------------------------------------------|
| F21   | Audit write failures are SILENT (no metric, no health signal)            | HOLDS   | `try/except Exception` swallows, logs `p22.audit_write_failed`, NO raise, NO metric/counter |
| F22   | `seed_last_hash()` returns `""` on error                                 | HOLDS   | Returns empty string `""` on BOTH empty result AND exception — silently starts fresh chain |
| F24   | `AuditChainVerificationError` defined but unused                         | PARTIAL | Defined is `ChainVerificationError` (NOT `Audit...`), but unused both; `verify_chain` returns bool, never raises |
| F25   | No UUID v7 (UUID v4 used for event_id)                                   | HOLDS   | `str(uuid.uuid4())` used in 2 `default_factory` (event_id, correlation_id)                  |
| F29   | `chain_version=2` hardcoded (no env override, no config)                 | HOLDS   | Hardcoded literal `2` in 3 places (docstring + INSERT SQL + schema DEFAULT)                  |
| F32   | No external signature (pure intra-chain SHA256)                          | HOLDS   | `hashlib.sha256(canonical + previous_hash)`; no Ed25519/RSA/Merkle/HMAC/timestamping       |
| F13   | TRUNCATE not in WORM contract; migration not idempotent in chain         | PARTIAL | TRUNCATE NOT revoked (only UPDATE, DELETE); BUT `down_revision` correctly chains; `IF NOT EXISTS` is idempotent for re-run |

---

## F21 — Audit write failures are SILENT

**Verdict:** HOLDS

**Citations:**
- `src/life_integrations/audit_db_writer.py:88-127` (write_event method)

**Verbatim excerpt** (`audit_db_writer.py:88-127`):
```python
        try:
            async with self._session_factory() as session:
                await session.execute(
                    sa_text(
                        "INSERT INTO audit.integration_api_log ("
                        "    event_id, occurred_at, actor_type, actor_id,"
                        "    integration_id, provider, action, tier,"
                        "    project_id, project_scope, result, correlation_id,"
                        "    metadata, previous_hash, event_hash, chain_version"
                        ") VALUES ("
                        "    :event_id, :occurred_at, :actor_type, :actor_id,"
                        "    :integration_id, :provider, :action, :tier,"
                        "    :project_id, NULL, :result, :correlation_id,"
                        "    CAST(:metadata AS jsonb), :previous_hash, :event_hash, 2"
                        ")"
                    ),
                    {
                        "event_id": event_id,
                        ...
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.error(
                "p22.audit_write_failed",
                event_id=event_dict.get("event_id", "<unknown>"),
                error=str(exc),
            )
```

The `try/except Exception` block at lines 88-127 swallows ALL exceptions, only emits `logger.error("p22.audit_write_failed")`, and returns `None` (never raises). This matches the documented "Never raises to caller" intent in line 63.

**No Prometheus counter / metric / health signal:** Grep across `src/life_integrations/` for `Counter`, `counter`, `prometheus`, `metric`, `p22_audit_write_failures` returned NO matches in `audit.py` or `audit_db_writer.py`. Failures are observable only via structlog logs (which requires log aggregation to human-monitoring). The only `metric` hits are in unrelated adapter files (`vps_adapter.py`, `onboarding_manifest.py` — health metrics, not audit).

**Contradiction vs brutal-audit claim:** NONE — claim HOLDS.

---

## F22 — `seed_last_hash()` returns "" on error

**Verdict:** HOLDS

**Citations:**
- `src/life_integrations/audit_db_writer.py:36-60`

**Verbatim excerpt** (`audit_db_writer.py:36-60`):
```python
    async def seed_last_hash(self) -> str:
        """Return the event_hash of the most recent row, or '' on empty/DB-error.

        Fail-open seed: an empty string starts a fresh chain, which is
        acceptable (pre-existing chain break from test-pollution rows is
        documented, not P22.1's to fix).
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    sa_text(
                        "SELECT event_hash FROM audit.integration_api_log "
                        "ORDER BY sequence DESC LIMIT 1"
                    )
                )
                row = result.first()
                if row and row[0]:
                    return str(row[0])
                return ""
        except Exception as exc:
            logger.error(
                "p22.audit_seed_failed",
                error=str(exc),
            )
            return ""
```

**Analysis:**
- Empty result → returns `""` (line 54).
- DB exception → returns `""` (line 60, after `except Exception as exc`).
- The docstring explicitly AVOWS this: "Fail-open seed: an empty string starts a fresh chain". This means an empty string can silently fork the chain from any previously persisting chain. If `seed_last_hash()` raises or fails-over to a fallback hash, the chain continues unbroken. Returning `""` IS the documented intent — there is no `None` sentinel, no `RuntimeError`, no distinct error signal.

**Note:** This is by design (fail-open), but the brutal-audit claim "an empty string silently starts a fresh chain" is technically CORRECT — the behavior is the same regardless of why `seed_last_hash()` returned empty.

**Contradiction vs brutal-audit claim:** NONE — claim HOLDS (the worst case = DB error → starts new chain; the normal case = empty result → also starts new chain).

---

## F24 — `AuditChainVerificationError` defined but unused

**Verdict:** PARTIAL — name is `ChainVerificationError` (no `Audit` prefix); both the wrong-named expected class AND the actually-defined class are unused; `verify_chain` returns bool.

**Citations:**
- `src/life_integrations/errors.py:70-71` (class definition)
- `src/life_integrations/audit.py:270-299` (verify_chain implementation)
- Grep for `AuditChainVerificationError` across `src/life_integrations/`: **NO MATCHES**
- Grep for `ChainVerificationError` across `src/life_integrations/`: **NO MATCHES** (defined but never raised/caught)

**Verbatim — errors.py:**
```python
class ChainVerificationError(IntegrationError):
    """Raised when audit chain verification fails (tamper detected)."""
```

**Verbatim — audit.py verify_chain (270-299):**
```python
    def verify_chain(self, events: list[AuditEvent]) -> bool:
        """Verify the integrity of an event chain.

        Args:
            events: List of AuditEvents to verify.

        Returns:
            True if all hashes are valid and chain is unbroken.
        """
        prev_hash = ""
        for event in events:
            if event.previous_hash != prev_hash:
                logger.error(
                    "audit.chain_broken",
                    event_id=event.event_id,
                    expected=prev_hash[:16],
                    got=event.previous_hash[:16],
                )
                return False
            computed = event.compute_hash()
            if computed != event.event_hash:
                logger.error(
                    "audit.hash_mismatch",
                    event_id=event.event_id,
                    expected=event.event_hash[:16],
                    got=computed[:16],
                )
                return False
            prev_hash = event.event_hash
        return True
```

**Analysis:**
- The actually defined class is `ChainVerificationError` (no `Audit` prefix).
- The brutal-audit claim text uses `AuditChainVerificationError` (with `Audit` prefix) — that exact name does NOT exist anywhere.
- Either way, NEITHER `ChainVerificationError` NOR `AuditChainVerificationError` is ever raised or caught in the entire `src/life_integrations/` tree.
- `verify_chain()` returns `bool` and uses `logger.error()` for tamper signals but does not raise.

**Contradiction vs brutal-audit claim:** PARTIAL — the claim is correct that the exception class is unused, but the developer must carefully read errors.py to see the actual class name is `ChainVerificationError`, not `AuditChainVerificationError`. This is a documentation/spec mismatch rather than a correctness bug.

---

## F25 — No UUID v7 (UUID v4 used)

**Verdict:** HOLDS — UUID v4 used everywhere; no UUID v7, no `gen_random_uuid` at the application level.

**Citations:**
- `src/life_integrations/audit.py:46` — `event_id` default_factory uses `str(uuid.uuid4())`
- `src/life_integrations/audit.py:58` — `correlation_id` default_factory uses `str(uuid.uuid4())`
- `src/life_integrations/audit.py:232` — lazy creation of `correlation_id` if None → `str(uuid.uuid4())`

**Verbatim excerpts:**
```
src\life_integrations\audit.py:46:    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
src\life_integrations\audit.py:58:    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
src\life_integrations\audit.py:232:            correlation_id=correlation_id or str(uuid.uuid4()),
```

Grep for `uuid4|uuid\.uuid4|gen_random_uuid|uuid7` across `src/life_integrations/`:
- `uuid.uuid4()` — 6 callsites (audit.py x3, project_context.py x1, runtime.py x1, tombstone.py x4)
- `gen_random_uuid()` — 1 callsite, only in `consent_ledger_writer.py` docstring (comment, not code)
- `uuid7` — **NO MATCHES**

Note: The DB schema (`alembic/versions/p22_001_integration_schema.py:38`) uses `DEFAULT gen_random_uuid()` for the `event_id` column at insert time. This is server-side fallback (pgaudit/pgcrypto extension); the application-side generate is universally UUID v4.

**Contradiction vs brutal-audit claim:** NONE — claim HOLDS.

---

## F29 — `chain_version=2` hardcoded

**Verdict:** HOLDS — hardcoded literal `2` in all 3 locations; no env var override; no config.

**Citations:**
- `src/life_integrations/audit_db_writer.py:9` — docstring `chain_version = 2`
- `src/life_integrations/audit_db_writer.py:96` — column list includes `chain_version`
- `src/life_integrations/audit_db_writer.py:101` — literal `2` in VALUES clause
- `alembic/versions/p22_001_integration_schema.py:54` — schema `DEFAULT 2`

**Verbatim excerpts:**
```
src\life_integrations\audit_db_writer.py:9:- chain_version = 2
src\life_integrations\audit_db_writer.py:96:                        "    metadata, previous_hash, event_hash, chain_version"
src\life_integrations\audit_db_writer.py:101:                        "    CAST(:metadata AS jsonb), :previous_hash, :event_hash, 2"
alembic\versions\p22_001_integration_schema.py:54:            chain_version       SMALLINT NOT NULL DEFAULT 2
```

Grep `chain_version` across `src/life_integrations/`: only matches are in `audit_db_writer.py` (above). No `os.getenv`, `settings.chain_version`, `ChainVersionConfig`, etc. — the value `2` is a magic literal.

**Contradiction vs brutal-audit claim:** NONE — claim HOLDS. Promoting `2` to schema named-constant `AUDIT_CHAIN_VERSION = 2` would only be DEFENSIBLE rename, not a fix.

---

## F32 — No external signature

**Verdict:** HOLDS — pure intra-chain SHA256 only; no Ed25519, RSA, Merkle, HMAC, or external timestamping.

**Citations:**
- `src/life_integrations/audit.py:14` — `import hashlib`
- `src/life_integrations/audit.py:63-87` — `compute_hash()` method
- `src/life_integrations/audit.py:85-87` — SHA256 call

**Verbatim excerpt — compute_hash (audit.py:63-87):**
```python
    def compute_hash(self) -> str:
        """Compute SHA256 hash of canonical payload.

        Returns:
            Hex digest of SHA256(canonical_payload + previous_hash).
        """
        payload = {
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "integration_id": self.integration_id,
            "provider": self.provider,
            "action": self.action,
            "tier": self.tier,
            "project_id": self.project_id,
            "result": self.result,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(
            f"{canonical}{self.previous_hash}".encode()
        ).hexdigest()
```

**Analysis:**
- Hash inputs: 13 payload fields + `previous_hash`, all JSON-stringified with `sort_keys=True`.
- Algorithm: `hashlib.sha256` (NIST SHA-2 256-bit).
- No Ed25519/RSA keypair signatures, no Merkle proofs, no external timestamping authority, no signed-chain anchor published to an external witness.
- The chain is intra-system only. An attacker who compromises the host (or the DB role) can rewrite `previous_hash` to fork the chain without the system noticing.

Grep `Ed25519|RSA|Merkle|timestamping|HMAC|sign`: NO relevant matches in audit code. The only `sign`/`signature` matches are unrelated HTTP/signoff language in adapter files.

**Contradiction vs brutal-audit claim:** NONE — claim HOLDS.

---

## F13 — TRUNCATE not in WORM contract

**Verdict:** PARTIAL — TRUNCATE is NOT revoked, but the migration is idempotent and correctly chained; only UPDATE/DELETE revoked from application role; TRUNCATE is implicitly only available to superuser.

**Citations:**
- `alembic/versions/p22_001_integration_schema.py:23-26` — revision chain metadata
- `alembic/versions/p22_001_integration_schema.py:78-83` — REVOKE/GRANT statements
- `alembic/versions/p22_001_integration_schema.py:35-56` — table CREATE (idempotent guards)

**Verbatim — REVOKE/GRANT (78-83):**
```python
    # WORM enforcement: revoke UPDATE/DELETE from application role
    op.execute("""
        REVOKE UPDATE, DELETE ON audit.integration_api_log FROM guinevere_core;
    """)
    op.execute("""
        GRANT INSERT, SELECT ON audit.integration_api_log TO guinevere_core;
    """)
```

**Verbatim — migration header (23-26):**
```python
revision: str = "p22_001_integration_schema"
down_revision: Union[str, Sequence[str], None] = "p19_003_audit_chain_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Verbatim — idempotent CREATE (35-56):**
```python
    # 1. audit.integration_api_log — hash-chained WORM table
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit.integration_api_log (
            id                  BIGSERIAL PRIMARY KEY,
            event_id            UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
            ...
            chain_version       SMALLINT NOT NULL DEFAULT 2
        );
    """)
```

**Analysis:**
- TRUNCATE is NOT explicitly revoked. By default, TRUNCATE in PostgreSQL requires either table ownership or explicit grant. Since the migration explicitly REVOKEs UPDATE/DELETE and GRANTs only INSERT/SELECT, `TRUNCATE` is not in the granted set for `guinevere_core`. However, this is INDIRECT defense — TRUNCATE will still work for the migration owner (alembic su) and any role with `TRUNCATE` grant or table ownership.
- Comment on lines 77 documents the WORM contract intent: `# WORM enforcement: revoke UPDATE/DELETE from application role`.
- Migration IS idempotent for CREATE (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `CREATE SCHEMA IF NOT EXISTS`).
- Migration correctly chains: `down_revision = "p19_003_audit_chain_version"` (line 24) — that file exists.
- The INSERT `ON CONFLICT (integration_id) DO NOTHING` on lines 138-153 is also idempotent.
- `downgrade()` drops tables but does NOT `IF EXISTS`-guard the audit table (line 165 just `DROP TABLE IF EXISTS audit.integration_api_log;`) — actually it's guarded. Fine.

**Contradiction vs brutal-audit claim:** PARTIAL — TRUNCATE is not in the explicit REVOKE list, but it is implicitly inaccessible to the application role (`guinevere_core` was only GRANTed INSERT/SELECT). The migration IS idempotent in the upgrade direction and correctly chains via `down_revision = "p19_003_audit_chain_version"`. To make the WORM contract airtight, the brutal-audit fix should add explicit `REVOKE TRUNCATE`.

---

## Cross-Finding Observations

1. **`compute_hash` is auditable but not externally verifiable** — F29 + F32 + F21 combine: a fail-silent writer that swallows errors + a hardcoded chain_version + no external signature = chain can be silently broken from inside the system without detection.

2. **`verify_chain` never raises** — F24 confirms `verify_chain` returns bool; combined with `ChainVerificationError` being defined-but-unused, ANY consumer that wants exception-based error handling must implement it on top of the bool return.

3. **Empty string is overloaded across three failure modes** — `seed_last_hash()` returns `""` on (a) empty table, (b) DB error, (c) successful chain tail but `row[0]` is None/empty. F22. Three semantics, one return value, no `Optional[str]` or distinct error signal.

4. **Self-correcting schema** — `gen_random_uuid()` DEFAULT on event_id means even if the application generates an invalid UUID, the DB will substitute one. This DIMINISHES the impact of F25 (UUID v4 vs v7) at the application layer — the v4-vs-v7 critique is about sortable timestamp, not correctness.

5. **Operator-friendly migration** — The migration deduces chain_version (`DEFAULT 2`) so application code's hardcoded `2` is at least consistent with schema default.

---

## Files Cited (absolute paths)

- `C:\Users\faizz\guinevere\src\life_integrations\audit.py`
- `C:\Users\faizz\guinevere\src\life_integrations\audit_db_writer.py`
- `C:\Users\faizz\guinevere\src\life_integrations\errors.py`
- `C:\Users\faizz\guinevere\alembic\versions\p22_001_integration_schema.py`
- `C:\Users\faizz\guinevere\alembic\versions\p19_003_audit_chain_version.py` (down_revision target — exists)

**End of report.**
