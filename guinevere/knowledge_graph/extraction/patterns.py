"""P16-007: rule-based extraction patterns for the NER/RE pipeline.

This module is the **single source of truth** for every regex pattern and
predicate-to-relation mapping used by the Wave 2 rule-based extractor.
Keeping them in one place makes it trivial to:

* audit the closed taxonomy (PRD v2.2 §6.2 P16);
* extend the coverage without touching the extractor classes;
* run pure-Python unit tests on the patterns themselves (no DB / no I/O).

Design constraints (per the P16-007 task contract and AGENTS.md BLOCKING
rules):

* **L1 + L2 only** — no GLiNER, no spaCy, no embedding-based NER.  The
  P17+ extractor may layer ML on top of these patterns but must not
  modify them in place.
* **No external API calls** — every pattern is local to this file.
* **No type suppression** — every compiled pattern is a
  ``re.Pattern[str]``; every mapping is a ``dict[str, RelationType]`` or
  ``dict[EntityCategory, list[re.Pattern[str]]]`` with explicit types.
* **No empty except / bare ``except``** — pattern compilation failures
  raise :class:`re.error` so misconfigurations surface immediately.

The patterns are organised in three families:

* :data:`NAME_PATTERNS` — person-name detection (titles, initials, known
  Guinevere operator handle, common 1-3-word capitalised sequences).
* :data:`GEO_PATTERNS` — geographic entity detection (city/country
  gazetteer, ``"City, ST"`` form, common Indonesian and SE-Asian cities).
* :data:`TECH_PATTERNS` — technology entity detection (databases,
  programming languages, frameworks, cloud providers).

Additional per-category patterns (organisations, projects, events,
documents, etc.) are bundled into :data:`ENTITY_PATTERNS` so the
extractor can iterate over a single ``dict[EntityCategory, ...]``.

The :data:`PREDICATE_MAP` maps normalised predicate strings to the
closed :class:`~guinevere.knowledge_graph.types.RelationType` taxonomy.  The
keys are intentionally simple substrings (e.g. ``"works_at"``) so the
relation extractor can do fast ``in`` checks without spinning up a
full-text index.  30+ entries cover the common English verbs seen in
the consolidation output.
"""
from __future__ import annotations

import re
from typing import Final

from guinevere.knowledge_graph.types import EntityCategory, RelationType

# ---------------------------------------------------------------------------
# Person-name patterns
# ---------------------------------------------------------------------------

# Operator handle — the agent must always recognise Faiz regardless of
# the language surface form used in the source fact.  Lowercase comparison
# only; casing is preserved in the surfaced entity name.
_OPERATOR_HANDLE_PATTERN: Final[str] = (
    r"\b(?:Faiz|Samm|Mama|Guinevere|de\s+Baroque)\b"
)

# Latin-script personal name: one to four capitalised tokens, each 2-25
# letters, no leading digits.  Allows hyphenated names ("Anne-Marie")
# and accented Latin characters via the explicit Unicode ranges — no
# ``re.UNICODE`` flag toggling needed for Python 3 str patterns.
_LATIN_NAME_PATTERN: Final[str] = (
    r"\b[A-ZÀ-Ý][a-zà-ÿ]{1,24}"
    r"(?:[\s\-'][A-ZÀ-Ý][a-zà-ÿ]{1,24}){0,3}\b"
)

# Honorific + capitalised name: "Dr. Smith", "Prof. Anne-Marie Curie".
_HONORIFIC_NAME_PATTERN: Final[str] = (
    r"\b(?:Dr|Mr|Mrs|Ms|Prof|Sir|Dame| Haji|Eng)\.?\s+"
    + _LATIN_NAME_PATTERN
)

NAME_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_OPERATOR_HANDLE_PATTERN, re.IGNORECASE),
    re.compile(_HONORIFIC_NAME_PATTERN),
    re.compile(_LATIN_NAME_PATTERN),
)
"""Compiled patterns for person-name detection.

Order matters — the operator-handle pattern is checked first so
``"Faiz"`` always wins over a generic Latin-name match.  All patterns
are case-sensitive except the operator handle (which intentionally
matches "faiz" / "FAIZ" / "Faiz" so we do not miss the operator in
sHOUT-cased or lower-cased source facts).
"""

# ---------------------------------------------------------------------------
# Geographic patterns
# ---------------------------------------------------------------------------

# A small gazetteer of common Indonesian cities (where the operator lives
# and where most early source facts originate) plus major world cities.
# Kept lowercase; matched case-insensitively against the source text.
_INDONESIAN_CITIES: Final[tuple[str, ...]] = (
    "jakarta",
    "bandung",
    "surabaya",
    "medan",
    "semarang",
    "yogyakarta",
    "jogja",
    "bali",
    "denpasar",
    "bekasi",
    "tangerang",
    "depok",
    "bogor",
    "makassar",
    "palembang",
    "pekanbaru",
    "padang",
    "malang",
    "pontianak",
    "banjarmasin",
    "samarinda",
    "manado",
    "kupang",
    "mataram",
    "ambon",
    "jayapura",
    "cakarta",
)

_MAJOR_CITIES: Final[tuple[str, ...]] = (
    "london",
    "paris",
    "tokyo",
    "new york",
    "los angeles",
    "san francisco",
    "berlin",
    "munich",
    "amsterdam",
    "barcelona",
    "madrid",
    "rome",
    "milan",
    "toronto",
    "vancouver",
    "sydney",
    "melbourne",
    "singapore",
    "kuala lumpur",
    "bangkok",
    "manila",
    "hong kong",
    "seoul",
    "beijing",
    "shanghai",
    "mumbai",
    "delhi",
    "dubai",
    "doha",
    "istanbul",
)

_COUNTRIES: Final[tuple[str, ...]] = (
    "indonesia",
    "malaysia",
    "singapore",
    "thailand",
    "vietnam",
    "philippines",
    "united states",
    "usa",
    "u.s.a.",
    "united kingdom",
    "uk",
    "u.k.",
    "japan",
    "china",
    "india",
    "germany",
    "france",
    "italy",
    "spain",
    "netherlands",
    "australia",
    "new zealand",
    "brazil",
    "argentina",
    "mexico",
    "canada",
    "south korea",
    "north korea",
    "russia",
    "saudi arabia",
    "united arab emirates",
)

# City, ST / City, Country abbreviation form (US-style postal codes only).
_CITY_STATE_PATTERN: Final[str] = (
    r"\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+)*"
    r",\s+[A-Z]{2}\b"
)

_CITY_COUNTRY_PATTERN: Final[str] = (
    r"\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+)*"
    r",\s+[A-ZÀ-Ý][a-zà-ÿ]{2,}\b"
)

# Country-only pattern (case-insensitive; word-anchored).
_COUNTRY_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(c) for c in _COUNTRIES) + r")\b"
)

# Indonesian city pattern (case-insensitive; word-anchored).
_INDONESIAN_CITY_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(c) for c in _INDONESIAN_CITIES) + r")\b"
)

# Major city pattern (case-insensitive; word-anchored).
_MAJOR_CITY_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(c) for c in _MAJOR_CITIES) + r")\b"
)

GEO_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_CITY_STATE_PATTERN),
    re.compile(_CITY_COUNTRY_PATTERN),
    re.compile(_COUNTRY_PATTERN, re.IGNORECASE),
    re.compile(_INDONESIAN_CITY_PATTERN, re.IGNORECASE),
    re.compile(_MAJOR_CITY_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for geographic entity detection.

Order is significant: structured ``"City, ST"`` patterns are checked
before the loose gazetteer so we anchor on punctuation when present.
All gazetteer matches are case-insensitive.
"""

# ---------------------------------------------------------------------------
# Technology patterns
# ---------------------------------------------------------------------------

_DATABASES: Final[tuple[str, ...]] = (
    "postgresql",
    "postgres",
    "mysql",
    "mariadb",
    "mongodb",
    "redis",
    "sqlite",
    "elasticsearch",
    "opensearch",
    "cassandra",
    "dynamodb",
    "neo4j",
    "cockroachdb",
    "clickhouse",
    "snowflake",
    "bigquery",
    "redshift",
    "duckdb",
    "influxdb",
)

_LANGUAGES: Final[tuple[str, ...]] = (
    "python",
    "javascript",
    "typescript",
    "golang",
    "go",
    "rust",
    "java",
    "kotlin",
    "swift",
    "objective-c",
    "ruby",
    "php",
    "scala",
    "haskell",
    "elixir",
    "erlang",
    "clojure",
    "lua",
    "perl",
    "r",
    "matlab",
    "julia",
    "dart",
    "c\\+\\+",
    "c#",
    "f#",
    "vb\\.net",
    "shell",
    "bash",
    "powershell",
)

_FRAMEWORKS: Final[tuple[str, ...]] = (
    "react",
    "reactjs",
    "react.native",
    "angular",
    "angularjs",
    "vue",
    "vuejs",
    "svelte",
    "sveltekit",
    "next.js",
    "nextjs",
    "nuxt",
    "remix",
    "express",
    "expressjs",
    "fastapi",
    "flask",
    "django",
    "fastify",
    "nestjs",
    "spring boot",
    "spring",
    "rails",
    "laravel",
    "symfony",
    "phoenix",
    "actix",
    "axum",
    "tokio",
    "gin",
    "echo",
)

_INFRA: Final[tuple[str, ...]] = (
    "docker",
    "kubernetes",
    "k8s",
    "helm",
    "terraform",
    "ansible",
    "pulumi",
    "vagrant",
    "jenkins",
    "github actions",
    "gitlab ci",
    "circleci",
    "argo cd",
    "argocd",
    "prometheus",
    "grafana",
    "loki",
    "tempo",
    "opentelemetry",
    "jaeger",
    "zipkin",
    "nginx",
    "apache",
    "caddy",
    "haproxy",
    "envoy",
    "istio",
    "linkerd",
)

_CLOUD: Final[tuple[str, ...]] = (
    "aws",
    "amazon web services",
    "azure",
    "microsoft azure",
    "gcp",
    "google cloud",
    "google cloud platform",
    "cloudflare",
    "vercel",
    "netlify",
    "fly.io",
    "render",
    "railway",
    "heroku",
    "digitalocean",
    "linode",
    "hetzner",
    "ovh",
    "bare metal",
    "on-prem",
    "on-premise",
)

# Technology-named entities always carry a version pin (PostgreSQL 16,
# Python 3.12, etc.).  We treat the version token as part of the same
# entity so a fuzzy match later can still tell them apart.
_VERSION_SUFFIX: Final[str] = r"(?:\s+(?:\d+(?:\.\d+){0,3}[a-z0-9]*))?"

_DATABASE_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(d) for d in _DATABASES) + r")"
    + _VERSION_SUFFIX
    + r"\b"
)
_LANGUAGE_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(_LANGUAGES) + r")"
    + _VERSION_SUFFIX
    + r"\b"
)
_FRAMEWORK_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(f) for f in _FRAMEWORKS) + r")"
    + _VERSION_SUFFIX
    + r"\b"
)
_INFRA_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(i) for i in _INFRA) + r")"
    + _VERSION_SUFFIX
    + r"\b"
)
_CLOUD_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(_CLOUD) + r")\b"
)

TECH_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_DATABASE_PATTERN, re.IGNORECASE),
    re.compile(_FRAMEWORK_PATTERN, re.IGNORECASE),
    re.compile(_INFRA_PATTERN, re.IGNORECASE),
    re.compile(_CLOUD_PATTERN, re.IGNORECASE),
    re.compile(_LANGUAGE_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for technology entity detection.

Order is tuned for specificity: databases and frameworks are checked
before cloud providers because the latter overlap with general
capitalised words (e.g. ``"Cloud"`` is a surname in English).  All
matches are case-insensitive and may include an optional version
suffix (``PostgreSQL 16``, ``Python 3.12``).
"""

# ---------------------------------------------------------------------------
# Organisation patterns
# ---------------------------------------------------------------------------

# Common corporate suffixes — listed lowercase, matched case-insensitively.
# Order matters: longer suffixes first so we do not mis-match "Co" inside
# "Company" or "Corp" inside "Corporation".
_ORG_SUFFIXES: Final[tuple[str, ...]] = (
    "inc.",
    "inc",
    "llc",
    "l.l.c.",
    "ltd.",
    "ltd",
    "limited",
    "corp.",
    "corp",
    "corporation",
    "co.",
    "co",
    "gmbh",
    "s.a.",
    "sa",
    "sdn bhd",
    "sdn. bhd.",
    "pte ltd",
    "pte. ltd.",
    "bhd",
    "plc",
    "nv",
    "bv",
    "ag",
    "kk",
    "oy",
    "ab",
    "as",
    "asa",
    "foundation",
    "institute",
    "university",
    "laboratory",
    "labs",
    "laboratories",
    "group",
    "holdings",
    "partners",
    "capital",
    "ventures",
    "studio",
    "studios",
)

# Common Guinevere-aware organisations — the agent should always recognise
# its own stack and the operator's platform even when the suffix is absent.
_KNOWN_ORGS: Final[tuple[str, ...]] = (
    "openai",
    "anthropic",
    "google",
    "alphabet",
    "microsoft",
    "amazon",
    "apple",
    "meta",
    "facebook",
    "instagram",
    "whatsapp",
    "netflix",
    "tesla",
    "ibm",
    "oracle",
    "salesforce",
    "adobe",
    "intel",
    "nvidia",
    "amd",
    "cisco",
    "samsung",
    "sony",
    "nintendo",
    "spotify",
    "uber",
    "airbnb",
    "stripe",
    "shopify",
    "slack",
    "zoom",
    "dropbox",
    "github",
    "gitlab",
    "atlassian",
    "notion",
    "discord",
    "telegram",
    "signal",
    "x",
    "twitter",
    "linkedin",
    "tiktok",
    "youtube",
    "reddit",
    "pinterest",
    "twitch",
    "hermes agent",
    "nous research",
    "guinevere",
    "faiz corp",
    "faiz corp.",
    "9router",
    "deepseek",
    "synthia",
)

_ORG_SUFFIX_PATTERN: Final[str] = (
    r"\b[A-ZÀ-Ý][A-Za-z0-9&]+(?:\s+[A-ZÀ-Ý][A-Za-z0-9&]+)*"
    r"\s+(?:" + "|".join(re.escape(s) for s in _ORG_SUFFIXES) + r")\b"
)

_KNOWN_ORG_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(o) for o in _KNOWN_ORGS) + r")\b"
)

ORG_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_ORG_SUFFIX_PATTERN),
    re.compile(_KNOWN_ORG_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for organisation entity detection.

The suffix pattern is checked first because the known-org gazetteer
contains short tokens (``"X"``, ``"Co"``) that could match
unrelated capitalised words.  The whitespace token ``\\s+`` before
the suffix requires the organisation name to be a multi-word phrase,
which drastically reduces false positives.
"""

# ---------------------------------------------------------------------------
# Project patterns
# ---------------------------------------------------------------------------

_KNOWN_PROJECTS: Final[tuple[str, ...]] = (
    "guinevere",
    "hermes agent",
    "hermes",
    "aizanta",
    "aizanta future",
    "obscuragram",
    "obscula",
    "synthia",
    "9router",
    "nine router",
    "opencode",
    "open code",
    "tasker",
    "postman",
    "insomnia",
    "jupyter",
)

_PROJECT_SUFFIX_PATTERN: Final[str] = (
    r"\bProject\s+[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b"
)

_KNOWN_PROJECT_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(p) for p in _KNOWN_PROJECTS) + r")\b"
)

PROJECT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_PROJECT_SUFFIX_PATTERN),
    re.compile(_KNOWN_PROJECT_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for project entity detection.

The ``Project Foo`` form is checked first so the gazetteer (which
contains very short tokens like ``"Co"`` is irrelevant here, but
``"Go"`` is a project) does not swallow generic single-word
matches.
"""

# ---------------------------------------------------------------------------
# Event / document / concept / emotion patterns
# ---------------------------------------------------------------------------

# YYYY-MM-DD, YYYY/MM/DD, or "Month DD, YYYY" form.
_DATE_PATTERN: Final[str] = (
    r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    r"\s+\d{1,2},?\s+\d{4})\b"
)

# Conference / summit / meetup / workshop form.
_EVENT_KEYWORDS: Final[tuple[str, ...]] = (
    "conference",
    "summit",
    "meetup",
    "workshop",
    "symposium",
    "convention",
    "expo",
    "fair",
    "festival",
    "concert",
    "launch",
    "release",
    "keynote",
    "webinar",
    "hackathon",
    "retreat",
    "ceremony",
)

_EVENT_PATTERN: Final[str] = (
    r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,4}"
    r"\s+(?:" + "|".join(_EVENT_KEYWORDS) + r")(?:\s+\d{4})?\b"
)

EVENT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_DATE_PATTERN),
    re.compile(_EVENT_PATTERN),
)
"""Compiled patterns for event entity detection.

Dates are matched first so the conference-suffix pattern only fires
on the remaining text.
"""

_DOCUMENT_EXTENSIONS: Final[tuple[str, ...]] = (
    r"\.pdf",
    r"\.md",
    r"\.txt",
    r"\.docx?",
    r"\.xlsx?",
    r"\.pptx?",
    r"\.json",
    r"\.ya?ml",
    r"\.toml",
    r"\.sql",
    r"\.py",
    r"\.ts",
    r"\.js",
    r"\.go",
    r"\.rs",
)

_DOCUMENT_KEYWORDS: Final[tuple[str, ...]] = (
    "spec",
    "specification",
    "rfc",
    "adr",
    "sop",
    "runbook",
    "policy",
    "charter",
    "guide",
    "manual",
    "handbook",
    "report",
    "whitepaper",
    "white paper",
    "blog post",
    "article",
    "thesis",
    "paper",
    "documentation",
)

_DOCUMENT_EXTENSION_PATTERN: Final[str] = (
    r"\b[A-Za-z0-9_\-]+(?:" + "|".join(_DOCUMENT_EXTENSIONS) + r")\b"
)

_DOCUMENT_KEYWORD_PATTERN: Final[str] = (
    r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\s+"
    r"(?:" + "|".join(_DOCUMENT_KEYWORDS) + r")\b"
)

DOCUMENT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_DOCUMENT_EXTENSION_PATTERN, re.IGNORECASE),
    re.compile(_DOCUMENT_KEYWORD_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for document entity detection.

Filenames with extensions come first (very high precision) followed
by the ``Foo Spec`` keyword pattern.
"""

_CONCEPT_HINT_WORDS: Final[tuple[str, ...]] = (
    "concept",
    "theory",
    "principle",
    "pattern",
    "paradigm",
    "framework",
    "methodology",
    "philosophy",
    "ideology",
    "strategy",
    "tactic",
    "approach",
    "model",
    "system",
    "process",
    "workflow",
    "pipeline",
    "architecture",
    "design",
    "protocol",
    "standard",
    "specification",
)

_CONCEPT_PATTERN: Final[str] = (
    r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}"
    r"\s+(?:" + "|".join(_CONCEPT_HINT_WORDS) + r")\b"
)

CONCEPT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_CONCEPT_PATTERN),
)
"""Compiled patterns for concept entity detection.

A concept is signalled by a capitalised phrase ending in a hint word
like ``"Pattern"`` or ``"Architecture"``.
"""

_EMOTION_WORDS: Final[tuple[str, ...]] = (
    "joy",
    "happiness",
    "sadness",
    "anger",
    "fear",
    "disgust",
    "surprise",
    "love",
    "hate",
    "trust",
    "anticipation",
    "anxiety",
    "stress",
    "calm",
    "excitement",
    "boredom",
    "curiosity",
    "pride",
    "shame",
    "guilt",
    "envy",
    "gratitude",
    "loneliness",
    "hope",
    "despair",
    "affection",
    "resentment",
    "compassion",
    "frustration",
    "satisfaction",
    "regret",
    "relief",
    "nostalgia",
)

_EMOTION_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(_EMOTION_WORDS) + r")\b"
)

EMOTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_EMOTION_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for emotion entity detection.

Pure dictionary match — emotions are closed-class.
"""

_RELATIONSHIP_WORDS: Final[tuple[str, ...]] = (
    "friend",
    "friendship",
    "enemy",
    "rivalry",
    "spouse",
    "partner",
    "boyfriend",
    "girlfriend",
    "fiance",
    "fiancee",
    "colleague",
    "coworker",
    "co-worker",
    "classmate",
    "roommate",
    "neighbour",
    "neighbor",
    "parent",
    "child",
    "sibling",
    "cousin",
    "uncle",
    "aunt",
    "nephew",
    "niece",
    "mentor",
    "mentee",
    "protege",
    "boss",
    "subordinate",
    "team",
    "squad",
    "crew",
)

_RELATIONSHIP_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(_RELATIONSHIP_WORDS) + r")\b"
)

RELATIONSHIP_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_RELATIONSHIP_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for inter-personal relationship detection.

Closed-class dictionary; same shape as :data:`EMOTION_PATTERNS`.
"""

_SURVEILLANCE_KEYWORDS: Final[tuple[str, ...]] = (
    "tasker",
    "location ping",
    "battery level",
    "screen time",
    "app usage",
    "notification",
    "sms",
    "call log",
    "ambient audio",
    "step count",
    "heart rate",
    "sleep duration",
    "windows daemon",
    "windows surveillance",
    "mobile ping",
    "ping",
)

_SURVEILLANCE_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(s) for s in _SURVEILLANCE_KEYWORDS) + r")\b"
)

SURVEILLANCE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_SURVEILLANCE_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for surveillance-context entity detection.

Guinevere-specific — these keywords are the surveillance channels
explicitly listed in PRD v2.2 §6.4 and the OperatorProcessManual.
"""

_SYSTEM_COMPONENT_KEYWORDS: Final[tuple[str, ...]] = (
    "agent loop",
    "memory read pipeline",
    "memory write pipeline",
    "consolidation worker",
    "ingestion pipeline",
    "query pipeline",
    "read pipeline",
    "write pipeline",
    "kg extractor",
    "kg resolver",
    "kg ingestion",
    "kg query",
    "consent manager",
    "consent gate",
    "safe word monitor",
    "safe-word monitor",
    "discord bot",
    "discord client",
    "telegram bot",
    "tasker profile",
    "tasker task",
    "9router",
    "sox runner",
    "audit logger",
    "logger",
    "tracer",
    "metrics exporter",
    "prometheus exporter",
    "grafana dashboard",
    "lokite",
    "loki pipeline",
    "sub-agent orchestrator",
    "planner",
    "verifier",
    "auditor",
)

_SYSTEM_COMPONENT_PATTERN: Final[str] = (
    r"\b(?:" + "|".join(re.escape(c) for c in _SYSTEM_COMPONENT_KEYWORDS) + r")\b"
)

SYSTEM_COMPONENT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(_SYSTEM_COMPONENT_PATTERN, re.IGNORECASE),
)
"""Compiled patterns for Guinevere system-component entity detection.

Closed gazetteer of the components named in AGENTS.md / PRD v2.2 —
these are the "things the agent itself touches".
"""

# ---------------------------------------------------------------------------
# Master ENTITY_PATTERNS dispatch table
# ---------------------------------------------------------------------------

ENTITY_PATTERNS: Final[dict[EntityCategory, tuple[re.Pattern[str], ...]]] = {
    EntityCategory.PERSON: NAME_PATTERNS,
    EntityCategory.ORGANIZATION: ORG_PATTERNS,
    EntityCategory.LOCATION: GEO_PATTERNS,
    EntityCategory.PROJECT: PROJECT_PATTERNS,
    EntityCategory.TECHNOLOGY: TECH_PATTERNS,
    EntityCategory.EVENT: EVENT_PATTERNS,
    EntityCategory.DOCUMENT: DOCUMENT_PATTERNS,
    EntityCategory.CONCEPT: CONCEPT_PATTERNS,
    EntityCategory.EMOTION: EMOTION_PATTERNS,
    EntityCategory.RELATIONSHIP: RELATIONSHIP_PATTERNS,
    EntityCategory.SURVEILLANCE_CONTEXT: SURVEILLANCE_PATTERNS,
    EntityCategory.SYSTEM_COMPONENT: SYSTEM_COMPONENT_PATTERNS,
    # Categories that intentionally have no L1+L2 patterns — fall back to
    # the generic classifier in :class:`EntityExtractor`.  Listed with an
    # empty tuple (NOT absent) so iteration over the dict is exhaustive.
    EntityCategory.MEMORY_THEME: (),
    EntityCategory.CONSENT_SCOPE: (),
    EntityCategory.COMMUNICATION_CHANNEL: (),
}
"""Dispatch table from :class:`EntityCategory` to compiled patterns.

The extractor iterates over this mapping in declaration order; the
**first category whose patterns match wins**.  Order is therefore
priority order — most-specific categories (PERSON, ORG) are checked
before generic ones.

Categories with no L1+L2 patterns (memory_theme, consent_scope,
communication_channel) are listed with an empty tuple so iteration
remains exhaustive.  Their classification falls through to the
heuristic path in :class:`EntityExtractor`.
"""

# ---------------------------------------------------------------------------
# Predicate → RelationType map
# ---------------------------------------------------------------------------

# Substring match keys — every key is checked against the lower-cased
# predicate via ``in``.  The longest matching key wins (so
# ``"works_at"`` beats ``"works"``).  This is implemented in
# :func:`guinevere.knowledge_graph.extraction.relation_extractor._match_predicate`.

PREDICATE_MAP: Final[dict[str, RelationType]] = {
    # --- employment / organisational affiliation ---------------------
    "works_at": RelationType.WORKS_AT,
    "works_for": RelationType.WORKS_AT,
    "employed_by": RelationType.WORKS_AT,
    "employed_at": RelationType.WORKS_AT,
    "employed_with": RelationType.WORKS_AT,
    "works_under": RelationType.WORKS_AT,
    "joined": RelationType.WORKS_AT,
    "hired_by": RelationType.WORKS_AT,
    "headhunted_by": RelationType.WORKS_AT,
    # --- geographic / spatial -----------------------------------------
    "lives_in": RelationType.LOCATED_IN,
    "located_in": RelationType.LOCATED_IN,
    "based_in": RelationType.LOCATED_IN,
    "resides_in": RelationType.LOCATED_IN,
    "hails_from": RelationType.LOCATED_IN,
    "born_in": RelationType.LOCATED_IN,
    "moved_to": RelationType.LOCATED_IN,
    "relocated_to": RelationType.LOCATED_IN,
    "from": RelationType.LOCATED_IN,
    # --- social / interpersonal ---------------------------------------
    "knows": RelationType.KNOWS,
    "friend_of": RelationType.KNOWS,
    "friends_with": RelationType.KNOWS,
    "acquainted_with": RelationType.KNOWS,
    "met": RelationType.KNOWS,
    "introduced_to": RelationType.KNOWS,
    # --- participation / membership -----------------------------------
    "member_of": RelationType.PARTICIPATES_IN,
    "belongs_to": RelationType.PARTICIPATES_IN,
    "part_of": RelationType.PARTICIPATES_IN,
    "participates_in": RelationType.PARTICIPATES_IN,
    "participated_in": RelationType.PARTICIPATES_IN,
    "attends": RelationType.PARTICIPATES_IN,
    "attended": RelationType.PARTICIPATES_IN,
    "joined_event": RelationType.PARTICIPATES_IN,
    "spoke_at": RelationType.PARTICIPATES_IN,
    "enrolled_in": RelationType.PARTICIPATES_IN,
    # --- creation / authorship ----------------------------------------
    "created": RelationType.CREATED_BY,
    "created_by": RelationType.CREATED_BY,
    "authored": RelationType.CREATED_BY,
    "invented": RelationType.CREATED_BY,
    "designed": RelationType.CREATED_BY,
    "built": RelationType.CREATED_BY,
    "wrote": RelationType.CREATED_BY,
    "founded": RelationType.CREATED_BY,
    "launched": RelationType.CREATED_BY,
    "originated": RelationType.CREATED_BY,
    # --- tool / tech use ----------------------------------------------
    "uses": RelationType.USES,
    "uses_tech": RelationType.USES,
    "depends_on": RelationType.USES,
    "relies_on": RelationType.USES,
    "powered_by": RelationType.USES,
    "built_on": RelationType.USES,
    "running_on": RelationType.USES,
    "hosted_on": RelationType.USES,
    "deployed_on": RelationType.USES,
    "integrates_with": RelationType.USES,
    # --- attribute / characteristic -----------------------------------
    "has": RelationType.HAS_ATTRIBUTE,
    "has_attribute": RelationType.HAS_ATTRIBUTE,
    "attribute_of": RelationType.HAS_ATTRIBUTE,
    "characterized_by": RelationType.HAS_ATTRIBUTE,
    "known_for": RelationType.HAS_ATTRIBUTE,
    "described_as": RelationType.HAS_ATTRIBUTE,
    "tagged_with": RelationType.HAS_ATTRIBUTE,
    "categorised_as": RelationType.HAS_ATTRIBUTE,
    # --- affect / emotional valence -----------------------------------
    "feels": RelationType.FEELS_ABOUT,
    "feels_about": RelationType.FEELS_ABOUT,
    "feels_toward": RelationType.FEELS_ABOUT,
    "expresses": RelationType.FEELS_ABOUT,
    "reacts_to": RelationType.FEELS_ABOUT,
    "loves": RelationType.FEELS_ABOUT,
    "hates": RelationType.FEELS_ABOUT,
    "fears": RelationType.FEELS_ABOUT,
    "enjoys": RelationType.FEELS_ABOUT,
    "dislikes": RelationType.FEELS_ABOUT,
    # --- memory / recall ----------------------------------------------
    "remembers": RelationType.REMEMBERS,
    "recalls": RelationType.REMEMBERS,
    "recollects": RelationType.REMEMBERS,
    "forgot": RelationType.REMEMBERS,
    "forgot_about": RelationType.REMEMBERS,
    "reminded_of": RelationType.REMEMBERS,
    "mentioned": RelationType.REMEMBERS,
    # --- consent / permission -----------------------------------------
    "consents_to": RelationType.CONSENTS_TO,
    "consented_to": RelationType.CONSENTS_TO,
    "agrees_to": RelationType.CONSENTS_TO,
    "agreed_to": RelationType.CONSENTS_TO,
    "authorises": RelationType.CONSENTS_TO,
    "authorizes": RelationType.CONSENTS_TO,
    "permits": RelationType.CONSENTS_TO,
    "grants_access_to": RelationType.CONSENTS_TO,
    "revokes": RelationType.CONSENTS_TO,
    "opts_in_to": RelationType.CONSENTS_TO,
    "opts_out_of": RelationType.CONSENTS_TO,
    # --- communication / channel --------------------------------------
    "communicates_via": RelationType.COMMUNICATES_VIA,
    "contacts_via": RelationType.COMMUNICATES_VIA,
    "talks_via": RelationType.COMMUNICATES_VIA,
    "messages_via": RelationType.COMMUNICATES_VIA,
    "reaches_via": RelationType.COMMUNICATES_VIA,
    "reachable_on": RelationType.COMMUNICATES_VIA,
    "reachable_via": RelationType.COMMUNICATES_VIA,
    "available_on": RelationType.COMMUNICATES_VIA,
    "presence_on": RelationType.COMMUNICATES_VIA,
    "on": RelationType.COMMUNICATES_VIA,
    # --- supervision / management -------------------------------------
    "supervises": RelationType.SUPERVISES,
    "manages": RelationType.SUPERVISES,
    "oversees": RelationType.SUPERVISES,
    "leads": RelationType.SUPERVISES,
    "heads": RelationType.SUPERVISES,
    "directs": RelationType.SUPERVISES,
    "reports_to": RelationType.SUPERVISES,
    "mentored_by": RelationType.SUPERVISES,
    "coached_by": RelationType.SUPERVISES,
    # --- collaboration / partnership ----------------------------------
    "collaborates_with": RelationType.COLLABORATES_WITH,
    "works_with": RelationType.COLLABORATES_WITH,
    "partners_with": RelationType.COLLABORATES_WITH,
    "teams_with": RelationType.COLLABORATES_WITH,
    "paired_with": RelationType.COLLABORATES_WITH,
    "co-authors": RelationType.COLLABORATES_WITH,
    "co-founded": RelationType.COLLABORATES_WITH,
    "co-created": RelationType.COLLABORATES_WITH,
    "allied_with": RelationType.COLLABORATES_WITH,
    "supports": RelationType.COLLABORATES_WITH,
    # --- preference ----------------------------------------------------
    "prefers": RelationType.PREFERENCES,
    "preference": RelationType.PREFERENCES,
    "favours": RelationType.PREFERENCES,
    "favors": RelationType.PREFERENCES,
    "favourite": RelationType.PREFERENCES,
    "favorite": RelationType.PREFERENCES,
    "likes": RelationType.PREFERENCES,
    "loves_to_use": RelationType.PREFERENCES,
    "chooses": RelationType.PREFERENCES,
    "opts_for": RelationType.PREFERENCES,
    # --- generic catch-all (LAST — checked only if nothing else hits) -
    "related_to": RelationType.RELATED_TO,
    "associated_with": RelationType.RELATED_TO,
    "linked_to": RelationType.RELATED_TO,
    "connected_to": RelationType.RELATED_TO,
    "refers_to": RelationType.RELATED_TO,
    "is_about": RelationType.RELATED_TO,
    "concerns": RelationType.RELATED_TO,
    "involves": RelationType.RELATED_TO,
}
"""Substring-keyed predicate → :class:`RelationType` map.

Every key is matched against the lower-cased predicate via substring
search (``key in predicate``).  The extractor picks the **longest
matching key** to avoid ``"works"`` swallowing ``"works_at"``.

Includes 30+ unique predicates per the P16-007 task contract.  All
predicates map into the closed :class:`RelationType` taxonomy; no
new relation types are introduced at L1+L2.

The order of the dict is preserved (Python 3.7+) but irrelevant to
matching — :func:`_match_predicate` sorts candidates by length.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Heuristic confidences for each pattern family.  Higher = more specific
# pattern.  Combined with the source fact's confidence in
# :meth:`EntityExtractor._confidence_for`.

PATTERN_CONFIDENCE: Final[dict[EntityCategory, float]] = {
    EntityCategory.PERSON: 0.85,
    EntityCategory.ORGANIZATION: 0.80,
    EntityCategory.LOCATION: 0.85,
    EntityCategory.PROJECT: 0.80,
    EntityCategory.TECHNOLOGY: 0.90,
    EntityCategory.EVENT: 0.75,
    EntityCategory.DOCUMENT: 0.80,
    EntityCategory.CONCEPT: 0.55,
    EntityCategory.EMOTION: 0.70,
    EntityCategory.RELATIONSHIP: 0.70,
    EntityCategory.SURVEILLANCE_CONTEXT: 0.80,
    EntityCategory.SYSTEM_COMPONENT: 0.85,
    EntityCategory.MEMORY_THEME: 0.40,
    EntityCategory.CONSENT_SCOPE: 0.40,
    EntityCategory.COMMUNICATION_CHANNEL: 0.40,
}
"""Per-category base confidence for a pattern-only match.

Combined with the source fact's confidence via geometric mean in
:meth:`EntityExtractor._confidence_for` — see that method for the
exact formula.
"""

# Floor used when the source fact's ``confidence`` is ``None``.  Mirrors
# the SQL DDL default (``0.5``) in ``memory.semantic_facts``.
DEFAULT_FACT_CONFIDENCE: Final[float] = 0.5
"""Fallback confidence when ``fact.confidence`` is ``None``."""


__all__ = [
    # Pattern families (used directly by the extractor)
    "NAME_PATTERNS",
    "GEO_PATTERNS",
    "TECH_PATTERNS",
    "ORG_PATTERNS",
    "PROJECT_PATTERNS",
    "EVENT_PATTERNS",
    "DOCUMENT_PATTERNS",
    "CONCEPT_PATTERNS",
    "EMOTION_PATTERNS",
    "RELATIONSHIP_PATTERNS",
    "SURVEILLANCE_PATTERNS",
    "SYSTEM_COMPONENT_PATTERNS",
    # Dispatch table
    "ENTITY_PATTERNS",
    # Predicate map
    "PREDICATE_MAP",
    # Confidence helpers
    "PATTERN_CONFIDENCE",
    "DEFAULT_FACT_CONFIDENCE",
]
