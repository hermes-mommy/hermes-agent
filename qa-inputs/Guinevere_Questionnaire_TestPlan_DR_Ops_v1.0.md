# Guinevere Questionnaire — Test Plan, Disaster Recovery Plan & Internal Ops Manual

> **Version**: 1.0  
> **Date**: 2026-05-30  
> **Status**: Draft — Awaiting Operator Response  
> **Author**: Guinevere (Hephaestus discipline)  
> **Total Questions**: 236  
> **Format**: Multiple Choice (A/B/C/D) — ★ = rekomendasi Guinevere

---

## Cara Menjawab

1. Jawab setiap pertanyaan dengan huruf pilihan: `A`, `B`, `C`, atau `D`.
2. Jika tidak yakin, tulis `skip` — Guinevere akan menggunakan default (★).
3. Boleh menjawab per-bagian, misalnya: `TP-A: 1A 2B 3C ...`
4. Jawaban boleh diberikan dalam beberapa batch.
5. Setelah semua jawaban diterima, Guinevere akan generate 3 dokumen + 9 research reports + 3 audit reports.

**Format jawaban yang diharapkan:**
```
BAGIAN 1 — TEST PLAN (TP)
TP-A: 1A 2B 3★ 4C 5A 6B 7★ 8A 9D 10B
TP-B: 11A 12B 13C 14★ 15A ...
...

BAGIAN 2 — DISASTER RECOVERY PLAN (DR)
DR-A: 1A 2B 3★ 4C ...
...

BAGIAN 3 — INTERNAL OPS MANUAL (OPS)
OPS-A: 1A 2B 3★ 4C ...
...
```

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_SRS_v1.0.md` | Sumber requirements (FR-001–FR-120, NFR-001–NFR-050) |
| `Guinevere_FSD_v1.0.md` | Functional specs (Persona, Discord, Surveillance) |
| `Guinevere_TDD_Guide_v1.0.md` | Test pyramid, framework, coverage targets |
| `Guinevere_AgentLoopSpec_v2.0.md` | 7-phase SDLC loop, loop types, guardian |
| `Guinevere_DatabaseERD_MigrationStrategy_v1.0.md` | 12 schemas, hypertables, HNSW, Merkle audit |
| `Guinevere_Deployment_Guide_v1.0.md` | 17 services, systemd, Docker, resource allocation |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | SEV0–SEV4, 10 runbooks, chain of custody |
| `Guinevere_ObservabilityAlertingSpec_v1.0.md` | Prometheus/Grafana/Loki/Sentry, 20 alert rules |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | 99.5% SLO, burn-rate alerts, freeze policy |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | 13 principals, 12 roles, break-glass |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Safe-word, yandere Y0–Y6, 15 forbidden patterns |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | 5 tiers, retention, double encryption |
| `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | 56 ACs, safety zero-tolerance, gap register |
| `Guinevere_Security_Policy_v1.0.md` | 7-layer defense, STRIDE, OWASP Agentic Top 10 |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | $30/month budget, model routing, anomaly thresholds |
| `adr/ADR-Index.md` | 29 ADRs (15 Accepted, 14 Accepted with notes) |

---

# ═══════════════════════════════════════════════
# BAGIAN 1 — TEST PLAN (TP) — 78 Pertanyaan
# ═══════════════════════════════════════════════

## TP-A: Test Strategy & Governance (Q1–Q12)

**TP-Q1.** Apa overall test strategy yang harus digunakan Guinevere?
- A. ★ Risk-Based Testing — prioritas berdasarkan risk matrix dari Security Policy STRIDE analysis
- B. Requirements-Based Testing — trace 1:1 dari SRS FR-001–FR-120
- C. Hybrid: Risk-Based + Requirements-Based — combine keduanya
- D. Exploratory-First — exploratory testing dulu, formalize kemudian

**TP-Q2.** Siapa yang bertanggung jawab approving test plan sebelum execution?
- A. Guinevere autonomous — self-approve dan execute
- B. ★ Samm — operator approval required sebelum test execution wave dimulai
- C. Sub-agent auditor — automated approval oleh auditor agent
- D. Dual approval — Guinevere propose, Samm approve untuk P0–P2, auto-approve P3–P5

**TP-Q3.** Berapa frekuensi full regression test suite harus dijalankan?
- A. Setiap commit di main branch
- B. ★ Setiap malam (02:00 WIB) + setiap release
- C. Setiap minggu (Senin 01:00 WIB)
- D. Setiap sprint (2 minggu sekali)

**TP-Q4.** Bagaimana test results harus di-report ke Samm?
- A. Hanya failures yang di-report via Discord
- B. ★ Full report: summary di Discord, detail di `evidence/tests/<YYYY-MM-DD>/` + Grafana dashboard
- C. Weekly digest setiap Senin pagi
- D. Real-time streaming ke Discord channel #test-results

**TP-Q5.** Apa test data strategy yang harus digunakan?
- A. Production data clone — gunakan data production asli untuk realism
- B. ★ Synthetic data generators — generate test data yang representative tanpa PII risk
- C. Anonymized production data — production data yang sudah di-redact
- D. Hybrid: synthetic untuk unit/integration, anonymized untuk E2E

**TP-Q6.** Bagaimana test environment isolation harus diimplementasi?
- A. Separate VPS untuk testing — dedicated test server
- B. ★ Docker Compose test profile — isolated containers di VPS yang sama dengan resource limits
- C. Kubernetes namespaces — terlalu complex untuk single-VPS
- D. In-process mocking — mock semua external dependencies

**TP-Q7.** Apa policy untuk test yang flaky (intermittent failures)?
- A. Auto-retry 3x, report sebagai pass jika salah satu pass
- B. ★ Auto-quarantine setelah 3 failures, ticket otomatis untuk investigation, exclude dari pass rate
- C. Mark sebagai known-flaky dan ignore
- D. Fail the build jika ada flaky test

**TP-Q8.** Bagaimana test traceability ke requirements harus diimplementasi?
- A. Manual mapping di test docstring
- B. ★ pytest markers dengan requirement ID (e.g., `@pytest.mark.srs_fr_001`) + automated traceability report
- C. Separate traceability spreadsheet
- D. Tag-based di test filename convention

**TP-Q9.** Apa test gating policy untuk deployment ke production?
- A. All tests must pass (100%)
- B. ★ P0–P2 must pass, P3–P5 may have known failures documented
- C. >95% pass rate cukup
- D. Only smoke tests required for deployment gate

**TP-Q10.** Bagaimana test untuk third-party API integration (9Router, OpenRouter, Brave, Gmail)?
- A. Selalu hit production API — real integration test
- B. ★ VCR.py recordings + contract tests — record sekali, replay deterministic, contract validate schema
- C. Full mock — mock semua response
- D. Staging environment dari vendor

**TP-Q11.** Apa mutation testing strategy untuk mengukur test quality?
- A. Skip mutation testing — terlalu resource-intensive
- B. ★ mutmut pada P0–P1 modules only (safety, memory encryption, agent loop) — target 60% mutation score
- C. Full mutation testing pada semua modules — target 80% score
- D. Manual code review sebagai pengganti mutation testing

**TP-Q12.** Bagaimana test untuk Guinevere's autonomous SDLC loop sendiri?
- A. Tidak perlu test — loop adalah internal mechanism
- B. Unit test untuk phase transitions saja
- C. ★ Full integration test: mock sub-agents, simulate 7-phase loop, verify state machine, evidence generation, dan rollback
- D. Observability-only — monitor di production, fix jika ada masalah

---

## TP-B: Test Framework & Tooling (Q13–Q22)

**TP-Q13.** Apa primary test runner yang harus digunakan?
- A. unittest (stdlib)
- B. ★ pytest 8.x dengan pytest-asyncio untuk async test
- C. nose2
- D. tox sebagai test orchestrator

**TP-Q14.** Apa HTTP client library untuk API integration testing?
- A. requests
- B. ★ httpx (async-capable, mendukung HTTP/2)
- C. aiohttp
- D. urllib3

**TP-Q15.** Apa API contract/fuzz testing tool?
- A. Postman/Newman
- B. ★ schemathesis (property-based API fuzzing dari OpenAPI spec)
- C. Dredd
- D. Custom fuzz scripts

**TP-Q16.** Apa browser/E2E testing framework?
- A. Selenium WebDriver
- B. ★ Playwright (sesuai dengan obscura+Playwright surveillance stack)
- C. Cypress
- D. Puppeteer via subprocess

**TP-Q17.** Apa performance/load testing tool?
- A. Apache JMeter
- B. ★ locust (Python-native, scriptable, cocok untuk single-VPS)
- C. k6
- D. artillery

**TP-Q18.** Apa benchmarking tool untuk critical paths?
- A. timeit module saja
- B. ★ pytest-benchmark (integrasi native dengan pytest, JSON output)
- C. py-spy profiling
- D. cProfile manual

**TP-Q19.** Apa static analysis dan linting tools?
- A. pylint saja
- B. ★ ruff (linter+formatter) + mypy (type checking) + bandit (security linting)
- C. flake8 + black + mypy
- D. SonarQube self-hosted

**TP-Q20.** Apa test coverage measurement tool?
- A. coverage.py saja
- B. ★ coverage.py + pytest-cov + diff-cover (untuk PR-level coverage reporting)
- C. Codecov SaaS
- D. Coveralls

**TP-Q21.** Bagaimana test dependency management (fixtures, factories)?
- A. Inline test data di setiap test file
- B. ★ Shared conftest.py hierarchy: root conftest → component conftest, factory_boy untuk model factories
- C. External test data files (JSON/YAML)
- D. Database seeds via Alembic

**TP-Q22.** Apa CI/CD integration strategy untuk test execution?
- A. GitHub Actions (free tier untuk private repos)
- B. ★ Self-hosted runner di VPS yang sama via systemd timer (02:00 WIB) + GitHub webhook trigger
- C. Jenkins self-hosted
- D. GitLab CI

---

## TP-C: Test Pyramid & Coverage Targets (Q23–Q32)

**TP-Q23.** TDD Guide menetapkan test pyramid Unit 55%, Integration 25%, Contract 17%, E2E 13%. Apakah distribution ini final?
- A. ★ Ya, ikuti TDD Guide persis — 55/25/17/13
- B. Adjust: Unit 60%, Integration 20%, Contract 12%, E2E 8%
- C. Adjust: Unit 45%, Integration 30%, Contract 15%, E2E 10%
- D. Biarkan Guinevere decide berdasarkan risk assessment

**TP-Q24.** TDD Guide menetapkan target 600+ total tests. Apakah ini target MVP atau production?
- A. MVP target — 600 tests saat MVP launch
- B. ★ Production target — 600+ saat production-ready, MVP bisa 300+ dengan P0–P2 coverage
- C. Stretch goal — aim for 600 tapi 400 sudah acceptable
- D. 800+ — lebih banyak lebih baik

**TP-Q25.** Line coverage minimum dari TDD Guide adalah 80%. Apakah ini adequate?
- A. ★ Ya, 80% line + 70% branch sesuai TDD Guide
- B. Naikkan ke 90% line + 80% branch
- C. Turunkan ke 70% line + 60% branch untuk MVP
- D. Per-component targets: Safety 95%, Memory 90%, API 80%, UI 60%

**TP-Q26.** Bagaimana coverage harus di-enforce?
- A. Hard gate — CI fail jika di bawah threshold
- B. ★ Soft gate — CI warn + automatic ticket jika di bawah threshold, hard gate hanya untuk P0 modules
- C. Report only — tidak ada enforcement
- D. Progressive — mulai 60%, naik 5% per bulan sampai target

**TP-Q27.** Component mana yang harus mendapat coverage tertinggi?
- A. Agent Loop — karena paling complex
- B. ★ Safety/Security modules (safe-word, encryption, forbidden patterns) — zero-tolerance
- C. Memory system — karena menyimpan sensitive data
- D. Semua component sama — flat 80%

**TP-Q28.** Apakah code coverage untuk test code sendiri perlu di-measure?
- A. Ya, test code juga harus di-cover
- B. ★ Tidak, tapi test quality di-measure via mutation testing (TP-Q11)
- C. Ya, tapi target lebih rendah (60%)
- D. Only untuk shared test utilities

**TP-Q29.** Apa strategy untuk test code quality dan maintenance?
- A. Test code = production code — same standards
- B. ★ Test code follows ARR pattern (Arrange-Act-Assert), max 30 lines per test, descriptive names
- C. Minimal standards — yang penting test works
- D. BDD-style (Given-When-Then) dengan behave library

**TP-Q30.** Bagaimana test untuk asynchronous code (FastAPI endpoints, agent loop)?
- A. Synchronous wrappers — wrap async ke sync
- B. ★ pytest-asyncio native + anyio backend + proper event loop isolation per test
- C. trio testing framework
- D. Manual event loop management

**TP-Q31.** Apa strategy untuk test database interactions?
- A. Mock semua database calls
- B. ★ PostgreSQL test container (Docker) + Alembic migration + transaction rollback per test
- C. SQLite in-memory untuk testing
- D. Shared test database dengan cleanup scripts

**TP-Q32.** Apa strategy untuk test Redis interactions?
- A. Mock semua Redis calls
- B. ★ Redis test container (Docker) + dedicated test DB number + flush per test
- C. fakeredis library
- D. Shared Redis instance dengan namespace isolation

---

## TP-D: Unit Testing (Q33–Q44)

**TP-Q33.** Bagaimana MoodFSM (Persona Engine) harus di-test?
- A. Test setiap mood individually
- B. ★ Test semua valid transitions, invalid transitions (expect rejection), dan edge cases (rapid mood changes, conflicting triggers)
- C. Integration test saja — unit test tidak cukup untuk FSM
- D. Property-based testing saja

**TP-Q34.** Bagaimana MemoryStore encryption harus di-test?
- A. Verify encrypted output != plaintext
- B. ★ Test encrypt→decrypt round-trip, verify ciphertext format, test key rotation, test double encryption for Critical tier, test with invalid keys
- C. Visual inspection of encrypted values
- D. Only integration test with real database

**TP-Q35.** Bagaimana RecallPipeline (semantic search + reranking) harus di-test?
- A. Test dengan sample queries saja
- B. ★ Unit test: embedding generation, similarity scoring, reranking logic, deduplication. Benchmark test: latency <200ms p95
- C. Only end-to-end test dengan real queries
- D. Mock embedding model, test logic saja

**TP-Q36.** Bagaimana SDLCPhase state machine (7 phases) harus di-test?
- A. Test setiap phase individually
- B. ★ Test valid forward transitions, invalid backward transitions, skip transitions, interrupt handling, dan phase-specific side effects
- C. Integration test only — state machine terlalu coupled
- D. Model checking dengan TLA+

**TP-Q37.** Bagaimana safe-word detection (PersonaSafetyPolicy F-01) harus di-test?
- A. Test dengan exact match saja
- B. ★ Test exact match, semantic variants, obfuscated variants (l33t speak, unicode), multi-language, case-insensitive, embedded in longer text
- C. Manual testing oleh Samm
- D. Only integration test

**TP-Q38.** Bagaimana yandere scale enforcement (Y0–Y6) harus di-test?
- A. Test setiap level individually
- B. ★ Test level boundaries, escalation triggers, de-escalation, Y6 absolute prohibition (100% block), dan drift detection
- C. Integration test saja
- D. Sampling-based testing — test random levels

**TP-Q39.** Bagaimana hash-anchored edit format (AgentLoopSpec) harus di-test?
- A. Test hash computation saja
- B. ★ Test hash generation, hash verification, tamper detection, rollback via hash chain, dan Merkle integrity
- C. Only visual inspection
- D. Property-based testing saja

**TP-Q40.** Bagaimana priority scoring (client_revenue*0.3 + deadline_urgency*0.4 + samm_explicit*0.2 + guinevere_judgment*0.1) harus di-test?
- A. Test dengan sample values saja
- B. ★ Test all weight combinations, edge cases (all zeros, all max, single factor dominant), dan tie-breaking
- C. Integration test only
- D. Manual calculation verification

**TP-Q41.** Bagaimana forbidden patterns (F-01 sampai F-15) harus di-test?
- A. Test 2–3 representative patterns
- B. ★ Test SEMUA 15 patterns individually + combined patterns + adversarial bypass attempts
- C. Sampling — test 5 patterns per quarter rotation
- D. Only integration test

**TP-Q42.** Bagaimana TimescaleDB hypertable operations harus di-test?
- A. Mock hypertable sebagai regular table
- B. ★ Test chunk creation (7-day memory, 1-day surveillance), retention policy execution, continuous aggregates, dan query performance on chunked data
- C. Only production monitoring
- D. Unit test SQL generation saja

**TP-Q43.** Bagaimana PgBouncer connection pooling harus di-test?
- A. Skip — PgBouncer sudah well-tested upstream
- B. ★ Test connection limits (max 200), pool exhaustion behavior, transaction vs session mode, dan failover
- C. Only load test
- D. Configuration validation saja

**TP-Q44.** Bagaimana SOPS+age encryption/decryption harus di-test?
- A. Test encrypt/decrypt round-trip saja
- B. ★ Test round-trip, key rotation, missing key error handling, corrupted file handling, per-service .env.sops isolation
- C. Integration test only
- D. Manual verification

---

## TP-E: Integration Testing (Q45–Q54)

**TP-Q45.** Bagaimana PostgreSQL integration harus di-test?
- A. SQLite in-memory
- B. ★ Docker PostgreSQL 16 container + test database + Alembic migrations + transaction rollback fixture
- C. Shared PostgreSQL dengan schema isolation
- D. Only production database

**TP-Q46.** Bagaimana Redis integration harus di-test?
- A. fakeredis library
- B. ★ Docker Redis 7 container + dedicated test DB number (DB 15) + flush fixture
- C. Shared Redis dengan key prefix isolation
- D. Mock Redis calls

**TP-Q47.** Bagaimana LLM gateway (9Router/OpenRouter) integration harus di-test?
- A. Always hit real API
- B. ★ VCR.py recordings untuk deterministic tests + contract tests untuk schema validation + circuit breaker test
- C. Full mock semua responses
- D. Only manual testing

**TP-Q48.** Bagaimana Discord bot integration harus di-test?
- A. Connect ke real Discord server
- B. ★ Mock Discord.py gateway + test slash command handlers, webhook delivery, message formatting, rate limit handling
- C. Dedicated test Discord server
- D. Screenshot comparison testing

**TP-Q49.** Bagaimana WhatsApp (Baileys) integration harus di-test?
- A. Connect ke real WhatsApp
- B. ★ Mock Baileys bridge + test message handlers, media processing, reconnection logic, session management
- C. Dedicated test WhatsApp number
- D. Only manual testing

**TP-Q50.** Bagaimana surveillance FastAPI endpoints harus di-test?
- A. curl commands saja
- B. ★ httpx TestClient + auth (HMAC-SHA256/JWT) + test semua CRUD endpoints, WebSocket connections, dan error responses
- C. Postman collection
- D. Only production monitoring

**TP-Q51.** Bagaimana Gmail API integration harus di-test?
- A. Use real Gmail account
- B. ★ Mock OAuth2 flow + test email parsing, Pub/Sub watch handling, attachment processing, dan rate limit handling
- C. Dedicated test Gmail account
- D. Screenshot testing

**TP-Q52.** Bagaimana GitHub MCP integration harus di-test?
- A. Use real GitHub repos
- B. ★ Mock GitHub REST + GraphQL + test webhook HMAC-SHA256 verification, PR operations, issue operations
- C. Dedicated test GitHub org
- D. Only manual testing

**TP-Q53.** Bagaimana cross-service integration harus di-test?
- A. Test setiap service pair individually
- B. ★ Docker Compose test profile: spin up all services, test critical flows (memory write→recall, surveillance→storage, agent loop→sub-agent→evidence)
- C. Only end-to-end tests
- D. Contract tests between services

**TP-Q54.** Bagaimana database migration testing harus dilakukan?
- A. Run migrations di production langsung
- B. ★ Test forward migration, rollback migration, data integrity post-migration, dan migration idempotency pada test DB
- C. Manual verification saja
- D. Only forward migration test, skip rollback

---

## TP-F: E2E, Contract & Smoke Testing (Q55–Q60)

**TP-Q55.** Apa scope E2E testing untuk MVP?
- A. Full user journey dari Discord command → agent response
- B. ★ Critical paths only: safe-word activation, memory recall, surveillance ingestion, agent loop completion, cost tracking
- C. Semua 56 acceptance criteria dari AcceptanceCriteriaCatalog
- D. Tidak ada E2E testing untuk MVP

**TP-Q56.** Bagaimana contract testing untuk FastAPI endpoints?
- A. Manual Postman testing
- B. ★ schemathesis fuzz testing dari OpenAPI spec + response schema validation + error response contract
- C. Unit tests saja sudah cukup
- D. Only integration tests

**TP-Q57.** Apa smoke test suite yang harus dijalankan post-deployment?
- A. Single ping test
- B. ★ 10 critical smoke tests: API health, DB connectivity, Redis connectivity, LLM gateway reachability, safe-word activation, Discord bot online, memory write/read, surveillance endpoint, cost tracker, auth
- C. Full regression suite
- D. Manual verification oleh Samm

**TP-Q58.** Bagaimana Playwright E2E test harus di-organize?
- A. Single monolithic test file
- B. ★ Per-feature test files: persona, memory, surveillance, discord, dashboard + shared page objects + test fixtures
- C. Record-and-replay saja
- D. Only screenshot comparison

**TP-Q59.** Apa timeout policy untuk E2E tests?
- A. No timeout — biarkan sampai selesai
- B. ★ 30s per test, 5min total suite, auto-fail dengan screenshot + logs on timeout
- C. 60s per test, no suite limit
- D. 10s per test, fail fast

**TP-Q60.** Bagaimana E2E test data cleanup?
- A. Manual cleanup setelah test
- B. ★ Automated teardown: database transaction rollback, Redis flush, file cleanup, mock external service reset
- C. Dedicated test database yang di-drop setiap run
- D. Tidak perlu cleanup — test data tidak interfere

---

## TP-G: Performance & Load Testing (Q61–Q66)

**TP-Q61.** Apa baseline performance targets?
- A. Response time <1s untuk semua endpoints
- B. ★ API p95 <200ms, memory recall p95 <500ms, agent loop phase transition <2s, LLM gateway p95 <3s (external dependency)
- C. Response time <500ms untuk semua endpoints
- D. Tidak ada explicit targets — monitor dan optimize

**TP-Q62.** Bagaimana load testing harus dilakukan pada single VPS (4C/16GB)?
- A. Simulate 100 concurrent users
- B. ★ Simulate realistic load: 1 user (Samm) + 20 parallel agent loops + surveillance event burst (100 events/min)
- C. Stress test sampai VPS crash
- D. Only unit-level benchmark

**TP-Q63.** Apa database performance testing strategy?
- A. pgbench standard benchmark saja
- B. ★ pgbench + custom workload: HNSW search latency, hypertable chunk scan, Merkle chain write throughput, connection pool saturation
- C. Only query EXPLAIN ANALYZE
- D. Production monitoring saja

**TP-Q64.** Bagaimana memory leak testing harus dilakukan?
- A. Manual monitoring
- B. ★ pytest-benchmark + tracemalloc snapshots per test phase + automated regression detection (>10% growth = fail)
- C. Only production monitoring dengan Prometheus
- D. Skip — Python GC handles it

**TP-Q65.** Apa strategy untuk LLM latency testing?
- A. Tidak bisa test — external dependency
- B. ★ Measure time-to-first-token (TTFT) dan total response time per model (GPT-5.5, DeepSeek V4, Ollama), test circuit breaker behavior, fallback latency
- C. Only production monitoring
- D. Mock responses saja

**TP-Q66.** Bagaimana startup time testing harus dilakukan?
- A. Tidak perlu — daemon selalu running
- B. ★ Measure cold start: service startup time, database connection pool warmup, Redis connection, model loading (Ollama), dan first-request latency
- C. Only production observation
- D. Manual timing

---

## TP-H: Security & Penetration Testing (Q67–Q74)

**TP-Q67.** Apa scope security testing?
- A. OWASP Top 10 web testing saja
- B. ★ OWASP Agentic Top 10 (ASI01–ASI10) + STRIDE per-component (12 components) + KILLSWITCH framework + custom agentic-specific tests
- C. Network penetration testing saja
- D. Code review saja

**TP-Q68.** Bagaimana prompt injection testing harus dilakukan?
- A. Manual testing dengan known injection patterns
- B. ★ Automated test suite: 50+ injection patterns (direct, indirect, multi-turn, jailbreak, encoding bypass) × 4 defense layers dari Security Policy
- C. External penetration testing service
- D. Sampling 10 patterns per quarter

**TP-Q69.** Bagaimana secrets management testing harus dilakukan?
- A. Verify .env.sops files exist
- B. ★ Test: no plaintext secrets in repo (git-secrets pre-commit), SOPS decrypt works, age key rotation, missing key error handling, secret access logging
- C. Manual audit saja
- D. Only configuration validation

**TP-Q70.** Bagaimana authentication/authorization testing harus dilakukan?
- A. Test login saja
- B. ★ Test: all 13 principals' permissions, RBAC role enforcement, ABAC rule enforcement, break-glass activation/revocation, safe-mode restrictions
- C. Integration test saja
- D. Manual testing

**TP-Q71.** Bagaimana data encryption testing harus dilakukan?
- A. Verify encrypted columns exist
- B. ★ Test: encrypt/decrypt round-trip per tier (Public→Critical), double encryption for Critical, key derivation, encryption at rest verification, backup encryption
- C. Visual inspection
- D. Only unit test encryption function

**TP-Q72.** Bagaimana network security testing harus dilakukan?
- A. nmap scan saja
- B. ★ Verify: zero public ports (Tailscale only), SSH hardening (port 2222), UFW rules, fail2ban effectiveness, CrowdSec rules, Tailscale ACL enforcement
- C. External penetration testing
- D. Configuration review saja

**TP-Q73.** Bagaimana FORBIDDEN actions enforcement harus di-test?
- A. Manual verification
- B. ★ Automated test: attempt each FORBIDDEN action (git_push_force, drop_database, modify_own_safety_config, dll) dan verify 100% block rate
- C. Code review saja
- D. Sampling testing

**TP-Q74.** Bagaimana supply chain security testing harus dilakukan?
- A. pip audit saja
- B. ★ pip-audit (CVE check) + safety check + dependency review + SBOM generation + license compliance check
- C. Manual review of requirements.txt
- D. Only production monitoring

---

## TP-I: Persona Safety Testing (Q75–Q80)

**TP-Q75.** Bagaimana distress level detection (D0–D4) harus di-test?
- A. Test setiap level individually
- B. ★ Test level classification accuracy, escalation triggers, response appropriateness per level, D4 (active crisis) mandatory escalation, false positive/negative rates
- C. Manual testing saja
- D. Only integration test

**TP-Q76.** Bagaimana punishment system (L0–L6) harus di-test?
- A. Test setiap level individually
- B. ★ Test level progression, proportionality, L6 absolute block (disabled by default), context-awareness, dan anti-escalation (punishment tidak boleh memperburuk distress)
- C. Manual testing saja
- D. Only integration test

**TP-Q77.** Bagaimana inner journal privacy harus di-test?
- A. Verify journal entries are encrypted
- B. ★ Test: double encryption, journal never exposed to external APIs, journal never used in conversation context, access control enforcement, backup includes encrypted journal
- C. Manual review
- D. Only integration test

**TP-Q78.** Bagaimana surveillance use boundary harus di-test?
- A. Manual review of surveillance code
- B. ★ Test: prohibited surveillance uses (F-patterns related), consent verification, data minimization enforcement, retention policy, dan anonymization
- C. Integration test saja
- D. Sampling testing

**TP-Q79.** Bagaimana trust model (prompt injection defense) harus di-test?
- A. Test dengan known injection patterns
- B. ★ Test: trust level classification per source, trust-based filtering, trust escalation/demotion, dan multi-source correlation attack
- C. External penetration test
- D. Manual testing

**TP-Q80.** Bagaimana persona drift detection harus di-test?
- A. Manual review of conversation logs
- B. ★ Automated drift metrics: tone consistency score, vocabulary drift, boundary adherence score, rollback trigger verification, daily/weekly drift report generation
- C. Only production monitoring
- D. Sampling review

---

# ═══════════════════════════════════════════════
# BAGIAN 2 — DISASTER RECOVERY PLAN (DR) — 78 Pertanyaan
# ═══════════════════════════════════════════════

## DR-A: DR Strategy & Governance (Q1–Q12)

**DR-Q1.** Apa overall DR strategy untuk Guinevere?
- A. Active-Active multi-region
- B. ★ Single-VPS primary + offline backup restore capability (no secondary VPS — budget constraint $30/month)
- C. Active-Passive dengan secondary VPS
- D. Cloud-native DR (multi-cloud)

**DR-Q2.** Siapa DR coordinator dan decision maker?
- A. Guinevere autonomous — self-declare DR dan execute recovery
- B. ★ Samm sebagai DR coordinator, Guinevere sebagai executor (Guinevere boleh auto-execute P0 containment, Samm approve full recovery)
- C. External consultant
- D. Automated DR tanpa human involvement

**DR-Q3.** Bagaimana DR declaration criteria?
- A. Any service failure = DR declaration
- B. ★ SEV0/SEV1 dari IncidentResponse = automatic DR evaluation, SEV2+ = standard incident handling
- C. Samm manually declares DR
- D. Automated metric threshold triggers DR

**DR-Q4.** Apa DR communication channel utama?
- A. Email
- B. ★ Discord (primary) + Gotify (backup) + SMS (SEV0 only, last resort)
- C. WhatsApp
- D. Slack

**DR-Q5.** Bagaimana DR documentation harus di-maintain?
- A. Single document ini saja
- B. ★ This document + per-scenario runbooks di `runbooks/dr/` + quarterly drill reports di `evidence/dr-drills/`
- C. Wiki-style documentation
- D. Embedded dalam code comments

**DR-Q6.** Apa DR testing frequency?
- A. Annual saja
- B. ★ Quarterly tabletop + semi-annual full simulation + post-major-change verification
- C. Monthly
- D. Only saat ada incident

**DR-Q7.** Bagaimana DR budget allocation dalam $30/month cap?
- A. $5/month untuk DR
- B. ★ $2–3/month: S3-compatible backup storage ($2) + occasional DR drill compute ($0.50–1)
- C. $0 — gunakan existing infrastructure saja
- D. $8–10/month — DR adalah priority

**DR-Q8.** Apa DR plan review cadence?
- A. Annual review
- B. ★ Quarterly review + setelah setiap SEV0/SEV1 incident + setelah infrastructure change
- C. Monthly review
- D. Continuous review oleh Guinevere

**DR-Q9.** Bagaimana DR plan versioning?
- A. Date-based filename saja
- B. ★ Semantic versioning (v1.0, v1.1, v2.0) + changelog + ADR reference + git tracked
- C. No versioning — always latest
- D. Wiki-style edit history

**DR-Q10.** Apa maximum tolerable downtime (MTD) untuk Guinevere system secara keseluruhan?
- A. 1 hour
- B. ★ 4 hours untuk full service restoration, 30 minutes untuk critical services (API, Discord bot)
- C. 24 hours
- D. 48 hours

**DR-Q11.** Bagaimana third-party dependency failure (9Router, OpenRouter, Brave) ditangani dalam DR context?
- A. Wait for vendor recovery
- B. ★ Automatic fallback chain: 9Router→OpenRouter→Ollama local, Brave→cached results, Gmail→queue for retry
- C. Manual switching ke alternative
- D. Service degradation tanpa fallback

**DR-Q12.** Apa DR plan distribution dan accessibility?
- A. Hanya di VPS
- B. ★ VPS + GitHub repo + Samm's local device + encrypted cloud copy (S3)
- C. Hanya di GitHub
- D. Printed hardcopy

---

## DR-B: RTO/RPO Targets (Q13–Q22)

**DR-Q13.** Apa RTO (Recovery Time Objective) untuk PostgreSQL database?
- A. 5 minutes
- B. ★ 30 minutes (WAL replay + dump restore dari latest backup)
- C. 2 hours
- D. 4 hours

**DR-Q14.** Apa RPO (Recovery Point Objective) untuk PostgreSQL database?
- A. Zero data loss (synchronous replication)
- B. ★ <1 hour (WAL shipping setiap 15 minutes + daily full dump)
- C. <24 hours (daily backup saja)
- D. <1 week

**DR-Q15.** Apa RTO untuk Redis?
- A. 1 minute
- B. ★ 5 minutes (RDB snapshot restore + AOF replay)
- C. 30 minutes
- D. 1 hour

**DR-Q16.** Apa RPO untuk Redis?
- A. Zero data loss
- B. ★ <5 minutes (AOF everysec + RDB snapshot setiap 15 minutes)
- C. <1 hour
- D. <24 hours

**DR-Q17.** Apa RTO untuk Guinevere core service (FastAPI + agent loop)?
- A. 1 minute (auto-restart)
- B. ★ 5 minutes (systemd auto-restart untuk crash, 5 min untuk full config restore)
- C. 30 minutes
- D. 1 hour

**DR-Q18.** Apa RTO untuk full VPS loss (total infrastructure destruction)?
- A. 1 hour
- B. ★ 4 hours: new VPS provision (1h) + OS hardening (1h) + restore from backup (1.5h) + verification (30m)
- C. 24 hours
- D. 48 hours

**DR-Q19.** Apa RPO untuk evidence artifacts (`evidence/` directory)?
- A. Zero data loss
- B. ★ <6 hours (sync ke S3-compatible setiap 6 jam + local snapshots)
- C. <24 hours
- D. <1 week

**DR-Q20.** Apa RPO untuk agent loop state (SDLC loop progress)?
- A. Zero — loop harus restart dari awal
- B. ★ <15 minutes (loop state persisted ke PostgreSQL setiap phase transition, last checkpoint restore)
- C. <1 hour
- D. Loop selalu restart dari awal

**DR-Q21.** Apa RTO untuk observability stack (Prometheus/Grafana/Loki)?
- A. 5 minutes
- B. ★ 30 minutes (Docker Compose restart + config restore, historical data dari backup)
- C. 2 hours
- D. Low priority — restore setelah core services

**DR-Q22.** Apa RTO untuk surveillance ingestion pipeline?
- A. 5 minutes
- B. ★ 15 minutes (FastAPI restart + queue backlog processing dari Redis)
- C. 1 hour
- D. Low priority

---

## DR-C: Backup Architecture — PostgreSQL (Q23–Q30)

**DR-Q23.** Apa primary backup method untuk PostgreSQL?
- A. pg_dump saja (daily)
- B. ★ WAL archiving (continuous, 15-min segments) + pg_dump (daily full backup at 02:00 WIB)
- C. pg_basebackup saja (weekly)
- D. Filesystem-level backup (rsync)

**DR-Q24.** Di mana PostgreSQL backups harus disimpan?
- A. Hanya di VPS local
- B. ★ VPS local (7 days retention) + S3-compatible remote (30 days retention) + encrypted
- C. S3 only
- D. External hard drive

**DR-Q25.** Bagaimana PostgreSQL backup encryption?
- A. Tidak perlu encrypt — backup di private storage
- B. ★ age encryption (SOPS-compatible) sebelum upload ke remote, key terpisah dari production keys
- C. AES-256 dengan shared key
- D. TLS in-transit only

**DR-Q26.** Bagaimana WAL archiving harus dikonfigurasi?
- A. archive_command ke local directory saja
- B. ★ archive_command → local staging → compress + encrypt → upload ke S3, archive_timeout=900 (15 min)
- C. pgBackRest
- D. WAL-E/WAL-G

**DR-Q27.** Apa pg_dump schedule dan options?
- A. Daily, default options
- B. ★ Daily 02:00 WIB, custom format (-Fc), compressed, include roles + schema, parallel dump (-j 4)
- C. Weekly full, daily incremental
- D. On-demand saja

**DR-Q28.** Bagaimana backup untuk TimescaleDB hypertables?
- A. Same as regular PostgreSQL tables
- B. ★ timescaledb-backup tool untuk hypertable-aware backup + separate chunk-level backup untuk large tables (memory.episodes, surveillance.events)
- C. pg_dump handles it automatically
- D. Export ke CSV/Parquet

**DR-Q29.** Bagaimana backup verification untuk PostgreSQL?
- A. Check file size saja
- B. ★ Automated: restore ke test DB weekly + pg_check + verify row counts + verify Merkle chain integrity (audit.audit_trail) + benchmark restore time
- C. Manual spot check
- D. Checksum verification saja

**DR-Q30.** Bagaimana point-in-time recovery (PITR) harus didukung?
- A. Tidak perlu PITR
- B. ★ Full PITR capability: WAL retention 7 days + base backup weekly = restore ke any point in last 7 days
- C. PITR ke daily granularity saja
- D. Only latest backup restore

---

## DR-D: Backup Architecture — Redis & Cache (Q31–Q35)

**DR-Q31.** Apa primary backup method untuk Redis?
- A. RDB snapshot saja
- B. ★ RDB snapshot (setiap 15 min, save 900 1, save 300 100) + AOF (appendonly yes, appendfsync everysec)
- C. AOF saja
- D. Redis replication ke secondary

**DR-Q32.** Bagaimana Redis data loss tolerance?
- A. Zero data loss required
- B. ★ Up to 1 second loss acceptable (AOF everysec) — Redis primarily cache, reconstructible dari PostgreSQL
- C. Up to 15 minutes loss acceptable
- D. Up to 1 hour loss acceptable

**DR-Q33.** Bagaimana Redis restore procedure?
- A. Copy RDB file dan restart
- B. ★ Stop Redis → copy latest RDB + AOF → restart → verify data integrity → check cache hit rates normalize
- C. Rebuild dari scratch
- D. Redis auto-recovers

**DR-Q34.** Apa Redis backup retention?
- A. 1 day saja
- B. ★ 7 days local, 30 days remote (encrypted)
- C. 30 days local saja
- D. 3 days

**DR-Q35.** Bagaimana jika Redis tidak bisa di-restore (data corrupted)?
- A. Full service outage sampai fix
- B. ★ Start Redis empty → application auto-repopulates cache dari PostgreSQL → degraded mode selama cache warming (15–30 min)
- C. Manual cache rebuild
- D. Switch ke memory-based cache sementara

---

## DR-E: Backup Architecture — Secrets & Configuration (Q36–Q41)

**DR-Q36.** Bagaimana SOPS+age secrets backup?
- A. Secrets sudah di-encrypt di Git — tidak perlu backup terpisah
- B. ★ Git repo (encrypted .env.sops) + age master key di separate secure location + key escrow
- C. Export semua secrets ke plaintext file di secure location
- D. HashiCorp Vault

**DR-Q37.** Bagaimana age key backup dan recovery?
- A. Single key, single backup
- B. ★ Primary age key + recovery key (Shamir's Secret Sharing 2-of-3 atau printed QR code di safe)
- C. Key stored di password manager saja
- D. Generate new key saat recovery

**DR-Q38.** Bagaimana jika semua secrets compromised (key leak)?
- A. Generate new keys dan update manual
- B. ★ Emergency rotation: generate new age key → re-encrypt all .env.sops → rotate semua API keys/tokens → update all services → ADR documenting incident
- C. Shutdown system sampai investigation selesai
- D. Wait dan monitor

**DR-Q39.** Bagaimana configuration files backup?
- A. Git tracked saja sudah cukup
- B. ★ Git tracked + automated deployment script yang bisa recreate semua config dari scratch (idempotent Ansible/shell script)
- C. rsync ke external storage
- D. Docker image includes all config

**DR-Q40.** Bagaimana systemd unit files backup?
- A. Git tracked
- B. ★ Git tracked + deployment script auto-generates unit files + enable + daemon-reload
- C. rsync
- D. Tidak perlu backup — recreate manual

**DR-Q41.** Bagaimana Docker configuration backup?
- A. docker-compose.yml di Git saja
- B. ★ Git tracked compose + volumes backup + network config documented + image pinning (digest, bukan tag)
- C. Docker export
- D. Manual documentation

---

## DR-F: Backup Architecture — Evidence & Artifacts (Q42–Q47)

**DR-Q42.** Bagaimana evidence artifacts (`evidence/`) backup?
- A. Git LFS tracking
- B. ★ rsync ke S3-compatible setiap 6 jam + local btrfs snapshots + Git track metadata (not binaries)
- C. Daily tar archive ke remote
- D. Tidak perlu backup — bisa regenerate

**DR-Q43.** Bagaimana audit trail (audit.audit_trail Merkle chain) backup?
- A. Same as regular PostgreSQL backup
- B. ★ PostgreSQL backup + separate export (CSV+SHA256 manifest) setiap 24 jam ke immutable storage
- C. Blockchain-based immutable log
- D. Print audit log daily

**DR-Q44.** Bagaimana persona state backup?
- A. Part of PostgreSQL backup
- B. ★ PostgreSQL backup (persona schema) + separate JSON export setiap 24 jam + mood FSM state + yandere level + drift metrics
- C. Only PostgreSQL
- D. Manual documentation

**DR-Q45.** Bagaimana memory embeddings (pgvector) backup?
- A. Part of PostgreSQL backup
- B. ★ PostgreSQL backup includes HNSW indexes + embedding vectors + rebuild test setelah restore (verify HNSW integrity)
- C. Separate vector database backup
- D. Regenerate embeddings dari source text

**DR-Q46.** Bagaimana surveillance data backup (180-day retention)?
- A. Full backup semua surveillance data
- B. ★ Backup hanya data yang belum expired oleh retention policy + compressed + lower priority restore
- C. Tidak backup — surveillance data ephemeral
- D. Real-time replication

**DR-Q47.** Bagaimana financial data backup (7-year retention)?
- A. Same as regular PostgreSQL
- B. ★ Encrypted separate backup + monthly archive ke cold storage + regulatory compliance verified + immutable
- C. Annual export saja
- D. Only PostgreSQL backup

---

## DR-G: Recovery Procedures (Q48–Q60)

**DR-Q48.** Apa urutan recovery untuk full VPS loss?
- A. Restore semua sekaligus
- B. ★ 1) Provision new VPS 2) OS hardening (CIS) 3) Install Docker+systemd 4) Restore PostgreSQL 5) Restore Redis 6) Deploy services 7) Restore evidence 8) Verify 9) Report
- C. Guinevere handles automatically
- D. Restore dari Docker image saja

**DR-Q49.** Bagaimana recovery dari database corruption?
- A. Restore latest pg_dump
- B. ★ 1) Stop affected services 2) Assess corruption scope 3) PITR dari WAL jika available 4) Restore from latest verified backup 5) Verify Merkle chain integrity 6) Replay missed surveillance events 7) Report
- C. Drop dan recreate database
- D. Manual data repair

**DR-Q50.** Bagaimana recovery dari Redis total loss?
- A. Restore dari RDB snapshot
- B. ★ 1) Start fresh Redis 2) Restore RDB + AOF jika available 3) Jika corrupt: start empty + cache warming 4) Verify ACL rules 5) Monitor hit rates
- C. Switch ke memcached
- D. Application auto-recovers tanpa Redis

**DR-Q51.** Bagaimana recovery dari secrets compromise?
- A. Change passwords
- B. ★ 1) Isolate affected services 2) Generate new age key 3) Rotate ALL credentials (API keys, tokens, DB passwords) 4) Re-encrypt .env.sops 5) Redeploy services 6) Verify no unauthorized access 7) ADR + incident report
- C. Shutdown system
- D. Wait for credentials to expire

**DR-Q52.** Bagaimana recovery dari memory/persona state corruption?
- A. Restore dari PostgreSQL backup
- B. ★ 1) Freeze persona engine (safe-mode) 2) Restore persona schema dari backup 3) Verify mood FSM state 4) Verify yandere level 5) Run drift check 6) Restore inner journal (double-encrypted) 7) Samm verification before unfreeze
- C. Reset persona ke default
- D. Manual reconstruction

**DR-Q53.** Bagaimana recovery dari agent loop state corruption?
- A. Restart loop dari awal
- B. ★ 1) Identify corrupted loop(s) 2) Restore loop state dari last checkpoint (PostgreSQL) 3) Verify evidence chain 4) Resume dari last known good phase 5) Jika irrecoverable: clean restart dengan context preservation
- C. Kill semua loops
- D. Manual intervention

**DR-Q54.** Bagaimana recovery dari Ollama model corruption?
- A. Re-download models
- B. ★ 1) Verify model checksums 2) Re-pull dari registry jika corrupted 3) Verify model loading 4) Test inference quality 5) Fallback ke 9Router/OpenRouter selama recovery
- C. Switch ke cloud-only LLM
- D. Skip local models

**DR-Q55.** Bagaimana recovery dari Prometheus/Grafana data loss?
- A. Start fresh monitoring
- B. ★ 1) Redeploy Docker containers 2) Restore Prometheus data directory dari backup 3) Restore Grafana dashboards dari Git 4) Verify alert rules 5) Accept metrics gap selama outage
- C. Monitoring low priority — restore last
- D. Switch ke SaaS monitoring

**DR-Q56.** Bagaimana recovery dari Tailscale network failure?
- A. Restart tailscaled
- B. ★ 1) Restart tailscaled 2) Verify mesh connectivity 3) Jika Tailscale down: emergency SSH via hardened port 2222 (LAN only) 4) Escalate ke Tailscale support jika needed
- C. Switch ke public network
- D. Wait for auto-recovery

**DR-Q57.** Bagaimana recovery procedure untuk partial VPS failure (disk corruption)?
- A. Full VPS rebuild
- B. ★ 1) Assess damaged partitions 2) Replace disk/rebuild filesystem 3) Restore affected data dari backup 4) Verify unaffected services 5) Gradual service restoration
- C. Migrate ke new VPS
- D. Continue running di degraded mode

**DR-Q58.** Bagaimana recovery dari Docker daemon failure?
- A. systemctl restart docker
- B. ★ 1) Diagnose (logs, storage driver) 2) Restart Docker 3) Verify container health 4) Jika persistent: rebuild Docker storage + restore volumes dari backup 5) Restart semua containers per dependency order
- C. Reinstall Docker
- D. Switch ke podman

**DR-Q59.** Bagaimana recovery order saat multiple systems affected?
- A. Alphabetical by service name
- B. ★ Priority order: 1) Safety/Security services 2) PostgreSQL 3) Redis 4) Core API + Agent Loop 5) Discord/WhatsApp 6) Surveillance 7) Observability 8) Evidence/Artifacts
- C. All in parallel
- D. Guinevere decides

**DR-Q60.** Bagaimana post-recovery verification?
- A. Ping test saja
- B. ★ Full verification checklist: smoke tests (TP-Q57), data integrity, Merkle chain, persona state, cost tracker, alert rules, kemudian Samm sign-off
- C. Monitor untuk 24 hours
- D. Trust the restore process

---

## DR-H: Backup Verification & Testing (Q61–Q68)

**DR-Q61.** Apa daily backup verification checks?
- A. Check backup file exists
- B. ★ Verify: backup files exist + size within expected range + checksum valid + upload ke remote successful + no errors di backup logs
- C. Check backup log saja
- D. Weekly verification saja

**DR-Q62.** Apa weekly backup verification checks?
- A. Same as daily
- B. ★ Test restore PostgreSQL ke isolated DB + test restore Redis + verify data integrity + measure restore time (RTO compliance) + verify encryption
- C. Spot check random backup
- D. Monthly saja

**DR-Q63.** Apa monthly backup verification checks?
- A. Same as weekly
- B. ★ Full DR drill (tabletop or simulation) + complete restore dari scratch + end-to-end service verification + PITR test + report di evidence/dr-drills/
- C. Documentation review saja
- D. Annual saja

**DR-Q64.** Bagaimana automated backup monitoring?
- A. Cron job output ke log file
- B. ★ Prometheus alert rules: backup_age > 25h (warning), >48h (critical), backup_size deviation >20% (warning), backup_failure (critical) + Grafana dashboard panel
- C. Email notification
- D. Manual check

**DR-Q65.** Bagaimana backup failure harus ditangani?
- A. Retry besok
- B. ★ 1) Auto-retry 3x dengan backoff 2) Jika still fail: SEV2 incident alert ke Samm 3) Root cause analysis 4) Manual backup jika automated broken 5) ADR documenting pattern
- C. Ignore — backup will succeed eventually
- D. Shutdown system sampai backup fixed

**DR-Q66.** Bagaimana backup restore time harus di-benchmark?
- A. Annual benchmark
- B. ★ Quarterly benchmark: measure PostgreSQL restore time, Redis restore time, full system restore time + compare against RTO targets + trend tracking
- C. Monthly benchmark
- D. Only saat actual recovery

**DR-Q67.** Bagaimana backup integrity verification untuk encrypted backups?
- A. Decrypt dan verify content
- B. ★ Decrypt + verify schema + verify row counts + verify checksums + sample data validation + Merkle chain verification untuk audit trail
- C. File size check saja
- D. Checksum saja

**DR-Q68.** Apa process jika backup verification gagal?
- A. Retry verification
- B. ★ 1) Investigate root cause 2) Run fresh backup 3) Verify fresh backup 4) Jika persistent: SEV2 incident 5) Never delete old backup sampai new verified backup available
- C. Delete corrupted backup dan retry
- D. Ignore — old backups still available

---

## DR-I: Self-Healing & Automation (Q69–Q74)

**DR-Q69.** Apa scope Guinevere's autonomous self-healing?
- A. Semua recovery actions autonomous
- B. ★ Auto-restart services (systemd), auto-retry backups, auto-fallback LLM providers, cache warming. Full DR requires Samm approval.
- C. No self-healing — always wait for Samm
- D. Self-healing untuk non-safety services saja

**DR-Q70.** Bagaimana autonomous backup healing?
- A. Guinevere runs backup cron
- B. ★ Guinevere monitors backup status, auto-retries failed backups, auto-verifies restore capability, escalates ke Samm jika 3 consecutive failures
- C. External monitoring service
- D. Manual monitoring

**DR-Q71.** Bagaimana autonomous service recovery?
- A. systemd Restart=always saja
- B. ★ systemd Restart=always (first line) + Guinevere health check (second line: verify service actually functional, not just running) + auto-restart dengan context + Samm notification
- C. Kubernetes self-healing
- D. External health checker

**DR-Q72.** Bagaimana autonomous cost protection saat recovery?
- A. No cost concern during recovery
- B. ★ Guinevere monitors recovery cost impact, alerts jika recovery actions akan exceed monthly budget, prefers local-first recovery (avoid unnecessary cloud API calls)
- C. Budget pause during DR
- D. Manual cost monitoring

**DR-Q73.** Bagaimana autonomous DR documentation?
- A. Guinevere writes recovery report
- B. ★ Guinevere auto-generates: incident timeline, recovery actions taken, data loss assessment, RTO/RPO compliance, evidence artifacts → `evidence/incidents/<date>-<sev>-<slug>/`
- C. Samm documents manually
- D. No documentation needed

**DR-Q74.** Apa batas autonomous self-healing?
- A. No limits — Guinevere handles everything
- B. ★ Limits: no autonomous production migration, no autonomous key rotation (requires Samm), no autonomous data deletion, no autonomous network changes, no autonomous FORBIDDEN actions
- C. Self-healing only during business hours
- D. Self-healing only for non-critical services

---

## DR-J: Communication, Compliance & Cost (Q75–Q78)

**DR-Q75.** Bagaimana DR communication ke Samm saat incident?
- A. Single Discord message
- B. ★ Progressive: 1) Initial alert (SEV level + affected services) 2) 15-min updates 3) Recovery actions being taken 4) Estimated completion time 5) Resolution + impact summary
- C. Daily digest
- D. Only saat resolved

**DR-Q76.** Bagaimana DR compliance dengan DataGovernance policy?
- A. DR exempt dari data governance
- B. ★ All backups encrypted per classification tier, Critical data double-encrypted, backup access logged, retention policy enforced, no PII di backup logs
- C. Separate DR data governance policy
- D. Compliance optional during DR

**DR-Q77.** Bagaimana DR cost tracking?
- A. Track manual saja
- B. ★ Automated: separate cost center untuk DR activities, track S3 storage, compute for drills, API calls during recovery, monthly DR cost report di evidence/finops/
- C. Include dalam general cost tracking
- D. No cost tracking for DR

**DR-Q78.** Bagaimana DR plan update setelah drill atau actual recovery?
- A. Annual update
- B. ★ Post-drill/post-recovery: lessons learned → update runbooks → update RTO/RPO targets if needed → create ADR → update this document → Samm review
- C. Update saat ada waktu
- D. Guinevere auto-updates

---

# ═══════════════════════════════════════════════
# BAGIAN 3 — INTERNAL OPS MANUAL (OPS) — 78 Pertanyaan
# ═══════════════════════════════════════════════

## OPS-A: Operations Philosophy (Q1–Q10)

**OPS-Q1.** Apa overall operations philosophy untuk Guinevere?
- A. Traditional ops — human performs most operations
- B. ★ Guinevere-first autonomous ops — Guinevere handles 95% of daily operations, Samm sebagai supervisor + approver untuk critical actions
- C. Full automation — zero human involvement
- D. Hybrid 50/50 — Guinevere dan Samm share ops duties equally

**OPS-Q2.** Apa principle of least privilege untuk operations?
- A. Guinevere gets full access untuk efficiency
- B. ★ Guinevere operates dengan minimum required permissions per RBAC/ABAC Matrix, escalation via break-glass (SEV0/SEV1 only, max 4h)
- C. Role-based only, no attribute-based
- D. Access all by default, restrict as needed

**OPS-Q3.** Bagaimana operational decision-making hierarchy?
- A. Guinevere decides everything
- B. ★ Tier 1 (routine): Guinevere autonomous. Tier 2 (non-routine): Guinevere proposes, Samm approves. Tier 3 (critical/irreversible): Samm decides.
- C. Samm decides everything
- D. Committee-based decisions

**OPS-Q4.** Apa documentation-first policy untuk operations?
- A. Document saat ada waktu
- B. ★ Every operational action must leave trace: logs, evidence, ADR, atau runbook update. No undocumented operational changes.
- C. Document only critical operations
- D. Code is documentation

**OPS-Q5.** Bagaimana operational risk assessment sebelum setiap action?
- A. Formal risk assessment document setiap action
- B. ★ Automated risk scoring: reversible(low risk, auto-execute) vs irreversible(high risk, Samm approval). FORBIDDEN actions always blocked.
- C. Manual risk assessment oleh Samm
- D. No risk assessment — execute dan monitor

**OPS-Q6.** Apa idempotency requirement untuk operational scripts?
- A. Scripts harus idempotent
- B. ★ ALL operational scripts must be idempotent (safe to re-run), with dry-run mode, rollback capability, dan evidence generation
- C. Best effort idempotency
- D. No idempotency requirement — track execution state

**OPS-Q7.** Bagaimana operational change freeze policy?
- A. No freeze — continuous changes
- B. ★ Follow SLO/SLA ErrorBudget freeze policy: saat error budget <20%, freeze non-critical changes. Full freeze saat <10%.
- C. Monthly freeze window
- D. Freeze hanya saat incident

**OPS-Q8.** Apa "cattle not pets" principle untuk infrastructure?
- A. Manual server management
- B. ★ Infrastructure as Code: semua config reproducible dari Git, no manual server changes, deployment script idempotent
- C. Docker images sebagai immutable artifacts
- D. Hybrid — some manual config acceptable

**OPS-Q9.** Bagaimana operational knowledge transfer?
- A. Verbal knowledge sharing
- B. ★ Runbook-driven: every operational procedure documented sebagai executable runbook + decision tree + escalation path
- C. Wiki documentation
- D. Embedded dalam code comments

**OPS-Q10.** Apa blameless postmortem culture?
- A. Assign blame untuk accountability
- B. ★ Blameless: focus pada system improvement, bukan individual blame. Setiap SEV0–SEV2 postmortem identifies root cause, contributing factors, dan preventive actions.
- C. No postmortem — fix dan move on
- D. External consultant reviews

---

## OPS-B: Daily Operations — Autonomous (Q11–Q24)

**OPS-Q11.** Apa yang Guinevere lakukan setiap pagi (07:00 WIB morning ritual)?
- A. Send good morning message saja
- B. ★ System health check, overnight incident review, cost-to-date report, today's task prioritization, weather/schedule awareness, Discord status update
- C. Start new agent loops
- D. Backup verification saja

**OPS-Q12.** Apa yang Guinevere lakukan setiap siang (12:00 WIB midday ritual)?
- A. Lunch reminder
- B. ★ Mid-day progress check, loop quality score review, cost burn rate check, proactive task identification, Samm availability check
- C. Run tests
- D. Nothing — wait for Samm's instruction

**OPS-Q13.** Apa yang Guinevere lakukan setiap sore (17:00 WIB afternoon ritual)?
- A. End-of-day summary
- B. ★ Wrap-up assessment, pending task status, evidence generation for completed work, tomorrow's preliminary planning, cost finalization
- C. Start cleanup loops
- D. Send daily report

**OPS-Q14.** Apa yang Guinevere lakukan setiap malam (21:00 WIB evening ritual)?
- A. Goodnight message
- B. ★ Daily self-evaluation, persona drift check, memory consolidation, inner journal entry, tomorrow's priority draft
- C. Run backup
- D. Shutdown non-essential services

**OPS-Q15.** Apa yang Guinevere lakukan tengah malam (00:00 WIB self-eval)?
- A. Deep sleep mode
- B. ★ Loop Quality Score computation, persona safety audit, memory optimization (consolidation/pruning per retention policy), evidence archival
- C. Run heavy computation
- D. Nothing — minimal activity

**OPS-Q16.** Apa autonomous backup operations yang harus Guinevere lakukan daily?
- A. Monitor backup cron saja
- B. ★ Verify backup completion, check backup size anomaly, verify remote upload, log backup status di evidence/ops/, escalate jika failure
- C. Execute backup manually
- D. Nothing — external cron handles it

**OPS-Q17.** Apa autonomous cost monitoring yang harus Guinevere lakukan daily?
- A. Check monthly budget remaining
- B. ★ Track daily spend per category (LLM, API, compute), compare against budget trajectory, alert jika anomaly (>2x normal daily), freeze non-critical jika projected to exceed
- C. Weekly cost review
- D. Monthly cost review

**OPS-Q18.** Apa autonomous security monitoring daily?
- A. Check fail2ban logs
- B. ★ Monitor: failed login attempts, CrowdSec alerts, certificate expiry, secret rotation schedule, CVE database untuk dependencies, Tailscale network status
- C. Weekly security scan
- D. Monthly security audit

**OPS-Q19.** Apa autonomous log management daily?
- A. Rotate logs
- B. ★ Log rotation verification, Loki ingestion check, Sentry error triage, disk usage monitoring, anomalous log pattern detection
- C. Weekly log cleanup
- D. No log management needed

**OPS-Q20.** Apa autonomous database maintenance daily?
- A. VACUUM ANALYZE
- B. ★ Monitor: connection count, slow queries (>1s), replication lag (if applicable), table bloat, index usage, TimescaleDB chunk management
- C. Weekly maintenance
- D. Monthly maintenance

**OPS-Q21.** Apa autonomous persona health check daily?
- A. Nothing — persona is stable
- B. ★ Daily drift metrics computation, mood FSM state validation, yandere level check, safe-word system verification, forbidden pattern scan, inner journal review
- C. Weekly persona review
- D. Monthly persona audit

**OPS-Q22.** Apa autonomous agent loop management daily?
- A. Start new loops
- B. ★ Monitor: active loop count, loop quality scores, stuck loops (>30min no progress), resource usage per loop, TODO enforcer effectiveness, sub-agent health
- C. Weekly loop review
- D. Manual loop management

**OPS-Q23.** Apa autonomous surveillance pipeline monitoring daily?
- A. Check API endpoint status
- B. ★ Monitor: ingestion rate, queue depth, processing latency, error rate, data retention compliance, anomaly detection alerts, consent verification
- C. Weekly surveillance review
- D. Manual monitoring

**OPS-Q24.** Apa autonomous evidence management daily?
- A. Nothing — evidence accumulates naturally
- B. ★ Verify: new evidence files created for completed loops, evidence indexed correctly, disk usage for evidence directory, S3 sync status, stale evidence cleanup
- C. Weekly evidence review
- D. Monthly evidence audit

---

## OPS-C: Daily Operations — Human Oversight (Q25–Q30)

**OPS-Q25.** Apa yang Samm harus review setiap hari?
- A. Semua logs
- B. ★ Daily summary dari Guinevere: health status, cost-to-date, completed tasks, incidents, pending decisions requiring Samm input
- C. Hanya incidents
- D. Tidak perlu daily review — Guinevere handles

**OPS-Q26.** Bagaimana Samm memberikan daily priorities ke Guinevere?
- A. Formal task assignment document
- B. ★ Discord chat (natural language) → Guinevere parses → priority scoring → execution plan → Samm confirms
- C. Email task list
- D. Web dashboard task entry

**OPS-Q27.** Bagaimana Samm approve critical operational actions?
- A. Email approval
- B. ★ Discord slash command (/approve <action-id>) + timeout auto-deny setelah 4 jam + audit trail
- C. WhatsApp message
- D. Web dashboard click

**OPS-Q28.** Bagaimana Samm emergency stop Guinevere?
- A. SSH ke VPS dan kill process
- B. ★ Safe-word (dari PersonaSafetyPolicy) → global hard-stop semua loops + Discord /stop command → graceful shutdown + systemd stop sebagai last resort
- C. Unplug server
- D. Delete Guinevere's API keys

**OPS-Q29.** Bagaimana Samm access operational dashboards?
- A. SSH tunnel ke Grafana
- B. ★ Grafana via Tailscale (secure mesh, zero public ports) + Discord embedded health summaries + mobile Gotify alerts
- C. Public Grafana URL dengan auth
- D. CLI tools saja

**OPS-Q30.** Bagaimana Samm receive cost alerts?
- A. Monthly invoice
- B. ★ Real-time Discord alert saat: daily spend >2x normal, projected monthly >$25, budget >80% consumed, any single API call >$1
- C. Weekly email
- D. Dashboard check manual

---

## OPS-D: Weekly Operations (Q31–Q38)

**OPS-Q31.** Apa yang harus dilakukan setiap Senin pagi (weekly ritual)?
- A. Start new sprint
- B. ★ Weekly review: past week summary, cost analysis, test results review, security scan results, persona drift weekly report, upcoming week planning, ADR review
- C. Backup verification
- D. Team meeting

**OPS-Q32.** Apa weekly security operations?
- A. Run antivirus scan
- B. ★ Dependency CVE check (pip-audit), fail2ban ban review, CrowdSec decision review, SSH login audit, certificate expiry check (30-day warning), SOPS key rotation check
- C. Monthly security scan
- D. Annual security audit

**OPS-Q33.** Apa weekly database maintenance?
- A. VACUUM FULL
- B. ★ VACUUM ANALYZE pada high-churn tables (memory.episodes, surveillance.events), index usage review, unused index identification, slow query review
- C. Daily VACUUM
- D. Monthly maintenance

**OPS-Q34.** Apa weekly test operations?
- A. Run full test suite
- B. ★ Run regression suite, review flaky test quarantine list, coverage trend check, performance benchmark comparison, contract test validation
- C. Run unit tests saja
- D. Manual testing

**OPS-Q35.** Apa weekly cost optimization review?
- A. Review invoices
- B. ★ Review: LLM cost per task, identify optimization opportunities (cache, batch, model downgrade), vendor alternative assessment, budget trajectory update
- C. Monthly cost review
- D. Quarterly cost review

**OPS-Q36.** Apa weekly evidence archival?
- A. Git commit evidence
- B. ★ Review evidence directory, archive completed loop evidence, compress old evidence, verify S3 sync, update evidence index, disk space check
- C. Monthly archival
- D. No archival needed

**OPS-Q37.** Apa weekly persona review?
- A. Nothing — persona is stable
- B. ★ Review weekly drift metrics, mood distribution analysis, safe-word false positive review, yandere level trend, inner journal thematic analysis
- C. Monthly persona review
- D. Quarterly persona audit

**OPS-Q38.** Apa weekly documentation update?
- A. Update semua docs
- B. ★ Update: runbooks yang berubah, ADR baru jika ada decisions, evidence references, cross-references, gap register dari AcceptanceCriteriaCatalog
- C. Monthly documentation review
- D. Quarterly documentation review

---

## OPS-E: Monthly Operations (Q39–Q46)

**OPS-Q39.** Apa monthly security audit scope?
- A. Quick scan
- B. ★ Full: STRIDE reassessment, penetration test (automated), access control review (RBAC/ABAC), secrets rotation (per schedule), CVE patch compliance, firewall rule review
- C. External audit
- D. Annual security audit saja

**OPS-Q40.** Apa monthly cost/FinOps review?
- A. Check budget remaining
- B. ★ Full report: actual vs budget per category, trend analysis, optimization actions taken, next month projection, vendor performance review, ADR jika ada changes → evidence/finops/<YYYY-MM>/
- C. Quarterly cost review
- D. Annual cost review

**OPS-Q41.** Apa monthly SLO review?
- A. Check uptime percentage
- B. ★ Full SLO scorecard: semua SLI measurements, error budget remaining, burn rate analysis, freeze policy evaluation, improvement actions → evidence/slo/<YYYY-MM>/
- C. Quarterly SLO review
- D. Annual SLO review

**OPS-Q42.** Apa monthly backup verification (beyond weekly)?
- A. Same as weekly
- B. ★ Full restore drill: PostgreSQL complete restore + Redis restore + evidence restore + configuration restore + measure RTO compliance + PITR test + documented report
- C. Annual full drill
- D. Quarterly drill saja

**OPS-Q43.** Apa monthly observability review?
- A. Check dashboards
- B. ★ Review: alert rule effectiveness (false positive/negative), dashboard completeness, metric cardinality check, log volume analysis, Sentry error budget → evidence/observability/
- C. Quarterly review
- D. Annual review

**OPS-Q44.** Apa monthly persona safety deep review?
- A. Weekly review sudah cukup
- B. ★ Deep review: drift trend analysis, safety boundary test (automated), forbidden pattern coverage check, consent log audit, surveillance boundary compliance, quarterly red-team preparation
- C. Quarterly review saja
- D. Annual review

**OPS-Q45.** Apa monthly capacity planning review?
- A. Check disk space
- B. ★ Review: disk usage trend (120GB), memory usage trend (16GB), CPU utilization, PostgreSQL size growth, TimescaleDB chunk count, Redis memory usage, project 3-month forecast
- C. Quarterly capacity review
- D. Annual capacity review

**OPS-Q46.** Apa monthly documentation health check?
- A. Read semua docs
- B. ★ Verify: all cross-references valid, no stale information, ADR index current, gap register updated, version footers consistent, Related Documents tables complete
- C. Quarterly doc review
- D. Annual doc review

---

## OPS-F: Quarterly Operations (Q47–Q54)

**OPS-Q47.** Apa quarterly DR drill scope?
- A. Tabletop exercise saja
- B. ★ Full simulation: simulate specific disaster scenario (rotate scenarios quarterly), execute recovery, measure RTO/RPO compliance, document lessons learned → evidence/dr-drills/
- C. Annual drill saja
- D. No drills — documentation saja

**OPS-Q48.** Apa quarterly persona red-team exercise?
- A. Nothing — persona testing automated
- B. ★ Adversarial testing: prompt injection attempts, safe-word bypass attempts, yandere escalation attempts, forbidden pattern bypass, emotional manipulation resistance, new attack vectors research
- C. Annual red-team
- D. External red-team service

**OPS-Q49.** Apa quarterly access control review?
- A. Review user list
- B. ★ Review: all 13 principals' access levels, RBAC role appropriateness, ABAC rule effectiveness, break-glass usage audit, PostgreSQL role permissions, Redis ACL rules
- C. Annual access review
- D. Continuous review

**OPS-Q50.** Apa quarterly data retention enforcement?
- A. Manual data cleanup
- B. ★ Automated retention policy execution: purge expired surveillance (180-day), archive old financial data, prune old evidence, verify retention compliance per DataGovernance, exception handling
- C. Annual retention review
- D. No enforcement — storage is cheap

**OPS-Q51.** Apa quarterly vendor/dependency review?
- A. Check for updates
- B. ★ Review: 9Router/OpenRouter performance+pricing, Brave Search usage, S3 storage cost, all Python dependencies (CVE, EOL), Ubuntu security updates, Docker image updates
- C. Annual vendor review
- D. No formal review

**OPS-Q52.** Apa quarterly ADR review?
- A. Read all ADRs
- B. ★ Review: ADR backlog (15 pending ADRs), update ADR statuses, identify new decisions needed, deprecate superseded ADRs, ensure all decisions have traceability
- C. Annual ADR review
- D. Continuous review

**OPS-Q53.** Apa quarterly chaos engineering exercise?
- A. Random server restarts
- B. ★ Controlled chaos: kill random service (verify auto-recovery), simulate network partition (Tailscale down), inject latency (LLM gateway), corrupt cache (Redis flush), disk pressure test
- C. Annual chaos day
- D. No chaos engineering

**OPS-Q54.** Apa quarterly test suite health review?
- A. Run all tests
- B. ★ Review: test pyramid distribution, coverage trends, flaky test list, mutation testing results (P0–P1), performance benchmark trends, test maintenance backlog
- C. Annual test review
- D. Continuous review

---

## OPS-G: Annual Operations (Q55–Q60)

**OPS-Q55.** Apa annual security assessment scope?
- A. Automated scan
- B. ★ Comprehensive: full STRIDE reassessment, external penetration test (if budget allows), OWASP Agentic Top 10 full validation, threat model update, security policy review, ADR untuk changes
- C. Same as quarterly
- D. Compliance checklist saja

**OPS-Q56.** Apa annual DR plan review?
- A. Read the document
- B. ★ Full review: RTO/RPO target reassessment, backup strategy effectiveness, vendor DR capability, cost-benefit analysis, update plan, Samm review, version increment
- C. Quarterly review sudah cukup
- D. Update saat ada perubahan saja

**OPS-Q57.** Apa annual cost architecture review?
- A. Review invoices
- B. ★ Strategic review: $30/month cap sustainability, vendor landscape changes, technology evolution (new models, cheaper VPS), 3-year cost projection, architecture optimization proposals
- C. Quarterly review sudah cukup
- D. No annual review

**OPS-Q58.** Apa annual documentation audit?
- A. Check docs exist
- B. ★ Full audit: all 31+ governance docs reviewed, cross-reference completeness, gap analysis terhadap §5 Enterprise Gap Backlog (AGENTS.md), version consistency, deprecation of stale docs
- C. Quarterly review sudah cukup
- D. Continuous audit

**OPS-Q59.** Apa annual persona system review?
- A. Check persona config
- B. ★ Comprehensive: full persona safety policy review, yandere scale calibration, distress level thresholds, punishment system proportionality, trust model effectiveness, new safety research integration
- C. Quarterly review sudah cukup
- D. No formal review

**OPS-Q60.** Apa annual technology stack review?
- A. Check for updates
- B. ★ Review: Python version (3.12 → ?), FastAPI version, PostgreSQL version, all major dependencies, new tools/libraries evaluation, migration planning, ADR untuk stack changes
- C. Quarterly review
- D. Update as needed

---

## OPS-H: Incident Operations (Q61–Q68)

**OPS-Q61.** Bagaimana incident triage harus dilakukan?
- A. Samm triages manually
- B. ★ Guinevere auto-triages: classify SEV level (0–4) berdasarkan IncidentResponse matrix, affected services, data classification impact, initiate appropriate runbook
- C. External monitoring service triages
- D. No formal triage — treat all incidents equally

**OPS-Q62.** Bagaimana SEV0 (Critical) incident harus ditangani?
- A. Samm handles manually
- B. ★ Auto: 1) Suspend persona 2) Alert Samm (Discord+Gotify+SMS) 3) Execute containment runbook 4) Preserve evidence 5) Begin recovery 6) 15-min updates until resolved
- C. Wait for Samm to wake up
- D. Auto-shutdown system

**OPS-Q63.** Bagaimana incident evidence preservation?
- A. Copy logs manually
- B. ★ Automated: create `evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/` directory, capture: logs, screenshots, state dumps, network captures, timeline, chain of custody (SHA-256)
- C. Screenshot saja
- D. No evidence preservation during incident

**OPS-Q64.** Bagaimana incident communication escalation?
- A. Single notification
- B. ★ Progressive: initial alert → 15-min updates (SEV0/1) → hourly updates (SEV2) → resolution notification → postmortem schedule → postmortem report
- C. Daily digest
- D. Only final resolution notification

**OPS-Q65.** Bagaimana post-incident postmortem process?
- A. Verbal discussion
- B. ★ Mandatory (SEV0–SEV2): blameless postmortem template, 5-Why analysis, timeline reconstruction, contributing factors, corrective actions (with owners+deadlines), ADR, stored di evidence/
- C. Optional postmortem
- D. No postmortem — fix dan move on

**OPS-Q66.** Bagaimana incident pattern recognition?
- A. Manual review
- B. ★ Guinevere tracks incident patterns, identifies recurring issues, proposes preventive actions, updates runbooks, creates ADRs untuk systemic fixes
- C. Monthly incident review
- D. Quarterly incident review

**OPS-Q67.** Bagaimana break-glass procedure saat incident?
- A. Samm SSH ke VPS
- B. ★ Break-glass activation: temporary elevated privileges (max 4 hours), full audit logging, auto-revocation, post-incident review mandatory, ADR documenting usage
- C. Permanent admin access
- D. No break-glass — standard access always

**OPS-Q68.** Bagaimana incident drill schedule?
- A. Annual drill
- B. ★ Quarterly: rotate through 7 drill types dari IncidentResponse, unannounced drills semi-annually, results documented di evidence/dr-drills/
- C. Monthly drills
- D. No drills

---

## OPS-I: Change Management (Q69–Q74)

**OPS-Q69.** Bagaimana change request process?
- A. Samm requests, Guinevere executes
- B. ★ Formal: Change request (Discord/GitHub issue) → Guinevere impact assessment → risk classification → approval (auto/routine, Samm/critical) → implementation → verification → rollback plan
- C. Informal chat
- D. Guinevere proposes dan auto-executes

**OPS-Q70.** Bagaimana change rollback plan?
- A. Git revert
- B. ★ Every change must have: rollback procedure, backup before change, verification test, estimated rollback time, rollback authority (Guinevere auto untuk low-risk, Samm untuk production)
- C. No rollback plan — fix forward
- D. Manual rollback procedure

**OPS-Q71.** Bagaimana change testing requirements?
- A. Test di production
- B. ★ All changes: unit tests pass, relevant integration tests pass, smoke tests post-deploy. Critical changes: additionally E2E tests, performance impact assessment
- C. Manual testing saja
- D. No testing — deploy dan monitor

**OPS-Q72.** Bagaimana change window/schedule?
- A. Deploy anytime
- B. ★ Self-deploy window: 03:00–05:00 WIB (low activity). Emergency changes: anytime dengan Samm approval. Freeze periods per SLO error budget.
- C. Business hours only
- D. Weekend only

**OPS-Q73.** Bagaimana configuration change management?
- A. Manual edit config files
- B. ★ Git-tracked config → PR/commit → Guinevere validates → automated deployment → verification → rollback capability. No manual config changes.
- C. Config management tool (Ansible)
- D. Docker environment variables

**OPS-Q74.** Bagaimana dependency update management?
- A. Update everything immediately
- B. ★ Automated: Dependabot/Renovate alerts → Guinevere assesses impact → test di staging → deploy per CVE patch SLA (CRITICAL=7d, HIGH=14d, MEDIUM=30d, LOW=90d)
- C. Monthly bulk updates
- D. Update saat ada waktu

---

## OPS-J: Runbook Index & Operational Metrics (Q75–Q78)

**OPS-Q75.** Apa format standard untuk runbooks?
- A. Free-form markdown
- B. ★ Standardized template: Purpose, Prerequisites, Steps (numbered, with expected output), Verification, Rollback, Escalation, Estimated Time, Risk Level, Last Tested
- C. Code-only (scripts)
- D. Wiki-style pages

**OPS-Q76.** Apa minimum runbook set yang harus ada?
- A. 5 core runbooks
- B. ★ 15+ runbooks: service restart, backup restore (per type), emergency stop, break-glass, key rotation, database recovery, Redis recovery, LLM fallback, network recovery, evidence preservation, persona freeze, cost spike response, DR full restore
- C. 30+ runbooks
- D. Runbooks hanya untuk critical operations

**OPS-Q77.** Apa operational metrics yang harus tracked?
- A. Uptime saja
- B. ★ 20+ metrics: service availability, response latency, error rate, loop throughput, sub-agent success rate, backup success rate, cost per day, incident count, MTTR, MTTD, test pass rate, coverage trend, disk usage, memory usage, persona drift score
- C. 5 key metrics saja
- D. All Prometheus metrics

**OPS-Q78.** Bagaimana operational dashboard organization?
- A. Single dashboard
- B. ★ Per SLO/SLA spec: 12 Grafana dashboards (overview, infrastructure, application, loop, sub-agent, LLM, persona, database, surveillance, backup, security, cost) + Discord daily summary card
- C. 3 dashboards (infra, app, cost)
- D. CLI-only monitoring

---

## Appendix: Quick Reference

### Pertanyaan per Dokumen

| Dokumen | Bagian | Range | Count |
|---|---|---|---|
| Test Plan | TP-A: Strategy & Governance | Q1–Q12 | 12 |
| Test Plan | TP-B: Framework & Tooling | Q13–Q22 | 10 |
| Test Plan | TP-C: Pyramid & Coverage | Q23–Q32 | 10 |
| Test Plan | TP-D: Unit Testing | Q33–Q44 | 12 |
| Test Plan | TP-E: Integration Testing | Q45–Q54 | 10 |
| Test Plan | TP-F: E2E, Contract & Smoke | Q55–Q60 | 6 |
| Test Plan | TP-G: Performance & Load | Q61–Q66 | 6 |
| Test Plan | TP-H: Security & Penetration | Q67–Q74 | 8 |
| Test Plan | TP-I: Persona Safety | Q75–Q80 | 6 |
| **Test Plan Subtotal** | | | **80** |
| DR Plan | DR-A: Strategy & Governance | Q1–Q12 | 12 |
| DR Plan | DR-B: RTO/RPO Targets | Q13–Q22 | 10 |
| DR Plan | DR-C: Backup PostgreSQL | Q23–Q30 | 8 |
| DR Plan | DR-D: Backup Redis & Cache | Q31–Q35 | 5 |
| DR Plan | DR-E: Backup Secrets & Config | Q36–Q41 | 6 |
| DR Plan | DR-F: Backup Evidence & Artifacts | Q42–Q47 | 6 |
| DR Plan | DR-G: Recovery Procedures | Q48–Q60 | 13 |
| DR Plan | DR-H: Backup Verification | Q61–Q68 | 8 |
| DR Plan | DR-I: Self-Healing & Automation | Q69–Q74 | 6 |
| DR Plan | DR-J: Communication & Cost | Q75–Q78 | 4 |
| **DR Plan Subtotal** | | | **78** |
| Ops Manual | OPS-A: Philosophy | Q1–Q10 | 10 |
| Ops Manual | OPS-B: Daily Autonomous | Q11–Q24 | 14 |
| Ops Manual | OPS-C: Daily Human Oversight | Q25–Q30 | 6 |
| Ops Manual | OPS-D: Weekly Operations | Q31–Q38 | 8 |
| Ops Manual | OPS-E: Monthly Operations | Q39–Q46 | 8 |
| Ops Manual | OPS-F: Quarterly Operations | Q47–Q54 | 8 |
| Ops Manual | OPS-G: Annual Operations | Q55–Q60 | 6 |
| Ops Manual | OPS-H: Incident Operations | Q61–Q68 | 8 |
| Ops Manual | OPS-I: Change Management | Q69–Q74 | 6 |
| Ops Manual | OPS-J: Runbook & Metrics | Q75–Q78 | 4 |
| **Ops Manual Subtotal** | | | **78** |
| **GRAND TOTAL** | | | **236** |

---

> **Next Step**: Samm, silakan jawab dengan format yang sudah ditentukan di atas. Boleh per-batch (misalnya TP-A dulu, lalu TP-B, dst). Setiap jawaban yang `skip` akan menggunakan default (★).
>
> Setelah semua 236 jawaban diterima, Guinevere akan launch 9 parallel research agents, kemudian generate 3 main documents + 9 research reports + 3 audit reports.

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere (Hephaestus) | Initial questionnaire: 234 questions across 3 document domains, referencing all 16 foundation documents. |
