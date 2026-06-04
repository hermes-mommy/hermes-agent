# P7-016: Tasker Clipboard Profile — Auditor Gate

## Audit Scope

This gate covers the Tasker clipboard profile documentation and its alignment with Guinevere security, privacy, and consent requirements.

## Pre-Audit Checks

- [ ] Files exist in `docs/setup-evidence/P7/STEP-P7-016/`
- [ ] `tasker-clipboard.md` present
- [ ] `verification.md` present
- [ ] `auditor-gate.md` present (this file)

## 1. Documentation Completeness

| Section | Required | Present | Notes |
|---|---|---|---|
| Overview | Yes | YES/NO | |
| Prerequisites | Yes | YES/NO | |
| Profile Setup | Yes | YES/NO | |
| Event Format | Yes | YES/NO | |
| Secret Scanning Integration | Yes | YES/NO | |
| HMAC Signing | Yes | YES/NO | |
| Consent Requirements | Yes | YES/NO | |
| Privacy and Data Classification | Yes | YES/NO | |
| Battery Optimization | Yes | YES/NO | |
| Troubleshooting | Yes | YES/NO | |
| References | Yes | YES/NO | |

## 2. Security Audit

- [ ] No hardcoded secrets in any file
- [ ] HMAC signing references P7-017 correctly
- [ ] Secret scanning is described as server-side only (P7-009)
- [ ] No suggestion of client-side secret scanning
- [ ] Event transmission uses POST (not GET)
- [ ] HMAC signature included in request headers

**Finding:** PASS / NEEDS REVIEW / FAIL

## 3. Privacy Audit

- [ ] Clipboard data classified as Restricted (highest sensitivity)
- [ ] Redaction pipeline explained: scan then replace with `[REDACTED]`
- [ ] Events are preserved after redaction (not dropped)
- [ ] Raw clipboard text scanned before storage
- [ ] No real clipboard content used in examples
- [ ] Synthetic examples only (test keys, fake passwords)

**Finding:** PASS / NEEDS REVIEW / FAIL

## 4. Consent Compliance

- [ ] Required consent scope stated: `surveillance.clipboard`
- [ ] Consent revocation behavior documented
- [ ] Reference to P7-012 for consent setup
- [ ] No bypass of consent mechanism described

**Finding:** PASS / NEEDS REVIEW / FAIL

## 5. Writing Quality Audit

- [ ] No em dashes used anywhere in the documentation
- [ ] No en dashes used as em dashes
- [ ] No AI-sounding phrases: "delve", "leverage", "utilize", "robust", "streamline", "facilitate"
- [ ] Natural contractions used
- [ ] Sentence length varies
- [ ] No filler openings
- [ ] Clear, direct language

**Finding:** PASS / NEEDS REVIEW / FAIL

## 6. Reference Accuracy

| Reference | Target | Correct | Notes |
|---|---|---|---|
| P7-009 | Secret Scanner | YES/NO | |
| P7-012 | Device Setup and Consent | YES/NO | |
| P7-017 | HMAC Signing | YES/NO | |

**Finding:** PASS / NEEDS REVIEW / FAIL

## 7. Technical Correctness

- [ ] Event format JSON matches specification
- [ ] Debounce rate documented (1 per 5 seconds)
- [ ] AutoTools requirement stated for Android 10+
- [ ] Tasker version requirement stated (5.8+)
- [ ] Android version differences explained
- [ ] Troubleshooting covers common failure modes
- [ ] Error handling described (log and continue, not block)

**Finding:** PASS / NEEDS REVIEW / FAIL

## 8. Anti-Pattern Scan

| Anti-Pattern | Check | Result |
|---|---|---|
| Real clipboard content | grep for non-synthetic patterns | PASS/FAIL |
| Hardcoded API keys | grep for `sk_`, `AKIA`, `ghp_` | PASS/FAIL |
| Em dashes | grep for `—` or `--` as em dash | PASS/FAIL |
| Client-side scanning suggestion | Review secret scanning section | PASS/FAIL |
| Files outside scope | Check all files are in STEP-P7-016 | PASS/FAIL |

## 9. Boundary Compliance

- [ ] No persona drift in documentation tone
- [ ] No consent violation in described behavior
- [ ] No surveillance overreach (consent-gated, redacted)
- [ ] No HARD STOP bypass described
- [ ] No intimate data in examples
- [ ] No raw surveillance data in artifacts

**Finding:** PASS / NEEDS REVIEW / FAIL

## 10. Cross-Reference Validation

Verify that referenced documents exist and are consistent:

- [ ] P7-009 (Secret Scanner) documentation exists and describes server-side scanning
- [ ] P7-012 (Device Setup) documentation exists and covers consent management
- [ ] P7-017 (HMAC Signing) documentation exists and describes HMAC-SHA256 implementation

## Audit Summary

| Category | Verdict |
|---|---|
| Documentation Completeness | PASS / NEEDS REVIEW / FAIL |
| Security | PASS / NEEDS REVIEW / FAIL |
| Privacy | PASS / NEEDS REVIEW / FAIL |
| Consent Compliance | PASS / NEEDS REVIEW / FAIL |
| Writing Quality | PASS / NEEDS REVIEW / FAIL |
| Reference Accuracy | PASS / NEEDS REVIEW / FAIL |
| Technical Correctness | PASS / NEEDS REVIEW / FAIL |
| Anti-Pattern Scan | PASS / NEEDS REVIEW / FAIL |
| Boundary Compliance | PASS / NEEDS REVIEW / FAIL |
| Cross-Reference Validation | PASS / NEEDS REVIEW / FAIL |

## Overall Verdict

**PASS** / **NEEDS REVIEW** / **FAIL**

## Findings and Recommendations

### Critical Findings
_List any FAIL items with specific details and remediation steps._

### Minor Findings
_List any NEEDS REVIEW items with recommendations._

### Positive Observations
_Note any particularly good practices observed._

## Auditor Sign-Off

Auditor: _________________
Date: _________________
Verdict: _________________
Next Action: _________________
