# Step 12 Routing Auditor Gate

**VERDICT: PASS**

## Scope

Parent-run independent audit of Phase 6 LLM routing correctness after sub-agent auditor infrastructure failed and Faiz explicitly instructed: `audit mandiri, jangan pake sub agent`.

## Files / Evidence Reviewed

- `src/core/services/llm_router.py`
- `hermes-config/config.yaml`
- `monitoring/prometheus/prometheus.yml`
- `docs/setup-evidence/phase-6/plan.md`
- `docs/setup-evidence/phase-6/STEP-6/verification.md`
- `docs/setup-evidence/phase-6/STEP-8/verification.md`
- `docs/setup-evidence/phase-6/STEP-9/verification.md`
- `docs/setup-evidence/phase-6/STEP-10/implementation-report.md`
- VPS read-only verification through SSH: service status, model inventory, Hermes config, metrics endpoint.

## Checks Performed

| Check | Evidence | Result |
|---|---|---|
| Primary model is DeepSeek through 9Router | `llm_router.py` `MODELS[CORE_REASONING]`; VPS config `model ninerouter http://localhost:20128/v1 ds/deepseek-v4-flash` | PASS |
| All router model URLs use 9Router localhost | `llm_router.py` all `base_url` values are `http://localhost:20128/v1` | PASS |
| No direct provider endpoint in routing/config surfaces | Targeted grep; false positives outside Phase 6/changed scope documented separately | PASS |
| Fallback chain has two 9Router-local entries | Local/VPS config: `cx/gpt-5.5`, `guinevere`, both `http://localhost:20128/v1` | PASS |
| Invalid `ninerouter/balance` excluded | STEP-6 proves model absent and not configured | PASS |
| SSE marker stripping handles spaced/unspaced variants | `_SSE_DONE_RE = re.compile(r"data:\s*\[DONE\]\s*$")`; router tests cover both variants | PASS |
| 100-prompt VPS test succeeds | STEP-9: 100/100 success, 0 SSE artifacts, 0 direct provider calls | PASS |
| Runtime services active | VPS: `hermes-gateway` active, `guinevere-core` active | PASS |
| 9Router model inventory OK | VPS `/v1/models`: `ds/deepseek-v4-flash`, `cx/gpt-5.5`, `guinevere` all present | PASS |
| Prometheus routing metrics present | VPS `localhost:9191/metrics` contains all four required metric families | PASS |

## Findings

1. Routing is constrained to 9Router at `http://localhost:20128/v1` in both source and runtime config.
2. Phase 6 primary is correctly set to `ds/deepseek-v4-flash`.
3. The configured runtime fallback chain is exactly two 9Router-local fallback entries: `cx/gpt-5.5` and `guinevere`.
4. `cx/gpt-5.5` is documented as degraded due expired Codex credentials, but it is present in 9Router model inventory and followed by operational `guinevere`.
5. `ninerouter/balance` is absent and not configured, matching the planner conflict resolution.
6. SSE `[DONE]` artifact handling is covered by unit tests and the 100-prompt test reported zero parsed artifacts.
7. Metrics endpoint is present and exposes required families.

## Caveats

- The 100-prompt run did not activate fallback because all 100 calls succeeded on primary DeepSeek. Fallback configuration and model inventory were verified, but live fallback activation remains a credential/state-dependent scenario.
- Global repository grep reports pre-existing direct-provider mentions in historical docs (`fixes/`, `stepprompts/`) outside Phase 6 changed runtime surfaces. They are not active routing paths.

## Verdict

**VERDICT: PASS** — Phase 6 LLM routing correctness is sufficiently evidenced for the required gate.
