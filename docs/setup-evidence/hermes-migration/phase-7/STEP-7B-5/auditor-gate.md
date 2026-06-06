# Step 7b.5 — Hermes Monitoring Config Files — Auditor Gate

**Status**: PENDING AUDIT

**Auditor Scope**: Security Posture and Blocker Honesty (A2)

**Scoped Files**:
- `monitoring/prometheus/prometheus.yml`
- `monitoring/prometheus/rules/guinevere-alerts.yml`
- `monitoring/grafana/dashboards/guinevere-hermes.json`
- `monitoring/alertmanager/alertmanager.yml`
- `monitoring/promtail/promtail-config.yml`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/verification.md`

**Checklist**:
- [ ] Prometheus scrape job uses canonical `job_name: "hermes"` (not `hermes-llm-routing`)
- [ ] Target is `host.docker.internal:9191` (not `localhost:9191`)
- [ ] Instance relabel to `hermes-gateway` present
- [ ] 6 `GuinevereHermes*` alert rules present with runbook annotations
- [ ] Dashboard JSON parses as valid JSON
- [ ] Dashboard panels cover: gateway status, LLM calls, latency, cost, safety/pending instrumentation
- [ ] Alertmanager Hermes routes present and non-breaking
- [ ] Promtail regex matches `hermes-gateway.service`
- [ ] No `job_name: "hermes-llm-routing"` remains
- [ ] No claim of live deployment verification
- [ ] All scaffold commands from plan §6.5 pass
- [ ] Boundary compliance: no persona/surveillance/secret violations

**Auditor Verdict**: *To be filled after audit execution*
