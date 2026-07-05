# P26.1 9Router Source/Write-Path Inventory

Date: 2026-06-28
Scope: Guinevere repo local evidence plus production 9Router runtime at `root@49.12.82.34 -p 39999`
Endpoint: `http://100.104.210.75:20128/v1`
Mode: read-only production inspection; no restarts, installs, firewall edits, env dumps, DB writes, or payload reads.

## Verdict

Production 9Router writes request/usage/token/cost telemetry to SQLite at `/var/lib/9router/db/data.sqlite`.

The exact deployed write functions are:

| Data | Deployed function | Deployed source file | Tables |
|---|---|---|---|
| request/token/cost usage rows | `saveRequestUsage(entry)` | `/root/9router/src/lib/db/repos/usageRepo.js` and deployed copy `/root/9router/.next/standalone/src/lib/db/repos/usageRepo.js` | `usageHistory`, `usageDaily`, `_meta` |
| detailed request/response observability records | `saveRequestDetail(detail)` -> `flushToDatabase()` | `/root/9router/src/lib/db/repos/requestDetailsRepo.js` and deployed copy `/root/9router/.next/standalone/src/lib/db/repos/requestDetailsRepo.js` | `requestDetails` |
| legacy/import migration only | `runMigrationOnce()` migration inserts | `/root/9router/src/lib/db/migrate.js` and deployed copy `/root/9router/.next/standalone/src/lib/db/migrate.js` | `usageHistory`, `usageDaily`, `requestDetails` during import/migration, not normal request path |

Hot-path finding:

- `usageHistory`/`usageDaily` writes are triggered in request completion paths through `saveUsageStats(...)`. They are fire-and-forget (`.catch(() => {})`) but still scheduled from the request lifecycle immediately after response parsing/stream completion. Inside `saveRequestUsage`, SQLite writes run in one synchronous better-sqlite3 transaction.
- `requestDetails` writes are also triggered from request success/error paths. `saveRequestDetail` first pushes to an in-memory `writeBuffer`; SQLite write is deferred until batch threshold or timer, except threshold-triggered flush is started immediately from the request path. This is already a write buffer, but not Redis-backed.
- `appendRequestLog(...)` is currently a no-op and does not write a DB request log.
- `trackPendingRequest(...)` updates in-memory counters only.

Confidence: High for SQLite write functions and hot-path trigger locations; Medium for runtime-effective compiled chunk equivalence because the readable source and `.next/standalone/src` are present, and compiled chunks contain the same SQL, but I did not reverse-map every minified bundle symbol.

## Production Runtime Inventory

Observed production runtime:

```text
hostname: ninerouter-vps
date: 2026-06-28T00:17:49+07:00
tailscale ip: 100.104.210.75
listener: 0.0.0.0:20128 owned by PM2 v7.0.1 daemon
systemd 9router: inactive, disabled
PM2: 9router v0.5.8, cluster mode, 2 online workers
worker processes: next-server (v16.2.9), PIDs 43086 and 43093 at inspection time
PM2 cwd: /root/9router/.next/standalone
PM2 script: custom-server.js
```

Relevant deployed files:

```text
/root/9router/.next/standalone/custom-server.js
/root/9router/.next/standalone/ecosystem.config.js
/root/9router/.next/standalone/server.js
/root/9router/src/sse/handlers/chat.js
/root/9router/open-sse/handlers/chatCore.js
/root/9router/open-sse/handlers/chatCore/requestDetail.js
/root/9router/open-sse/handlers/chatCore/nonStreamingHandler.js
/root/9router/open-sse/handlers/chatCore/streamingHandler.js
/root/9router/open-sse/handlers/chatCore/sseToJsonHandler.js
/root/9router/src/lib/usageDb.js
/root/9router/src/lib/requestDetailsDb.js
/root/9router/src/lib/db/index.js
/root/9router/src/lib/db/driver.js
/root/9router/src/lib/db/paths.js
/root/9router/src/lib/db/repos/usageRepo.js
/root/9router/src/lib/db/repos/requestDetailsRepo.js
/root/9router/.next/standalone/src/lib/db/repos/usageRepo.js
/root/9router/.next/standalone/src/lib/db/repos/requestDetailsRepo.js
```

The app-facing DB path is derived by code:

```text
src/lib/db/paths.js:5 export const DB_DIR = path.join(DATA_DIR, "db");
src/lib/db/paths.js:6 export const DATA_FILE = path.join(DB_DIR, "data.sqlite");
```

Local/P26 evidence and live production both identify the production DB as:

```text
/var/lib/9router/db/data.sqlite
```

## SQLite Tables Observed

Read-only schema/count snapshot from production:

```text
CREATE TABLE usageHistory (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, provider TEXT, model TEXT, connectionId TEXT, apiKey TEXT, endpoint TEXT, promptTokens INTEGER DEFAULT 0, completionTokens INTEGER DEFAULT 0, cost REAL DEFAULT 0, status TEXT, tokens TEXT, meta TEXT);
CREATE INDEX idx_uh_ts ON usageHistory(timestamp DESC);
CREATE INDEX idx_uh_provider ON usageHistory(provider);
CREATE INDEX idx_uh_model ON usageHistory(model);
CREATE INDEX idx_uh_conn ON usageHistory(connectionId);

CREATE TABLE usageDaily (dateKey TEXT PRIMARY KEY, data TEXT NOT NULL);

CREATE TABLE requestDetails (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, provider TEXT, model TEXT, connectionId TEXT, status TEXT, data TEXT NOT NULL);
CREATE INDEX idx_rd_ts ON requestDetails(timestamp DESC);
CREATE INDEX idx_rd_provider ON requestDetails(provider);
CREATE INDEX idx_rd_model ON requestDetails(model);
CREATE INDEX idx_rd_conn ON requestDetails(connectionId);
```

Counts at inspection:

```text
usageHistory_count: 8573
usageDaily_count: 3
requestDetails_count: 1000
```

DB files at inspection:

```text
-rw-r--r-- 1 root root 920M Jun 28 00:16 /var/lib/9router/db/data.sqlite
-rw-r--r-- 1 root root  96K Jun 28 00:17 /var/lib/9router/db/data.sqlite-shm
-rw-r--r-- 1 root root  44M Jun 28 00:17 /var/lib/9router/db/data.sqlite-wal
```

No `requestDetails.data`, token JSON values, env values, provider credentials, API keys, request bodies, or response bodies were printed.

## Request Path

The public OpenAI-compatible routes are thin wrappers:

```text
src/app/api/v1/chat/completions/route.js:29 export async function POST(request) {
src/app/api/v1/chat/completions/route.js:31   await ensureInitialized();
src/app/api/v1/chat/completions/route.js:33   return await handleChat(request);

src/app/api/v1/responses/route.js:27 export async function POST(request) {
src/app/api/v1/responses/route.js:28   await ensureInitialized();
src/app/api/v1/responses/route.js:29   return await handleChat(request);

src/app/api/v1/messages/route.js:32 export async function POST(request) {
src/app/api/v1/messages/route.js:33   await ensureInitialized();
src/app/api/v1/messages/route.js:34   return await handleChat(request);
```

`handleChat` then calls `handleSingleModelChat`, which calls `handleChatCore`:

```text
src/sse/handlers/chat.js:244 const result = await handleChatCore({
src/sse/handlers/chat.js:245   body: { ...body, model: `${provider}/${model}` },
src/sse/handlers/chat.js:249   clientRawRequest,
src/sse/handlers/chat.js:250   connectionId: credentials.connectionId,
src/sse/handlers/chat.js:252   apiKey,
```

`handleChatCore` imports telemetry functions from the DB shim:

```text
open-sse/handlers/chatCore.js:14 import { trackPendingRequest, appendRequestLog, saveRequestDetail } from "@/lib/usageDb.js";
open-sse/handlers/chatCore/requestDetail.js:1 import { saveRequestUsage, appendRequestLog, saveRequestDetail } from "@/lib/usageDb.js";
src/lib/usageDb.js:1 // Shim -> re-export from new SQLite-based DB layer (src/lib/db/)
src/lib/db/index.js:60   statsEmitter, trackPendingRequest, getActiveRequests,
src/lib/db/index.js:61   saveRequestUsage, getUsageHistory, getUsageStats, getChartData,
src/lib/db/index.js:67   saveRequestDetail, getRequestDetails, getRequestDetailById,
```

## Usage/Token/Cost Write Path

`saveUsageStats(...)` normalizes usage tokens and calls `saveRequestUsage(...)` fire-and-forget:

```text
open-sse/handlers/chatCore/requestDetail.js:75 export function saveUsageStats({ provider, model, tokens, connectionId, apiKey, endpoint, label = "USAGE" }) {
open-sse/handlers/chatCore/requestDetail.js:81   if (inTokens === 0 && outTokens === 0) return;
open-sse/handlers/chatCore/requestDetail.js:87   // Normalize to OpenAI token shape for storage
open-sse/handlers/chatCore/requestDetail.js:93   saveRequestUsage({
open-sse/handlers/chatCore/requestDetail.js:94     provider: provider || "unknown",
open-sse/handlers/chatCore/requestDetail.js:95     model: model || "unknown",
open-sse/handlers/chatCore/requestDetail.js:96     tokens: normalized,
open-sse/handlers/chatCore/requestDetail.js:97     timestamp: new Date().toISOString(),
open-sse/handlers/chatCore/requestDetail.js:98     connectionId: connectionId || undefined,
open-sse/handlers/chatCore/requestDetail.js:99     apiKey: apiKey || undefined,
open-sse/handlers/chatCore/requestDetail.js:100    endpoint: endpoint || null
open-sse/handlers/chatCore/requestDetail.js:101  }).catch(() => {});
```

Non-streaming completion path:

```text
open-sse/handlers/chatCore/nonStreamingHandler.js:175 const usage = extractUsageFromResponse(responseBody);
open-sse/handlers/chatCore/nonStreamingHandler.js:176 appendLog({ tokens: usage, status: "200 OK" });
open-sse/handlers/chatCore/nonStreamingHandler.js:177 saveUsageStats({ provider, model, tokens: usage, connectionId, apiKey, endpoint: clientRawRequest?.endpoint });
```

Forced SSE-to-JSON completion paths:

```text
open-sse/handlers/chatCore/sseToJsonHandler.js:125 const usage = jsonResponse.usage || {};
open-sse/handlers/chatCore/sseToJsonHandler.js:126 appendLog({ tokens: usage, status: "200 OK" });
open-sse/handlers/chatCore/sseToJsonHandler.js:127 saveUsageStats({ provider, model, tokens: usage, connectionId, apiKey, endpoint: clientRawRequest?.endpoint });

open-sse/handlers/chatCore/sseToJsonHandler.js:201 const usage = parsed.usage || {};
open-sse/handlers/chatCore/sseToJsonHandler.js:202 appendLog({ tokens: usage, status: "200 OK" });
open-sse/handlers/chatCore/sseToJsonHandler.js:203 saveUsageStats({ provider, model, tokens: usage, connectionId, apiKey, endpoint: clientRawRequest?.endpoint });
```

Streaming completion path:

```text
open-sse/handlers/chatCore.js:321 // Streaming response
open-sse/handlers/chatCore.js:322 const { onStreamComplete } = buildOnStreamComplete({ ...sharedCtx });
open-sse/handlers/chatCore.js:323 return handleStreamingResponse({ ...sharedCtx, providerResponse, sourceFormat, targetFormat, userAgent, reqLogger, toolNameMap, streamController, onStreamComplete });

open-sse/handlers/chatCore/streamingHandler.js:83 const onStreamComplete = (contentObj, usage, ttftAt) => {
open-sse/handlers/chatCore/streamingHandler.js:104   saveUsageStats({ provider, model, tokens: usage, connectionId, apiKey, endpoint: clientRawRequest?.endpoint, label: "STREAM USAGE" });
```

Actual SQLite writes:

```text
src/lib/db/repos/usageRepo.js:243 export async function saveRequestUsage(entry) {
src/lib/db/repos/usageRepo.js:245   const db = await getAdapter();
src/lib/db/repos/usageRepo.js:248   entry.cost = await calculateCost(entry.provider, entry.model, entry.tokens);
src/lib/db/repos/usageRepo.js:254   // All 3 writes (history insert, daily upsert, lifetime counter) in ONE transaction.
src/lib/db/repos/usageRepo.js:256   db.transaction(() => {
src/lib/db/repos/usageRepo.js:257     db.run(
src/lib/db/repos/usageRepo.js:258       `INSERT INTO usageHistory(timestamp, provider, model, connectionId, apiKey, endpoint, promptTokens, completionTokens, cost, status, tokens, meta) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
src/lib/db/repos/usageRepo.js:267     const dateKey = getLocalDateKey(entry.timestamp);
src/lib/db/repos/usageRepo.js:268     const row = db.get(`SELECT data FROM usageDaily WHERE dateKey = ?`, [dateKey]);
src/lib/db/repos/usageRepo.js:274     db.run(`INSERT INTO usageDaily(dateKey, data) VALUES(?, ?) ON CONFLICT(dateKey) DO UPDATE SET data = excluded.data`, [dateKey, stringifyJson(day)]);
src/lib/db/repos/usageRepo.js:277     const cur = db.get(`SELECT value FROM _meta WHERE key = 'totalRequestsLifetime'`);
src/lib/db/repos/usageRepo.js:279     db.run(`INSERT INTO _meta(key, value) VALUES('totalRequestsLifetime', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value`, [String(next)]);
```

Cost is calculated immediately before the transaction:

```text
src/lib/db/repos/usageRepo.js:113 async function calculateCost(provider, model, tokens) {
src/lib/db/repos/usageRepo.js:116   const { getPricingForModel } = await import("./pricingRepo.js");
src/lib/db/repos/usageRepo.js:121   const inputTokens = tokens.prompt_tokens || tokens.input_tokens || 0;
src/lib/db/repos/usageRepo.js:131   const outputTokens = tokens.completion_tokens || tokens.output_tokens || 0;
src/lib/db/repos/usageRepo.js:134   const reasoningTokens = tokens.reasoning_tokens || 0;
```

Conclusion: usage/token/cost writes do happen from request completion code. They are not awaited by callers, but they are still initiated from the hot request lifecycle and perform synchronous SQLite transaction work when the async function runs.

## Request Details Write Path

`saveRequestDetail(...)` is triggered on provider errors:

```text
open-sse/handlers/chatCore.js:240 trackPendingRequest(model, provider, connectionId, false, true);
open-sse/handlers/chatCore.js:241 appendRequestLog({ model, provider, connectionId, status: `FAILED ${error.name === "AbortError" ? 499 : HTTP_STATUS.BAD_GATEWAY}` }).catch(() => { });
open-sse/handlers/chatCore.js:242 saveRequestDetail(buildRequestDetail({

open-sse/handlers/chatCore.js:285 trackPendingRequest(model, provider, connectionId, false, true);
open-sse/handlers/chatCore.js:287 appendRequestLog({ model, provider, connectionId, status: `FAILED ${statusCode}` }).catch(() => { });
open-sse/handlers/chatCore.js:288 saveRequestDetail(buildRequestDetail({
```

Non-streaming success path:

```text
open-sse/handlers/chatCore/nonStreamingHandler.js:220 const totalLatency = Date.now() - requestStartTime;
open-sse/handlers/chatCore/nonStreamingHandler.js:221 saveRequestDetail(buildRequestDetail({
open-sse/handlers/chatCore/nonStreamingHandler.js:234 }, { endpoint: clientRawRequest?.endpoint || null })).catch(err => {
```

Streaming path writes an initial detail and later updates/saves final content under the same generated id:

```text
open-sse/handlers/chatCore/streamingHandler.js:57 const streamDetailId = `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
open-sse/handlers/chatCore/streamingHandler.js:58 saveRequestDetail(buildRequestDetail({
open-sse/handlers/chatCore/streamingHandler.js:67 }, { id: streamDetailId })).catch(err => {

open-sse/handlers/chatCore/streamingHandler.js:91 saveRequestDetail(buildRequestDetail({
open-sse/handlers/chatCore/streamingHandler.js:100 }, { id: streamDetailId })).catch(err => {
```

`saveRequestDetail(...)` buffers before DB write:

```text
src/lib/db/repos/requestDetailsRepo.js:42 let writeBuffer = [];
src/lib/db/repos/requestDetailsRepo.js:43 let flushTimer = null;
src/lib/db/repos/requestDetailsRepo.js:44 let isFlushing = false;

src/lib/db/repos/requestDetailsRepo.js:125 export async function saveRequestDetail(detail) {
src/lib/db/repos/requestDetailsRepo.js:126   const config = await getObservabilityConfig();
src/lib/db/repos/requestDetailsRepo.js:127   if (!config.enabled) return;
src/lib/db/repos/requestDetailsRepo.js:129   writeBuffer.push(detail);
src/lib/db/repos/requestDetailsRepo.js:131   // Trigger immediate flush if batch threshold reached.
src/lib/db/repos/requestDetailsRepo.js:133   if (writeBuffer.length >= config.batchSize) {
src/lib/db/repos/requestDetailsRepo.js:135     flushToDatabase().catch((e) => console.error("[requestDetailsRepo] flush err:", e));
src/lib/db/repos/requestDetailsRepo.js:136   } else if (!flushTimer) {
src/lib/db/repos/requestDetailsRepo.js:137     flushTimer = setTimeout(() => {
src/lib/db/repos/requestDetailsRepo.js:139       flushToDatabase().catch(() => {});
src/lib/db/repos/requestDetailsRepo.js:140     }, config.flushIntervalMs);
```

Actual SQLite write and prune:

```text
src/lib/db/repos/requestDetailsRepo.js:71 async function flushToDatabase() {
src/lib/db/repos/requestDetailsRepo.js:77   while (writeBuffer.length > 0) {
src/lib/db/repos/requestDetailsRepo.js:78     const items = writeBuffer.splice(0, writeBuffer.length);
src/lib/db/repos/requestDetailsRepo.js:79     const db = await getAdapter();
src/lib/db/repos/requestDetailsRepo.js:82     db.transaction(() => {
src/lib/db/repos/requestDetailsRepo.js:83       for (const item of items) {
src/lib/db/repos/requestDetailsRepo.js:103        db.run(
src/lib/db/repos/requestDetailsRepo.js:104          `INSERT INTO requestDetails(id, timestamp, provider, model, connectionId, status, data) VALUES(?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET timestamp = excluded.timestamp, provider = excluded.provider, model = excluded.model, connectionId = excluded.connectionId, status = excluded.status, data = excluded.data`,
src/lib/db/repos/requestDetailsRepo.js:109      const cnt = db.get(`SELECT COUNT(*) as c FROM requestDetails`);
src/lib/db/repos/requestDetailsRepo.js:111        db.run(
src/lib/db/repos/requestDetailsRepo.js:112          `DELETE FROM requestDetails WHERE id IN (SELECT id FROM requestDetails ORDER BY timestamp ASC LIMIT ?)`,
```

Conclusion: requestDetails writes are request-triggered but buffered. The normal case does not synchronously write on every request; it writes on batch threshold, timer, or shutdown. However, the batch-threshold branch can start a flush immediately from the request path.

## Other DB Writes Found

The grep inventory also found non-telemetry DB writes in normal application/admin paths:

```text
src/lib/db/repos/settingsRepo.js
src/lib/db/repos/nodesRepo.js
src/lib/db/repos/pricingRepo.js
src/lib/db/repos/connectionsRepo.js
src/lib/db/repos/combosRepo.js
src/lib/db/repos/disabledModelsRepo.js
src/lib/db/repos/proxyPoolsRepo.js
src/lib/db/repos/apiKeysRepo.js
src/lib/db/helpers/metaStore.js
src/lib/db/helpers/kvStore.js
```

Those are not usage/request/token/cost hot-path telemetry writes except `_meta.totalRequestsLifetime` inside `saveRequestUsage`.

Migration/import writes:

```text
src/lib/db/migrate.js:177 INSERT INTO usageHistory(...)
src/lib/db/migrate.js:191 INSERT OR REPLACE INTO usageDaily(...)
src/lib/db/migrate.js:209 INSERT OR REPLACE INTO requestDetails(...)
```

These are startup/import migration paths, not per-request writes.

## Commands Run

Local read-only:

```powershell
Get-Content -LiteralPath AGENTS.md -Raw
git status --short
rg --files
rg -n "9router|nine|requestDetails|request_details|usage|token|cost|sqlite|better-sqlite|dashboard|write|insert|update" docs/setup-evidence/P26 research-reports vps-mirror ecosystem.config.js package.json pyproject.toml -S
rg -n "9router|requestDetails|request_details|usage|token|cost|sqlite|better-sqlite|INSERT|UPDATE|db\.prepare|\.run\(|Database\(" -S --glob '!node_modules/**' --glob '!**/.git/**'
Get-Content -LiteralPath vps-mirror\systemd-live\guinevere-9router.service -Raw
Get-Content -LiteralPath docs\setup-evidence\P26\p25-cluster-inventory.md -Raw
Get-Content -LiteralPath docs\setup-evidence\P26\requestdetails-autoprune\research\current-dashboard-db-ground-truth.md -Raw
Get-Content -LiteralPath docs\setup-evidence\P26\highend-2worker-tuning\research\current-runtime-ground-truth.md -Raw
```

Production read-only:

```bash
ssh -p 39999 root@49.12.82.34 "hostname; date -Is; pgrep -af 9router; pgrep -af 'custom-server|next-server|pm2'; pm2 list"
ssh -p 39999 root@49.12.82.34 "ls -ld /root/9router /root/9router/.next /root/9router/.next/standalone /var/lib/9router /var/lib/9router/db 2>/dev/null"
ssh -p 39999 root@49.12.82.34 "ls -lh /var/lib/9router/db/data.sqlite* 2>/dev/null"
ssh -p 39999 root@49.12.82.34 "systemctl cat 9router --no-pager 2>/dev/null | sed -n '1,80p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && find . -maxdepth 4 -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.mjs' -o -name '*.cjs' \) | sed 's#^./##' | sort | head -250"
ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite '.schema usageHistory'"
ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite '.schema usageDaily'"
ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite '.schema requestDetails'"
ssh -p 39999 root@49.12.82.34 "sqlite3 /var/lib/9router/db/data.sqlite 'select count(1) from usageHistory;' ; sqlite3 /var/lib/9router/db/data.sqlite 'select count(1) from usageDaily;' ; sqlite3 /var/lib/9router/db/data.sqlite 'select count(1) from requestDetails;'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -RIn --exclude-dir=node_modules --exclude-dir=.git --exclude='*.map' -e usageHistory -e usageDaily -e requestDetails -e 'better-sqlite3' -e 'data.sqlite' -e 'INSERT INTO' -e 'UPDATE usage' -e recordUsage -e trackUsage -e logRequest app lib server cli src .next/standalone 2>/dev/null | head -300"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba src/lib/db/repos/usageRepo.js | sed -n '1,140p;230,290p;680,715p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba src/lib/db/repos/requestDetailsRepo.js | sed -n '1,190p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -RIn --exclude-dir=node_modules --exclude-dir=.git --exclude='*.map' -e addUsage -e recordRequestDetail -e addRequestDetails -e recordRequestDetails -e requestDetailsRepo -e usageRepo app lib server cli src .next/standalone/src .next/standalone/.next/server/app/api/v1 2>/dev/null | head -250"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba src/lib/db/index.js | sed -n '1,140p' && nl -ba src/lib/db/paths.js | sed -n '1,80p' && nl -ba src/lib/db/driver.js | sed -n '1,110p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -RIn --exclude-dir=node_modules --exclude-dir=.git --exclude='*.map' -e saveRequestUsage -e saveRequestDetail -e trackPendingRequest -e getActiveRequests app lib server cli src .next/standalone/src .next/standalone/.next/server/app/api 2>/dev/null | head -300"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && find src/lib src/app/api/v1 -maxdepth 5 -type f | sort | sed -n '1,260p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -RIn --exclude-dir=node_modules --exclude-dir=.git --exclude='*.map' -e 'usageDb' -e 'requestDetailsDb' -e 'trackPending' -e 'activeRequests' -e 'prompt_tokens' -e 'completion_tokens' src/app/api/v1 src/lib .next/standalone/src/app/api/v1 .next/standalone/.next/server/app/api/v1 2>/dev/null | head -350"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba src/app/api/v1/chat/completions/route.js | sed -n '1,240p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba src/app/api/v1/responses/route.js | sed -n '1,260p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba src/app/api/v1/messages/route.js | sed -n '1,260p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba src/sse/handlers/chat.js | sed -n '1,260p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && grep -RIn --exclude-dir=.git --exclude='*.map' -e 'saveRequestUsage' -e 'saveRequestDetail' -e 'trackPendingRequest' -e 'usageDb' -e 'requestDetailsDb' open-sse src/sse .next/standalone/src/sse .next/standalone/.next/server/chunks 2>/dev/null | head -400"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba open-sse/handlers/chatCore.js | sed -n '1,320p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba open-sse/handlers/chatCore/requestDetail.js | sed -n '1,180p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba open-sse/handlers/chatCore/nonStreamingHandler.js | sed -n '1,280p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba open-sse/handlers/chatCore/streamingHandler.js | sed -n '1,170p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba open-sse/handlers/chatCore/sseToJsonHandler.js | sed -n '1,240p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba open-sse/utils/stream.js | sed -n '280,335p'"
ssh -p 39999 root@49.12.82.34 "cd /root/9router && nl -ba open-sse/utils/usageTracking.js | sed -n '300,365p'"
ssh -p 39999 root@49.12.82.34 "ss -ltnp | grep ':20128' || true; systemctl is-active 9router 2>/dev/null || true; systemctl is-enabled 9router 2>/dev/null || true; systemctl cat 9router --no-pager 2>/dev/null | sed -n '1,70p'; tailscale ip -4 2>/dev/null || true"
```

Quoting failures encountered and discarded:

```text
One PM2 JSON parsing command was rejected locally by PowerShell before SSH due arrow-function parsing.
One sqlite count command was rejected locally by PowerShell because count(*) was parsed before SSH.
One grep command had remote shell quoting issues around alternation/metacharacters.
No production mutation occurred from these failures.
```

## Local Evidence Inputs

Relevant existing local artifacts read:

```text
docs/setup-evidence/P26/p25-cluster-inventory.md
docs/setup-evidence/P26/requestdetails-autoprune/research/current-dashboard-db-ground-truth.md
docs/setup-evidence/P26/highend-2worker-tuning/research/current-runtime-ground-truth.md
vps-mirror/systemd-live/guinevere-9router.service
ecosystem.config.js
research-reports/9router-usage-persistence-audit.md
research-reports/9router-stream-pipeline-map.md
research-reports/9router-dashboard-details-trace.md
```

Local evidence already stated:

```text
Usage logging writes to usageHistory/usageDaily.
SQLite WAL handles concurrent reads and one writer.
Prior lock evidence included SQLITE_BUSY / SQLITE_BUSY_SNAPSHOT / database is locked in PM2 logs.
requestDetails was large: prior snapshot had 1000 rows and about 601 MB of requestDetails.data.
```

## Unknowns

- I did not inspect `requestDetails.data` payloads, provider credentials, env files, API keys, or raw token JSON. This was intentional.
- I did not run a live request/load test, so this report proves source/runtime write paths, not per-request latency impact under current traffic.
- I did not reverse-map every minified `.next/standalone/.next/server/chunks/*.js` symbol. I confirmed readable source, standalone source copies, route wrappers, and compiled chunks containing the same SQL strings.
- `requestDetails` observability enablement is runtime-config dependent (`settings.enableObservability2` or `OBSERVABILITY_ENABLED`). Current DB growth and row count prove it has been enabled recently, but I did not read settings payload values.
- PM2 cluster has two workers sharing SQLite. This report identifies write sources but does not quantify lock contention probability after prior tuning/autoprune.

## Boundary Compliance

- Production inspection was read-only.
- No production service was restarted or reloaded.
- No firewall, systemd, PM2, Tailscale, package, or env changes were made.
- No secrets, bearer tokens, cookies, DB passwords, provider credentials, raw request bodies, raw response bodies, or `requestDetails.data` content were printed.
- Only repository output created by this task is this markdown file:
  `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\research\write-path-inventory.md`

## Footer

Prepared for P26.1 redis-write-buffer research. This is an inventory artifact, not an implementation or production change.
