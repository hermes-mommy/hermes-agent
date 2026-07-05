# P26.1 PM2 Cutover Proof

Date: 2026-06-28
Live target: `root@49.12.82.34 -p 39999`

## What Was Done
- Verified the live PM2 process definition after the stale-runtime cutover.
- Captured the post-cutover `pm2 show 9router` process metadata.

## Files Changed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\pm2-cutover-proof.md`

## Validation Results
- Live PM2 process now reports:
  - script path: `/root/9router/.next/standalone/server.js`
  - exec cwd: `/root/9router/.next/standalone`
  - exec mode: `cluster_mode`
  - worker count: `2`
  - worker ids: `3`, `4`
  - restart count: `0`
- This closes the earlier ambiguity where the stale runtime had been observed on:
  - `/root/9router/.next/standalone/custom-server.js`
  - with process cwd showing `(deleted)`

## Interpretation
- The currently active PM2 runtime is no longer the deleted stale standalone bundle.
- The live app process now points at the expected standalone `server.js` entrypoint that was validated to publish Redis stream events with non-empty `streamId`.

## Doc-Sync Impact
- Architecture and final status docs should cite this file when asserting the PM2 entrypoint after cutover.

## Boundary Compliance
- Read-only verification only.
- No runtime mutation occurred during this proof capture.

## Rollback / Re-run Safety
- Safe to re-run.

## Auditor Gate
- Required input for `architecture`, `runtime-deploy`, and `evidence-docs`.

## Security Scan
- No secrets recorded.

## Acceptance Criteria Mapping
- post-cutover PM2 entrypoint explicitly proven: pass
- stale `custom-server.js` ambiguity closed: pass

## Footer
- PM2 cutover verdict: `ACTIVE ENTRYPOINT PROVEN`.

