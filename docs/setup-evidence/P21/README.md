# P21 — Voice Interface: Index

**Status:** 🟣 DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS
**Date:** 2026-06-24 (definition phase complete)
**Phase:** Expansion — Voice Interface

## Planned Scope

Phase 21 adds a voice interface to Guinevere alongside the existing Discord
text channel. The voice path covers speech-to-text ingestion (push-to-talk
and wake-word), text-to-speech replies using a consented persona voice,
real-time interruption handling, and consent gating for always-listening
modes. Voice is treated as a first-class surveillance stream with the same
consent, retention, and redaction rules as text.

Planned deliverables include: STT/TTS provider integration with rotation,
voice activity detection and wake-word config, push-to-talk Discord voice
channel handler, consent flow for always-listening mode, and retention
policy aligned with SurveillanceDataPolicy.

> **Definition complete (2026-06-24):** The P21 voice interface is fully
> defined end-to-end (plan + 9 research files + 2 audit rounds, all PASS).
> The definition integrates voice into the existing Hermes turn-core, life_kernel,
> memory, consent, audit, and HARD STOP infrastructure — **not** as a sidecar.
> Core insight: a voice transcript is text, so the existing text-based safety
> hooks (HARD STOP, distress, injection-sanitization) apply unchanged.
> Implementation waves P21-001..009 are scaffolded but HELD until the P20
> Living Autonomy Kernel production-pass (LK-017 soak) completes, because
> several waves touch LOCKED P20 files. No runtime code was written, deployed,
> or restarted in this phase.

## Directory Structure

```
P21/
├── README.md                    ← You are here
├── plan/
│   └── p21-voice-interface-enterprise-plan.md   ← enterprise plan (planner gate)
├── evidence/
│   ├── audits/
│   │   ├── round-1/             ← 8 audit dimensions (initial)
│   │   └── round-2/             ← 8 audit dimensions (post-amendment, all PASS)
│   ├── p21-definition-verification.md
│   ├── auditor-gate.md
│   └── final-p21-planning-report.md
└── research/
    ├── p21-tool-skill-coverage-matrix.md
    ├── p21-voice-provider-research.md
    ├── p21-discord-voice-research.md
    ├── p21-hermes-core-integration-research.md
    ├── p21-life-kernel-integration-research.md
    ├── p21-memory-transcript-research.md
    ├── p21-consent-surveillance-research.md
    ├── p21-security-secrets-research.md
    ├── p21-runtime-latency-deploy-research.md
    └── p21-dependency-collision-research.md
```

## Production Code Location

| Artifact | Path |
|---|---|
| Package | `src/voice/` (planned — NEW, unblocked but not executed) |
| Voice sensor adapter | `src/life_kernel/sensor_adapters/voice_sensor_adapter.py` (planned) |
| Discord voice client | `src/discord/_voice_client.py` + `cmd_voice.py` (planned) |
| DB Migration | `alembic/versions/p21_001_voice_stream.py` (planned, `down_revision=p20_001`) |
| Secrets | `secrets/voice-secrets.enc.yaml` (planned, SOPS/age) |
| systemd unit | `guinevere-voice.service` (planned) |

## Progress

| Step | Status | Description |
|---|---|---|
| DEFINITION | ✅ COMPLETE | Plan + 9 research files + 2 audit rounds (all PASS) |
| P21-001 | ⬜ HELD | STT/TTS provider abstraction (NEW files, unblocked but not executed) |
| P21-002 | ⬜ HELD | Discord push-to-talk MVP |
| P21-003 | ⬜ HELD (P20-gate) | Hermes voice turn pipeline (LOCKED file: hermes_conversational.py) |
| P21-004 | ⬜ HELD (P20-gate) | Transcript memory + retention/redaction (LOCKED: models.py) |
| P21-005 | ⬜ HELD | Consent + HARD STOP + safe-word enforcement |
| P21-006 | ⬜ HELD | VAD/wake-word gated design (always-listening NOT MVP) |
| P21-007 | ⬜ HELD | Dashboard/status integration (additive) |
| P21-008 | ⬜ HELD (P20-gate) | Runtime deploy + smoke + rollback (LOCKED: main.py, pyproject.toml) |
| P21-009 | ⬜ HELD | Audit + soak + final evidence |

> **Note:** The definition phase is complete. Implementation waves are
> scaffolded with per-step verification (Expected Files / Forbidden Patterns /
> Required Commands / Evidence / Hard Rejection) and held until the P20
> production-pass. See `plan/p21-voice-interface-enterprise-plan.md` for the
> full enterprise plan and `evidence/final-p21-planning-report.md` for the
> executive summary.

## Key Decisions

- **Integration, not sidecar** — voice reuses the Hermes text turn-core (`_process_turn_core`).
- **HARD STOP first-class in audio path** — `HardStopHandler.check(transcript)` pre-Hermes pre-sanitization; shared Redis `life_kernel:hard_stop` flag.
- **Always-listening NOT MVP** — 8-gate checklist (consent + indicator + retention + HARD STOP + audit + device auth + purpose-bound + no-silent-reactivation).
- **Voice transcript = untrusted text (Trust 6)** — injection vector V-022; classify→sanitize→quarantine→L7-L9.
- **P19 forward-compat** — nullable `project_id` on voice episodes.
- **P20 non-interference** — strictly additive life_kernel changes; LOCKED files untouched until P20 pass.

## Latest Evidence

- Definition verification: `evidence/p21-definition-verification.md`
- Auditor gate: `evidence/auditor-gate.md`
- Final planning report: `evidence/final-p21-planning-report.md`
- Round-1 audits: `evidence/audits/round-1/`
- Round-2 audits: `evidence/audits/round-2/` (all PASS)
