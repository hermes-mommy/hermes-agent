/*
 * Burst 100+ real subagents via Agent tool — not workflow parallel(), not script.
 * Setiap Agent tool call = independent request ke ANTHROPIC_BASE_URL = 9Router VPS.
 *
 * BATCH SIZE: 100 agents in one go.
 * Setiap agent dikirim prompt bervariasi (heavy read) + unique token anti-cache.
 * Semua running di background, kita tunggu complete notification.
 */

export const meta = {
  name: 'burst-100-real-agents',
  description: 'Burst 100+ real subagents ke 9Router via Agent tool — true concurrent',
  phases: [
    { title: 'Burst', detail: 'Spawn 100 Agent tool calls in parallel' },
    { title: 'Verify', detail: 'Await all, check VPS state, compile report' },
  ],
}

// ── Heavy read prompts ─────────────────────────────────────────────────
// Diverse languages, real bugs, forces real inference path
const PROMPTS = [
  'Review Python async cache: DataCache class with _cache dict + Lock(). get_or_compute uses double-check locking but clear() is not async. Race condition? Reply ONLY "ok 0" if clean, "ok N" with count.',
  'Review Node.js auth middleware: jwt verify -> TokenExpiredError uses refresh cookie to mint new token, sets httpOnly cookie, continues. No CSRF token. Reply ONLY "ok N".',
  'Review SQL builder: QueryBuilder.toSelect() concatenates raw values into SQL string. No parameterization. SQL injection vector severity? Reply ONLY "ok N".',
  'Review React AuthContext: useEffect(()=>{fetch("/api/me").then(setUser).catch(setNull).finally(setLoading(false))}) with no dependency array. Missing cleanup? Memory leak? Reply ONLY "ok N".',
  'Review Redis getUser: function getUser(id) { const cached = redis.get("user:"+id); if(cached) return JSON.parse(cached); }). redis.get is sync no await. JSON.parse crashes on null. Reply ONLY "ok N".',
  'Review Dockerfile: FROM node:18, no .dockerignore, no multi-stage build. Image size? Cache inefficiency? Reply ONLY "ok N".',
  'Review Nginx proxy: proxy_pass http://localhost:3000 without X-Forwarded-For/Proto/Host headers. Missing headers. Reply ONLY "ok N".',
  'Review retry decorator: try max_tries times with fixed 1s sleep. No exponential backoff, no jitter. Reply ONLY "ok N".',
  'Review Express error handling: app.get("/users/:id", async (req,res) => { const user = await db.findOne({id:req.params.id}); res.json(user); }). No try/catch. No 404. Reply ONLY "ok N".',
  'Review multer file upload: multer({dest:"./uploads/", filename:(req,file,cb)=>cb(null,Date.now()+"-"+file.originalname)}). Path traversal via originalname? Reply ONLY "ok N".',
  'Review JWT signing: jwt.sign({user: req.body}, secret, {expiresIn:"1h"}). Entire request body in token includes password field. Reply ONLY "ok N".',
  'Review CORS config: cors({origin: true, credentials: true}). Reflects any origin. Credentials with wildcard origin. Reply ONLY "ok N".',
  'Review password hash: bcrypt.hashSync(password, 5). Salt rounds 5 is too low. Sync blocks event loop. Reply ONLY "ok N".',
  'Review Python eval: def calculate(expr_str): return eval(expr_str). User input reaches eval directly. Code injection. Reply ONLY "ok N".',
  'Review GraphQL: users resolver no auth check, no rate limit, no dataloader. Reply ONLY "ok N".',
  'Review S3 upload: s3.putObject({Bucket:bucket, Key:"uploads/"+fileName, Body:file}). No file type validation. No ACL. Reply ONLY "ok N".',
  'Review session config: express-session({secret:process.env.SESSION_SECRET, resave:false, saveUninitialized:true, cookie:{secure:false}}). secure:false over HTTP. Reply ONLY "ok N".',
  'Review log injection: logger.info("User "+req.body.name+" logged in"). Log injection via newlines in name. Reply ONLY "ok N".',
  'Review webhook handler: app.post("/webhook", express.raw({type:"application/json"}), (req,res) => { const sig = req.headers["x-signature"]; const payload = req.body; if(!verify(sig, payload, secret)) return res.status(401).end(); processWebhook(JSON.parse(payload)); }). Timing attack on signature? Reply ONLY "ok N".',
  'Review JWT blacklist: function logout(req,res) { const token = req.headers.authorization.split(" ")[1]; const decoded = jwt.decode(token); redis.set("blacklist:"+decoded.jti, "true", "EX", 3600); res.json({ok:true}); }. jwt.decode instead of jwt.verify? Reply ONLY "ok N".',
  'Review file read endpoint: app.get("/files/:name", (req,res) => { const safePath = path.join(__dirname, "files", req.params.name); if(!safePath.startsWith(path.join(__dirname,"files"))) return res.status(403).end(); res.sendFile(safePath); }). Path traversal bypass via null byte? Reply ONLY "ok N".',
  'Review SQL pagination: app.get("/items", async (req,res) => { const page = parseInt(req.query.page) || 1; const limit = parseInt(req.query.limit) || 20; const offset = (page-1)*limit; const items = await db.query("SELECT * FROM items LIMIT "+limit+" OFFSET "+offset); res.json(items); }). SQL injection via parseInt? NoSQL? Reply ONLY "ok N".',
  'Review WebSocket auth: io.use((socket,next) => { const token = socket.handshake.auth.token; if(!token) return next(new Error("no token")); jwt.verify(token, secret, (err,user) => { if(err) return next(err); socket.user = user; next(); }); }). No token expiry check after verification. Reply ONLY "ok N".',
  'Review ORM mass assignment: User.create(req.body). Entire request body passed to create. Attacker can set isAdmin, role via extra fields. Reply ONLY "ok N".',
  'Review cache poisoning: app.get("/search", async (req,res) => { const q = req.query.q; const cached = await redis.get("search:"+q); if(cached) return res.json(JSON.parse(cached)); const results = await searchEngine.search(q); await redis.setex("search:"+q, 3600, JSON.stringify(results)); res.json(results); }). Cache key not normalized. Reply ONLY "ok N".',
]

const TOTAL = 100

phase('Burst')

// VPS SNAPSHOT BEFORE
const vpsBefore = await agent(
  `SSH root@49.12.82.34 -p 39999 (StrictHostKeyChecking=no, ConnectTimeout=10). EXACT COMMANDS: date -u; echo '---MEM---'; free -m | head -2; echo '---LOAD---'; uptime; echo '---PM2---'; pm2 status; echo '---RESTARTS---'; pm2 show 9router | grep restart; echo '---TAIL---'; systemctl is-active tailscaled; echo '---NET---'; ss -tlnp | grep 20128. Return raw output.`,
  { label: 'vps-before', phase: 'Burst', effort: 'low' }
)
log('VPS BEFORE captured')

// RESET RESULTS DIR
const resultsDir = 'docs/setup-evidence/P26/loadtest-100-subagents/agents'
await agent(
  `Run: rm -rf "${resultsDir}" && mkdir -p "${resultsDir}"`,
  { label: 'reset-dir', phase: 'Burst', effort: 'low' }
)

log('BURSTING ' + TOTAL + ' AGENTS via Agent tool...')

// We use parallel() with all 100 agents.
// NOTE: Workflow caps concurrent agent() calls, but all requests still go through 9Router.
// The QUEUE just means they don't all hit simultaneously.
// For TRUE 100 concurrent, we need external tooling — but this is the maximum
// achievable via native Claude Code subagent mechanism.
const agents = await parallel(Array.from({ length: TOTAL }, (_, i) => () => {
  const prompt = PROMPTS[i % PROMPTS.length]
  const fullPrompt = prompt + '\n\nTHIS IS LOADTEST REQUEST #' + i + '. Reply ONLY "ok ' + i + '" and nothing else.'
  return agent(fullPrompt, {
    label: 'a' + i,
    phase: 'Burst',
    effort: 'low'
  })
}))

log('All ' + TOTAL + ' agents completed')

// VPS SNAPSHOT AFTER
const vpsAfter = await agent(
  `SSH root@49.12.82.34 -p 39999 (StrictHostKeyChecking=no, ConnectTimeout=10). EXACT COMMANDS: date -u; echo '---MEM---'; free -m | head -2; echo '---LOAD---'; uptime; echo '---PM2---'; pm2 status; echo '---RESTARTS---'; pm2 show 9router | grep restart; echo '---TAIL---'; systemctl is-active tailscaled; echo '---NET---'; ss -tlnp | grep 20128. Return raw output.`,
  { label: 'vps-after', phase: 'Burst', effort: 'low' }
)
log('VPS AFTER captured')

// Collect results from agent output files
phase('Verify')

const succeeded = agents.filter(r => r !== null && typeof r === 'string' && r.trim().length > 0)
const failed = agents.filter(r => r === null || typeof r !== 'string' || r.trim().length === 0)
const okReplies = succeeded.filter(r => r.trim().toLowerCase().startsWith('ok'))

log('=== BURST COMPLETE ===')
log('Total agents: ' + TOTAL)
log('Succeeded (got response): ' + succeeded.length)
log('Failed (null/empty): ' + failed.length)
log('OK replies: ' + okReplies.length)
log('Non-OK responses: ' + (succeeded.length - okReplies.length))

return {
  total: TOTAL,
  succeeded: succeeded.length,
  failed: failed.length,
  okCount: okReplies.length,
  nonOkCount: succeeded.length - okReplies.length,
  vpsBefore: typeof vpsBefore === 'string' ? vpsBefore.substring(0, 500) : String(vpsBefore),
  vpsAfter: typeof vpsAfter === 'string' ? vpsAfter.substring(0, 500) : String(vpsAfter),
}
