# P26 Global Recent Requests Fix Plan

Date: 2026-06-28
Scope: make dashboard `Recent Requests` reflect global 9Router history instead of per-worker in-memory ring state.

## What Was Requested
- User reported that dashboard `Recent Requests` appears to show only one worker's history.
- Desired outcome: recent requests should reflect global request history across PM2 workers.

## Current Known State
- `UsageStats.js` renders the widget from `stats.recentRequests`.
- `UsageStats.js` updates `recentRequests` from `/api/usage/stream` SSE.
- Prior runtime research documented process-memory globals such as `global._recentRing` and `global._statsEmitter`, which likely explain the per-worker view.
- Authoritative deployed 9Router source is on the VPS at `/root/9router`, not in this repo.

## Binding Decision
- Prefer fixing the backend data source so the widget receives global DB-backed recent requests, instead of trying to merge worker-local memory in the browser.

## Expected Files
- Source changes on authoritative 9Router backend files under `/root/9router`
- Evidence note in `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\fixes\`

## Forbidden Patterns
- `as any`
- `@ts-ignore`
- empty `catch`
- secret dumps
- fake global aggregation in the client without backend proof

## Required Commands
- inspect backend source for `/api/usage/stream` and usage stats helpers
- verify any recent-requests query uses durable global history (`usageHistory`) rather than worker-local ring only
- validate runtime behavior after patch

## Hard Rejection Criteria
- patch still depends on single-worker in-memory `recentRequests`
- PM2 worker count changes from 2
- secrets are exposed in logs or evidence
- validation cannot prove global source behavior
