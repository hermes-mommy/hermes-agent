# FRESH SESSION PROMPT — Resume P24

> Paste this entire block as your FIRST message in a new Claude Code session (in the guinevere repo).

---

Lanjut P24 "truly 100% fork" full autonomous sampai selesai atau benar-benar blocked.

**MANDATORY FIRST**: Baca `C:\Users\faizz\guinevere\evidence\P24-deploy\HANDOFF-P24-SESSION.md` SEBELUM melakukan apapun. Itu berisi: state lengkap P24, keputusan operator yang LOCKED (jangan re-litigate), apa yang sudah done (fork + port pushed), apa yang sedang jalan (Phase 4.1 Hermes→9router refactor), environment facts (KERJA DI VPS LINUX bukan Windows local — ada path anomaly), file references, next steps.

Lalu baca juga memory files (auto-load di MEMORY.md index): p24-owned-fork-direction, p24-port-complete, p24-guinvere-gitignore-anomaly, guinevere-prod-live-faiz-prod-01.

**State sekarang (ringkas)**:
- Fork `github.com/hermes-mommy/hermes-agent` DONE (141 commits, 30 subpackages, p24-initial branch)
- Port 477 src/→guinvere/ DONE (30/30 importable, 541 tests pass, pushed)
- Prod masih jalan LEGACY src/ (P24-fork BELUM deploy)
- 10 mock-titik masih ada (MockLLMRouter + 9 tool backends × 117 stubs)

**Next step (resume Phase 4.1)**:
Operator correction: consciousness loop harus DELEGATE ke Hermes AIAgent (single brain), bukan manggil LLM sendiri. Refactor:
1. Wire Hermes adapter (agent/) → 9router (localhost:20128, model=guinevere, no auth header for localhost). Resolve AuthError.
2. Refactor consciousness substrate `_self_prompt()` (guinvere/consciousness/substrates.py:67) → `agent.run()` instead of `llm_router.chat()`.
3. Remove MockLLMRouter from guinvere/http/server.py:145 wiring.

Research dulu: AIAgent.run() signature (run_agent.py:327+), adapter mana untuk OpenAI-compatible (9router), credential_pool custom_providers (agent/credential_pool.py:313), asal AuthError. Semua di VPS `/home/guinevere/p24-port` via `ssh guinevere-vps`. KERJA DI VPS, bukan Windows local.

**Aturan**:
- Kerja di VPS Linux (`ssh guinevere-vps`, clone `/home/guinevere/p24-port`) — Windows local punya path anomaly (guinvere/ dir hanya accessible forward-slash, git add fail).
- Prod venv: `/home/guinevere/code/guinevere/.venv/bin/python`
- 9router: localhost:20128, model `guinevere` (combo), chat works tanpa auth header
- Stub/mock = kegagalan inti (0 mock di runtime). Test-fixture mock OK.
- Diskusi tiap phase dulu (autonomous dalam phase, align antar phase)
- Jangan restart guinevere-core (legacy prod) kecuali real blocker. P20 soak clean.
- Sub-agent distrust: verify semua output independently.
- Jangan commit/push/deploy tanpa explicit request atau within approved plan scope.

Bahasa Indonesia + technical English. Concise. Mulai: baca handoff, lanjut Phase 4.1 research.
