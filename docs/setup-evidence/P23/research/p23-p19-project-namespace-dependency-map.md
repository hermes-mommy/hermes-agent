# P23 Research — P19 Project-Namespace Dependency Map

> **Status:** RESEARCH — no implementation requested.  
> **Date:** 2026-06-25  
> **Author:** Guinevere research subagent  
> **Caveat (updated 2026-06-25):** P19 definition is complete (definition pass); the namespace contract is forward-design and not yet enforced in runtime. P23-012 is gated on P19 namespace contract readiness, not on P19 implementation.

---

## 1. Objective

P23 “Embodied Operations / Personal OS Action Layer” adds action-oriented capabilities to Guinevere (browser/screen control, OS-level automation, device actuation). Those actions must be scoped to a project namespace from day one so that, once P19 Multi-Project Context is delivered, every action can be partitioned correctly across projects without a painful backfill or migration.

This document maps the **P19 project-namespace model** onto the **P23 action layer** and mirrors the P19 dependency design already approved for P22 Life Integration Hub, preserving behavioral consistency across all future phases.

**Scope of this artifact:**

- Define the namespace model P19 will provide.
- Define the pre-P19 and post-P19 identifier templates for P23 actions.
- Define namespace inheritance, collision-resolution, and migration rules.
- Define audit requirements for namespace switches and P23 action logging.
- State hard-rejection criteria for namespace-less P23 actions.
- Identify the forward-compat seam (`project_namespace` column / field) that P23 must carry today.
- Record the implementation-hold condition (P19 namespace contract readiness).

---

## 2. Sources Consulted

| # | Source | Path | Relevance |
|---|---|---|---|
| 1 | P19 README | `docs/setup-evidence/P19/README.md` | P19 definition complete (definition pass, 2026-06-25); lists 5 planned steps: registry + namespace model, memory partitioning, surveillance filters, agent-loop, operator switcher + audit trail. Namespace contract forward-design, not yet enforced in runtime. |
| 2 | P22 Life Integration Hub plan | `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` §P19 Project-Namespace Dependency Map | Provides the canonical P19 dependency pattern P23 must mirror exactly. |
| 3 | AGENTS.md §0.1 / §2.1 | `AGENTS.md` | Consent revocation absolute; namespaces isolate memory, surveillance, consent, and agent-loop per project. |

---

## 3. Findings

### 3.1 Namespace model P19 will provide

P19 will introduce a **project registry** and a **namespace model** that partitions the following Guinevere subsystems per project:

| P19 Capability | What it isolates | P23 Relevance |
|---|---|---|
| **Project registry** | Canonical list of projects, each with a stable slug, name, owner, and policy set. | P23 must look up a project slug before acting on its behalf. |
| **Namespace slug** | Stable identifier for a project namespace (e.g., `default`, `guinevere`, `work`, `p23-demo`). | Every P23 action row carries `project_namespace` and encodes the slug in its identifier. |
| **Per-project memory partitioning** | Memory graph, recall, and working context scoped to a project. | P23 action plans, observations, and outcomes must be stored under the correct namespace so P19 memory partitioning can route them later. |
| **Scoped surveillance filters** | Surveillance data tagged and filtered by project. | P23 screen/browser/OS recordings must be tagged with the namespace; do not leak cross-project recordings. |
| **Consent boundary per project** | Consent grants and revocations scoped to a namespace. | P23 must honor per-project consent; a revocation in namespace `work` does not affect `guinevere`. |
| **Project-aware agent loop** | The autonomous loop schedules and executes tasks within one namespace at a time, or explicitly switches. | P23 actions must declare which namespace they run in; the loop must pass that namespace to every P23 executor. |
| **Operator switcher + audit trail** | UI / command to switch active project and log every switch. | P23 must subscribe to project-switch events and reset or re-scope state accordingly; all actions log `from_namespace`, `to_namespace`, `actor`, `timestamp`, `correlation_id`. |

**Pre-P19 default namespace:**

Until P19 lands, every P23 action lives in the single default namespace:

```text
default
```

This mirrors P22’s pre-P19 default and avoids requiring a project registry before P23 can be prototyped.

### 3.2 Identifier templates

#### Pre-P19 identifier template

```text
p23:<executor>:<surface>:<action-id>
```

Components:

- `p23` — phase identifier, fixed.
- `<executor>` — the actor performing the action: `browser`, `os`, `screen`, `device`, `hermes`, `kernel`.
- `<surface>` — the target surface or integration: `obscura`, `desktop`, `discord`, `gmail`, `vps`, `file-system`.
- `<action-id>` — opaque, unique within executor+surface, lowercase kebab case.

Examples:

```text
p23:browser:obscura:nav-001
p23:os:desktop:click-042
p23:screen:obscura:ocr-007
p23:device:serial:send-003
```

#### Post-P19 identifier template

After P19 delivery, every identifier is prefixed with the project namespace:

```text
<project>:p23:<executor>:<surface>:<action-id>
```

Examples:

```text
guinevere:p23:browser:obscura:nav-001
work:p23:browser:obscura:nav-001
default:p23:os:desktop:click-042
```

**Rationale for prefix placement:**

- Mirrors P22 exactly (`<project>:p22:<domain>:<provider>:<resource-id>`).
- Keeps the phase token (`p23`) adjacent to the rest of the identifier, making phase-specific routing and log parsing consistent.
- Allows P19 to own the leading namespace segment and P23 to own everything after `p23:`.

### 3.3 Namespace inheritance rules

1. **Unqualified P23 actions fall back to `default`.**  
   Any action created before P19 is implicitly in namespace `default`.

2. **Project-specific actions are addressed by prefixing the project slug.**  
   Example: `work:p23:browser:obscura:nav-001`.

3. **P19 owns the project registry.**  
   P23 reads the registry read-only and maps action identifiers accordingly. P23 must never create, rename, or delete namespaces.

4. **Namespace is inherited from the active project context.**  
   If the operator or agent loop sets the active project to `work`, new P23 actions are created under `work` unless explicitly overridden.

5. **Explicit namespace on an action overrides the active context.**  
   A P23 action may carry a hard-coded `project_namespace`; the hard-coded value wins over the ambient context for that action only.

### 3.4 Collision-resolution policy

| Scenario | Rule |
|---|---|
| Same action ID across two projects | P19 namespace is authoritative; P23 stores `(project_namespace, executor, surface, action_id)` as a composite unique key. |
| Same executor+surface in two projects | Qualify with project slug; e.g., `guinevere:p23:browser:obscura:nav-001` vs `work:p23:browser:obscura:nav-001`. |
| P19 removes a namespace | P23 treats all actions in that namespace as **revoked**; executors refuse to start them and log `namespace_revoked`. |
| P19 renames a namespace | P19 issues a migration event; P23 rewrites internal mapping keys only, never external action identifiers. |
| Namespace slug collision | P19 registry is authoritative; P23 must treat slug conflicts as a registry error and escalate. |

### 3.5 Migration path (mirror P22 exactly)

**Phase 0 (now):**

- All P23 actions live in `default`.
- No `project_namespace` column is required yet, but P23 designs should reserve it.

**Phase 1 (P19 design freeze):**

- Add optional `project_namespace` column/field to every P23 table, audit row, artifact path, and in-memory action descriptor.
- Default value: `'default'`.
- Identifier parsing remains backward-compatible with the pre-P19 template.

**Phase 2 (P19 rollout):**

- Backfill `project_namespace = 'default'` for all existing P23 rows.
- Enable project-qualified lookups behind a feature flag.
- Update log aggregation and dashboards to group by `project_namespace`.

**Phase 3 (mature P19):**

- Remove the `default` assumption for new actions.
- Require an explicit `project_namespace` from P19 for every new P23 action.
- Keep `default` as a valid legacy namespace for historical rows and for contexts where no project is active.

### 3.6 Audit requirements

P19 owns the project registry and switch events; P23 reads these events read-only and appends its own action audit rows.

**Namespace-switch audit row**

| Field | Type | Description |
|---|---|---|
| `event_id` | UUID | Unique event identifier. |
| `from_namespace` | TEXT | Previous active namespace. |
| `to_namespace` | TEXT | New active namespace. |
| `actor` | TEXT | Who/what triggered the switch: `user:faiz`, `agent:guinevere`, `system:p19`. |
| `timestamp` | TIMESTAMPTZ | UTC switch time. |
| `correlation_id` | UUID | Ties the switch to the surrounding session/decision cycle. |
| `project_registry_version` | TEXT | Version/hash of the P19 registry at switch time. |

**P23 action audit row**

| Field | Type | Description |
|---|---|---|
| `action_id` | TEXT | Full identifier, e.g., `guinevere:p23:browser:obscura:nav-001`. |
| `project_namespace` | TEXT | Nullable, default `'default'`. |
| `executor` | TEXT | `browser`, `os`, `screen`, `device`, etc. |
| `surface` | TEXT | Target surface. |
| `operation` | TEXT | Human-readable action name. |
| `actor` | TEXT | `user:faiz`, `agent:guinevere`, `system:p23`. |
| `timestamp` | TIMESTAMPTZ | Start time. |
| `correlation_id` | UUID | Ties action to the decision cycle. |
| `result` | TEXT | `success`, `rate_limited`, `auth_failed`, `consent_denied`, `hard_stop`, `namespace_missing`. |
| `metadata` | JSONB | Extra context; no secrets or PII. |

**Audit invariants:**

- Every namespace switch is logged.
- Every P23 action row records the active `project_namespace`.
- Audit records are immutable (INSERT/SELECT only; UPDATE/DELETE blocked).
- Hash-chaining or equivalent tamper-evidence is recommended, mirroring P22 `audit.integration_api_log`.

### 3.7 Hard-rejection list

P23 code must **FAIL** in the following situations:

| # | Condition | Failure behavior |
|---|---|---|
| 1 | P23 action submitted without a `project_namespace` value. | Hard reject; log `namespace_missing`; do not execute. |
| 2 | P23 code attempts to create, rename, or delete a P19 namespace. | Hard reject; log `namespace_registry_violation`. |
| 3 | P23 action targets a namespace not present in the P19 registry (post-P19). | Hard reject; log `namespace_unknown`. |
| 4 | P23 action runs while active project context and explicit namespace disagree and no override rule is defined. | Hard reject; log `namespace_conflict`. |
| 5 | P23 stores action artifacts under a path missing the namespace segment (post-P19). | Hard reject; log `namespace_path_violation`. |

**Implementation-hold corollary:** Until P19 is defined, `project_namespace` is nullable/default `'default'`, but the field must still be present in every P23 data structure so the transition is mechanical rather than architectural.

### 3.8 Forward-compat seam

Every P23 artifact that may be partitioned by project must carry a nullable `project_namespace` field today, even though P19 is not started.

| Artifact | Required field | Default today | Post-P19 behavior |
|---|---|---|---|
| Action records | `project_namespace` | `'default'` | Required, looked up from P19. |
| Audit rows | `project_namespace` | `'default'` | Required, derived from action or switch event. |
| Artifact paths | `<namespace>/` prefix or `project_namespace` metadata | `default/` or omitted | Required prefix/segment. |
| In-memory action descriptors | `.project_namespace` | `'default'` | Required attribute. |
| Log streams | `project_namespace` dimension | `'default'` | Required label. |
| Feature flags | `p23:<namespace>:<flag>` or flag + `project_namespace` | `p23:default:<flag>` | Per-namespace flags. |
| Consent scopes | `project_namespace` qualifier | `default` | Per-namespace consent. |
| Memory entries | `project_namespace` tag | `default` | Partitioned by P19. |

**Design rule:** default `'default'` everywhere so that P19 can partition later without any backfill other than adding the project slug to new records.

---

## 4. Implications for P23 Design

### 4.1 Action executor interface

Every P23 executor (browser, OS, screen, device) must accept a `project_namespace` argument:

```python
class P23Action:
    project_namespace: str  # default "default" until P19
    executor: str
    surface: str
    action_id: str

    @property
    def qualified_id(self) -> str:
        return f"{self.project_namespace}:p23:{self.executor}:{self.surface}:{self.action_id}"
```

If `project_namespace` is missing, the executor must raise `NamespaceRequiredError`.

### 4.2 Database / storage schema

All P23 tables and artifact paths should reserve `project_namespace` now:

```sql
CREATE TABLE p23.actions (
    id BIGSERIAL PRIMARY KEY,
    project_namespace TEXT NOT NULL DEFAULT 'default',
    executor TEXT NOT NULL,
    surface TEXT NOT NULL,
    action_id TEXT NOT NULL,
    -- ...
    UNIQUE (project_namespace, executor, surface, action_id)
);
```

Artifact path convention (pre-P19 vs post-P19):

```text
evidence/p23/default/<executor>/<surface>/<action-id>.md
evidence/p23/<project>/<executor>/<surface>/<action-id>.md
```

### 4.3 Agent-loop integration

- The P20/P23 agent loop should pass the active `project_namespace` into every action invocation.
- On project switch, the loop must flush or re-scope per-project state and log the switch.
- If the loop attempts to run a P23 action without a namespace, the action layer must hard-reject it.

### 4.4 Consent and safety

- P23 must honor per-project consent scopes (read, write, destructive) once P19 defines them.
- A consent revocation in one namespace must not implicitly revoke consent in another.
- HARD STOP remains global across all namespaces (AGENTS.md §0.1).

### 4.5 Observability

- Logs, metrics, and traces must include `project_namespace` as a dimension.
- Dashboards should default to `default` and later allow per-project filtering.

---

## 5. Risks / Open Questions

| # | Risk / Open Question | Mitigation / Next Step |
|---|---|---|
| 1 | **P19 undefined.** P19 is NOT STARTED; its registry schema, slug rules, and switch-event API are unknown. | Treat P19 as an external dependency; do not implement P19 logic inside P23. Reserve only the nullable `project_namespace` field. |
| 2 | **Namespace slug format.** Will slugs allow `:`, `-`, `_`, digits? P23 identifier parsing depends on it. | Adopt P22 convention: lowercase kebab-case slugs matching `[a-z][a-z0-9\-]*`. Revisit when P19 is defined. |
| 3 | **Default namespace longevity.** Keeping `default` forever may create a “garbage namespace.” | Document a future cleanup policy (e.g., migrate personal-project actions to `guinevere` after P19 rollout). |
| 4 | **Cross-namespace action orchestration.** Will P23 actions every span multiple namespaces in a single workflow? | Default to single-namespace actions; multi-namespace workflows require explicit project-switch events and audit logging. |
| 5 | **Collision with P22 namespace identifiers.** Both P22 and P23 will prefix with project slug; ensure no parser confuses `p22:` and `p23:` tokens. | Phase token (`p22`/`p23`) is the second segment; parsers should use it to dispatch to the correct subsystem. |
| 6 | **Implementation hold clarity.** P23 must not start production implementation until P19 namespace contract readiness, not merely P20 axis satisfied by operator accepted-risk waiver. | Add this hold to the P23 plan and gate any P23 implementation tickets on P19-001..P19-005 definition completion. |

---

## 6. Recommendations to Planner

1. **Carry `project_namespace` from day one.**  
   Add `project_namespace` to every P23 data structure, DB table, and artifact path as a nullable/default field before writing any non-research code.

2. **Mirror P22 exactly.**  
   Use the same identifier prefix order, default namespace, migration phases, and audit fields as P22 to reduce cognitive and tooling overhead.

3. **Hard-reject namespace-less actions at the entry point.**  
   Do not allow the executor to default silently; fail fast and log.

4. **Do not build a namespace registry inside P23.**  
   P23 must remain read-only with respect to P19. If a registry lookup is needed, treat it as an external dependency and stub it with `default` until P19 delivers.

5. **Gate P23 implementation on P19 namespace contract readiness.**  
   Do not start P23 coding waves until P19-001..P19-005 are at least defined (not necessarily implemented). Research and design-only work can proceed.

6. **Document the forward-compat seam in the P23 plan.**  
   Reference this research file in the P23 master plan so the seam is visible to implementers and auditors.

7. **Add namespace switch to P23 test harnesses.**  
   Even before P19, tests should exercise `default` and a mock project slug to ensure the seam works.

---

## 7. Verdict

P23 must treat project namespace as a first-class, mandatory field on every action and audit row, defaulting to `default` today and becoming project-qualified once P19 is delivered. The design mirrors P22 exactly: pre-P19 identifiers are `p23:<executor>:<surface>:<action-id>`; post-P19 identifiers become `<project>:p23:<executor>:<surface>:<action-id>`. P23 must not create, rename, or delete P19 namespaces, must hard-reject namespace-less actions, and must log every namespace switch. Implementation of P23 is held until P19 reaches definition pass.

---

| Version | Date | Author | Status |
|---|---|---|---|
| 1.0 | 2026-06-25 | Guinevere research subagent | RESEARCH — forward-design namespace contract; P19 definition complete 2026-06-25 (updated in DOC-GATE cleanup). |
