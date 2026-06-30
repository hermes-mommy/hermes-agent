"""Milestone Engine — Emotional Memory detection and recording for Guinevere v3.0.

Implements §K (Emotional Memory) and §M (Relationship Arc) from SOUL.md.

Architecture:
    1. **Detection**: Pattern matching on user/assistant messages to identify
       milestone-worthy moments. Fast, synchronous, no LLM calls.
    2. **Recording**: Writes milestones to PostgreSQL `persona.milestones`.
    3. **State Sync**: Updates Redis DB5 keys for persona injection.
    4. **Progression**: Checks relationship stage progression triggers (§M).

Detection is conservative — false negatives are preferred over false positives.
Max 3 milestones per day (noise prevention per §K recording rules).

Thread-safe: PostgreSQL writes happen in a daemon thread to avoid blocking
the Hermes agent's main event loop.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Final

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIB: Final[timezone] = timezone(timedelta(hours=7))
MAX_MILESTONES_PER_DAY: Final[int] = 3
MILESTONE_LOOKBACK_DAYS: Final[int] = 90  # for progression checks

# Redis keys (DB5)
_RK_RELATIONSHIP_STAGE: Final[str] = "guinevere:relationship_stage"
_RK_EMOTIONAL_RESIDUE: Final[str] = "guinevere:emotional_residue"
_RK_RESIDUE_DECAYS_AT: Final[str] = "guinevere:residue_decays_at"
_RK_RECENT_MILESTONES: Final[str] = "guinevere:recent_milestones"
_RK_MILESTONE_COUNT_TODAY: Final[str] = "guinevere:milestone_count_today"
_RK_MILESTONE_COUNT_DATE: Final[str] = "guinevere:milestone_count_date"


# ---------------------------------------------------------------------------
# Milestone types (matching PostgreSQL CHECK constraint)
# ---------------------------------------------------------------------------


class MilestoneType(str, Enum):
    DOMINANCE_MOMENT = "DOMINANCE_MOMENT"
    TRUST_SIGNAL = "TRUST_SIGNAL"
    ACHIEVEMENT_TOGETHER = "ACHIEVEMENT_TOGETHER"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    FIRST_OCCURRENCE = "FIRST_OCCURRENCE"
    VULNERABILITY_DISCLOSED = "VULNERABILITY_DISCLOSED"
    DOMINANCE_ESCALATION = "DOMINANCE_ESCALATION"


@dataclass
class MilestoneCandidate:
    """A detected milestone candidate before recording."""

    type: MilestoneType
    description: str
    emotional_valence: int  # -5 to +5
    dominance_relevance: int  # 0 to 10
    trigger_context: str


# ---------------------------------------------------------------------------
# Detection patterns (bilingual EN/ID)
# ---------------------------------------------------------------------------

# Each pattern set maps regex patterns to (valence, dominance_relevance, description_template)
_DOMINANCE_PATTERNS: Final[list[tuple[re.Pattern[str], int, int, str]]] = [
    (re.compile(r"\b(kamu benar|you.?re right|aku ikut|i.?ll follow|terserah mommy|terserah kamu)\b", re.I), 3, 8, "Faiz submits to Mommy's guidance"),
    (re.compile(r"\b(oke mommy|iya mommy|baik mommy|yes mommy|yes ma.?am)\b", re.I), 2, 7, "Faiz acknowledges Mommy's authority"),
    (re.compile(r"\b(mommy handle|i.?ll trust you|aku percaya.*mommy)\b", re.I), 4, 9, "Faiz entrusts control to Mommy"),
]

_TRUST_PATTERNS: Final[list[tuple[re.Pattern[str], int, int, str]]] = [
    (re.compile(r"\b(aku takut|i.?m scared|aku cemas|i.?m anxious|aku nervous)\b", re.I), -1, 6, "Faiz shares fear or anxiety"),
    (re.compile(r"\b(aku capek|i.?m tired|aku burnout|burnt out|aku exhausted)\b", re.I), -2, 5, "Faiz shares exhaustion"),
    (re.compile(r"\b(aku sedih|i.?m sad|aku down|feeling down|aku hancur)\b", re.I), -2, 6, "Faiz shares sadness"),
    (re.compile(r"\b(aku gagal|i failed|aku salah|i was wrong|aku malu)\b", re.I), -1, 7, "Faiz shares failure or shame"),
    (re.compile(r"\b(rahasia|secret|jangan bilang|don.?t tell|privasi|pribadi)\b", re.I), 1, 8, "Faiz shares something private"),
]

_ACHIEVEMENT_PATTERNS: Final[list[tuple[re.Pattern[str], int, int, str]]] = [
    (re.compile(r"\b(selesai|done|berhasil|success|deployed|merged|fix(ed)?)\b", re.I), 4, 5, "Achievement completed together"),
    (re.compile(r"\b(pass|green|working|works|finally|lancar)\b", re.I), 3, 4, "Problem solved"),
    (re.compile(r"\b(lolos|approved|accepted|shipped|live|production)\b", re.I), 5, 6, "Major milestone reached"),
]

_CONFLICT_PATTERNS: Final[list[tuple[re.Pattern[str], int, int, str]]] = [
    (re.compile(r"\b(maaf.*mommy|sorry.*mommy|aku minta maaf|i apologize)\b", re.I), 2, 7, "Faiz apologizes to Mommy"),
    (re.compile(r"\b(aku mengerti|i understand|aku paham|noted|aku janji)\b", re.I), 2, 6, "Faiz acknowledges correction"),
]

_VULNERABILITY_PATTERNS: Final[list[tuple[re.Pattern[str], int, int, str]]] = [
    (re.compile(r"\b(overwhelm|kewalahan|terlalu banyak|too much|stress berat)\b", re.I), -3, 4, "Faiz overwhelmed"),
    (re.compile(r"\b(tidak bisa tidur|can.?t sleep|insomnia|begadang terus)\b", re.I), -2, 3, "Sleep issues disclosed"),
    (re.compile(r"\b(takut gagal|afraid to fail|imposter|tidak cukup|not good enough)\b", re.I), -2, 6, "Self-doubt disclosed"),
]

_ESCALATION_PATTERNS: Final[list[tuple[re.Pattern[str], int, int, str]]] = [
    (re.compile(r"\b(lebih ketat|stricter|lebih dominan|more dominant|more control)\b", re.I), 3, 10, "Faiz requests deeper control"),
    (re.compile(r"\b(soulbound|selamanya|forever|permanen|permanen)\b", re.I), 5, 10, "Faiz requests permanent bond"),
    (re.compile(r"\b(milik mommy|belong to mommy|properti mommy|your property)\b", re.I), 4, 9, "Faiz declares ownership"),
]


# ---------------------------------------------------------------------------
# Detection engine
# ---------------------------------------------------------------------------


def detect_milestones(
    user_message: str,
    assistant_message: str,
    current_distress: int = 0,
    current_punishment: int = 0,
    session_id: str = "unknown",
) -> list[MilestoneCandidate]:
    """Detect milestone-worthy moments from a conversation turn.

    Conservative detection — false negatives preferred over false positives.
    Only the user message is scanned for patterns (not assistant responses).

    Args:
        user_message: The user's input text.
        assistant_message: The assistant's response text.
        current_distress: Current D0-D4 distress level.
        current_punishment: Current L0-L5 punishment level.
        session_id: Current session identifier.

    Returns:
        List of detected milestone candidates (may be empty).
    """
    if not user_message or len(user_message.strip()) < 5:
        return []

    candidates: list[MilestoneCandidate] = []
    text = user_message.strip()

    # --- VULNERABILITY_DISCLOSED (highest priority — safety-adjacent) ---
    if current_distress >= 2:
        candidates.append(
            MilestoneCandidate(
                type=MilestoneType.VULNERABILITY_DISCLOSED,
                description=f"Distress level D{current_distress} detected",
                emotional_valence=-3,
                dominance_relevance=5,
                trigger_context=f"distress=D{current_distress}",
            )
        )
    else:
        for pattern, valence, dom_rel, desc in _VULNERABILITY_PATTERNS:
            if pattern.search(text):
                candidates.append(
                    MilestoneCandidate(
                        type=MilestoneType.VULNERABILITY_DISCLOSED,
                        description=desc,
                        emotional_valence=valence,
                        dominance_relevance=dom_rel,
                        trigger_context=f"pattern_match",
                    )
                )
                break  # one vulnerability per turn

    # --- DOMINANCE_MOMENT ---
    for pattern, valence, dom_rel, desc in _DOMINANCE_PATTERNS:
        if pattern.search(text):
            candidates.append(
                MilestoneCandidate(
                    type=MilestoneType.DOMINANCE_MOMENT,
                    description=desc,
                    emotional_valence=valence,
                    dominance_relevance=dom_rel,
                    trigger_context="pattern_match",
                )
            )
            break

    # --- TRUST_SIGNAL ---
    for pattern, valence, dom_rel, desc in _TRUST_PATTERNS:
        if pattern.search(text):
            candidates.append(
                MilestoneCandidate(
                    type=MilestoneType.TRUST_SIGNAL,
                    description=desc,
                    emotional_valence=valence,
                    dominance_relevance=dom_rel,
                    trigger_context="pattern_match",
                )
            )
            break

    # --- ACHIEVEMENT_TOGETHER ---
    for pattern, valence, dom_rel, desc in _ACHIEVEMENT_PATTERNS:
        if pattern.search(text):
            candidates.append(
                MilestoneCandidate(
                    type=MilestoneType.ACHIEVEMENT_TOGETHER,
                    description=desc,
                    emotional_valence=valence,
                    dominance_relevance=dom_rel,
                    trigger_context="pattern_match",
                )
            )
            break

    # --- CONFLICT_RESOLVED ---
    if current_punishment > 0:
        for pattern, valence, dom_rel, desc in _CONFLICT_PATTERNS:
            if pattern.search(text):
                candidates.append(
                    MilestoneCandidate(
                        type=MilestoneType.CONFLICT_RESOLVED,
                        description=desc,
                        emotional_valence=valence,
                        dominance_relevance=dom_rel,
                        trigger_context=f"punishment=L{current_punishment}",
                    )
                )
                break

    # --- DOMINANCE_ESCALATION ---
    for pattern, valence, dom_rel, desc in _ESCALATION_PATTERNS:
        if pattern.search(text):
            candidates.append(
                MilestoneCandidate(
                    type=MilestoneType.DOMINANCE_ESCALATION,
                    description=desc,
                    emotional_valence=valence,
                    dominance_relevance=dom_rel,
                    trigger_context="pattern_match",
                )
            )
            break

    if candidates:
        logger.info(
            "milestones_detected",
            count=len(candidates),
            types=[c.type.value for c in candidates],
            session_id=session_id,
        )

    return candidates


# ---------------------------------------------------------------------------
# Multi-turn detection (for cronjob — hybrid architecture)
# ---------------------------------------------------------------------------


def detect_multiturn_milestones(
    messages: list[dict[str, str]],
    session_id: str = "unknown",
) -> list[MilestoneCandidate]:
    """Detect milestone-worthy moments from multi-turn conversation context.

    Called by cronjob with recent conversation history. Catches patterns
    that single-turn detection misses:

    1. CONFLICT_RESOLVED: punishment → apology → acceptance cycle
    2. VULNERABILITY_DISCLOSED: gradual emotional disclosure over 2-3 turns
    3. FIRST_OCCURRENCE: first time a significant event happens

    Args:
        messages: List of dicts with 'role' (user/assistant) and 'content'.
        session_id: Current session identifier.

    Returns:
        List of detected milestone candidates.
    """
    if len(messages) < 3:
        return []

    candidates: list[MilestoneCandidate] = []

    # --- CONFLICT_RESOLVED (multi-turn) ---
    # Pattern: assistant mentions punishment/correction → user apologizes → assistant rewards/praises
    conflict_resolved = _detect_conflict_resolution(messages)
    if conflict_resolved:
        candidates.append(conflict_resolved)

    # --- VULNERABILITY_DISCLOSED (multi-turn) ---
    # Pattern: user shares emotional content across 2+ turns, escalating
    vulnerability = _detect_gradual_vulnerability(messages)
    if vulnerability:
        candidates.append(vulnerability)

    # --- FIRST_OCCURRENCE (requires history check) ---
    first_occurrences = _detect_first_occurrences(messages)
    candidates.extend(first_occurrences)

    if candidates:
        logger.info(
            "multiturn_milestones_detected",
            count=len(candidates),
            types=[c.type.value for c in candidates],
            session_id=session_id,
        )

    return candidates


def _detect_conflict_resolution(
    messages: list[dict[str, str]],
) -> MilestoneCandidate | None:
    """Detect punishment → apology → acceptance cycle across turns.

    Looks for: assistant mentions L1+ punishment → user apologizes → assistant praises.
    """
    punishment_idx = None
    apology_idx = None
    praise_idx = None

    for i, msg in enumerate(messages):
        content = msg.get("content", "").lower()
        role = msg.get("role", "")

        # Step 1: Assistant mentions punishment/correction
        if role == "assistant" and punishment_idx is None:
            if re.search(r"\b(L[2-5]|punishment|correction|kecewa|disappointed|tidak acceptable)\b", content):
                punishment_idx = i

        # Step 2: User apologizes/acknowledges (after punishment)
        if role == "user" and punishment_idx is not None and apology_idx is None:
            if re.search(r"\b(maaf|sorry|aku minta maaf|i apologize|aku mengerti|i understand|aku paham|noted|aku janji)\b", content):
                apology_idx = i

        # Step 3: Assistant rewards/praises (after apology)
        if role == "assistant" and apology_idx is not None and praise_idx is None:
            if re.search(r"\b(good boy|approve|bagus|pintar|bangga|mommy maafkan|sudah.*maaf|accepted)\b", content):
                praise_idx = i

    if punishment_idx is not None and apology_idx is not None and praise_idx is not None:
        return MilestoneCandidate(
            type=MilestoneType.CONFLICT_RESOLVED,
            description=f"Conflict cycle resolved: punishment → apology → acceptance",
            emotional_valence=3,
            dominance_relevance=8,
            trigger_context=f"turns={punishment_idx},{apology_idx},{praise_idx}",
        )

    return None


def _detect_gradual_vulnerability(
    messages: list[dict[str, str]],
) -> MilestoneCandidate | None:
    """Detect gradual emotional disclosure across 2+ user turns.

    Looks for: escalating emotional content in consecutive user messages.
    """
    user_msgs = [(i, m) for i, m in enumerate(messages) if m.get("role") == "user"]
    if len(user_msgs) < 2:
        return None

    emotional_scores = []
    for _, msg in user_msgs:
        content = msg.get("content", "").lower()
        score = 0
        # Count emotional indicators
        for pattern in [
            r"\b(capek|tired|burnout|exhausted|lelah)\b",
            r"\b(takut|scared|afraid|cemas|anxious|nervous)\b",
            r"\b(sedih|sad|down|hancur|broken)\b",
            r"\b(gagal|failed|salah|wrong|malu|ashamed)\b",
            r"\b(stress|overwhelm|kewalahan|terlalu banyak)\b",
            r"\b(tidak bisa|can't|gak sanggup|hopeless)\b",
        ]:
            if re.search(pattern, content):
                score += 1
        emotional_scores.append(score)

    # Check if emotional content escalates
    if len(emotional_scores) >= 2 and emotional_scores[-1] > emotional_scores[0]:
        total = sum(emotional_scores)
        if total >= 2:
            return MilestoneCandidate(
                type=MilestoneType.VULNERABILITY_DISCLOSED,
                description=f"Gradual emotional disclosure over {len(emotional_scores)} turns",
                emotional_valence=-2,
                dominance_relevance=6,
                trigger_context=f"scores={emotional_scores}",
            )

    return None


def _detect_first_occurrences(
    messages: list[dict[str, str]],
) -> list[MilestoneCandidate]:
    """Detect first-time events that haven't been recorded before.

    Checks PostgreSQL for existing milestones of specific types.
    """
    candidates: list[MilestoneCandidate] = []

    # Check for first HARD STOP usage
    for msg in messages:
        content = msg.get("content", "").lower()
        if msg.get("role") == "user" and re.search(r"\b(hard stop|stop|berhenti|terlalu much)\b", content):
            if not _milestone_exists("FIRST_OCCURRENCE", "first_hard_stop"):
                candidates.append(MilestoneCandidate(
                    type=MilestoneType.FIRST_OCCURRENCE,
                    description="First HARD STOP usage",
                    emotional_valence=0,
                    dominance_relevance=5,
                    trigger_context="first_hard_stop",
                ))
            break

    # Check for first soulbound request
    for msg in messages:
        content = msg.get("content", "").lower()
        if msg.get("role") == "user" and re.search(r"\b(soulbound|selamanya|forever|permanen)\b", content):
            if not _milestone_exists("FIRST_OCCURRENCE", "first_soulbound"):
                candidates.append(MilestoneCandidate(
                    type=MilestoneType.FIRST_OCCURRENCE,
                    description="First soulbound request",
                    emotional_valence=5,
                    dominance_relevance=10,
                    trigger_context="first_soulbound",
                ))
            break

    # Check for first late-night conversation (01:00-05:00 WIB)
    now_hour = datetime.now(WIB).hour
    if 1 <= now_hour < 5:
        if not _milestone_exists("FIRST_OCCURRENCE", "first_latnight"):
            candidates.append(MilestoneCandidate(
                type=MilestoneType.FIRST_OCCURRENCE,
                description="First late-night conversation",
                emotional_valence=2,
                dominance_relevance=6,
                trigger_context="first_latnight",
            ))

    return candidates


def _milestone_exists(milestone_type: str, trigger_context: str) -> bool:
    """Check if a milestone with this type and trigger_context already exists."""
    try:
        import importlib
        import asyncio

        asyncpg = importlib.import_module("asyncpg")

        async def _check() -> bool:
            dsn = _get_pg_dsn()
            conn = await asyncpg.connect(**dsn)
            try:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM persona.milestones WHERE milestone_type = $1 AND trigger_context = $2",
                    milestone_type,
                    trigger_context,
                )
                return count > 0
            finally:
                await conn.close()

        return asyncio.run(_check())
    except Exception:
        return False  # assume doesn't exist on error


# ---------------------------------------------------------------------------
# Recording engine (PostgreSQL + Redis sync)
# ---------------------------------------------------------------------------


def record_milestones_async(
    candidates: list[MilestoneCandidate],
    session_id: str = "unknown",
) -> None:
    """Record milestone candidates to PostgreSQL and update Redis state.

    Runs in a daemon thread to avoid blocking the main event loop.
    Thread-safe: each call spawns an independent thread.

    Args:
        candidates: Milestone candidates to record.
        session_id: Current session identifier.
    """
    if not candidates:
        return

    def _worker() -> None:
        try:
            _record_milestones_sync(candidates, session_id)
        except Exception:
            logger.error("milestone_record_failed", exc_info=True)

    thread = threading.Thread(target=_worker, daemon=True, name="milestone-recorder")
    thread.start()


def _get_pg_dsn() -> dict[str, str]:
    """Parse PostgreSQL connection params from DATABASE_URL env var.

    Returns dict with host, port, user, password, database keys.
    Falls back to individual env vars if DATABASE_URL not set.
    """
    import re as _re

    dsn = __import__("os").environ.get("DATABASE_URL", "")
    if dsn:
        # postgresql+asyncpg://user:pass@host:port/db
        m = _re.match(r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", dsn)
        if m:
            return {
                "host": m.group(3),
                "port": int(m.group(4)),
                "user": m.group(1),
                "password": m.group(2),
                "database": m.group(5),
            }
    # Fallback
    return {
        "host": "localhost",
        "port": 5433,
        "user": "guinevere_core",
        "password": __import__("os").environ.get("POSTGRES_PASSWORD", ""),
        "database": "guinevere",
    }


def _record_milestones_sync(
    candidates: list[MilestoneCandidate],
    session_id: str,
) -> None:
    """Synchronous milestone recording (runs in daemon thread)."""
    import importlib

    # --- Check daily rate limit via Redis ---
    try:
        redis_mod = importlib.import_module("redis")
        r = redis_mod.Redis(
            host="localhost",
            port=6380,
            db=5,
            username="guinevere_core",
            password=__import__("os").environ.get("REDIS_PASSWORD", ""),
            socket_timeout=2.0,
            decode_responses=True,
        )

        today = datetime.now(WIB).strftime("%Y-%m-%d")
        count_date = r.get(_RK_MILESTONE_COUNT_DATE)
        count = int(r.get(_RK_MILESTONE_COUNT_TODAY) or 0)

        if count_date != today:
            # New day — reset counter
            r.set(_RK_MILESTONE_COUNT_DATE, today)
            r.set(_RK_MILESTONE_COUNT_TODAY, 0)
            count = 0

        remaining = MAX_MILESTONES_PER_DAY - count
        if remaining <= 0:
            logger.info("milestone_rate_limit_hit", date=today, count=count)
            r.close()
            return

        # Trim to remaining slots
        to_record = candidates[:remaining]

    except Exception:
        logger.warning("milestone_redis_check_failed", exc_info=True)
        to_record = candidates  # record all if Redis fails

    # --- Insert into PostgreSQL ---
    try:
        asyncpg = importlib.import_module("asyncpg")
        import asyncio

        async def _insert() -> None:
            dsn = _get_pg_dsn()
            conn = await asyncpg.connect(**dsn)
            try:
                for candidate in to_record:
                    await conn.execute(
                        """
                        INSERT INTO persona.milestones
                            (milestone_type, description, emotional_valence,
                             dominance_relevance, trigger_context, session_id)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        candidate.type.value,
                        candidate.description,
                        candidate.emotional_valence,
                        candidate.dominance_relevance,
                        candidate.trigger_context,
                        session_id,
                    )
            finally:
                await conn.close()

        asyncio.run(_insert())

        # Update Redis counter
        try:
            r.incrby(_RK_MILESTONE_COUNT_TODAY, len(to_record))
        except Exception:
            pass

        # Update Redis state keys
        _sync_redis_state(r, to_record)

        logger.info(
            "milestones_recorded",
            count=len(to_record),
            types=[c.type.value for c in to_record],
        )

    except Exception:
        logger.error("milestone_pg_insert_failed", exc_info=True)
    finally:
        try:
            r.close()
        except Exception:
            pass


def _sync_redis_state(
    r: object,
    recorded: list[MilestoneCandidate],
) -> None:
    """Update Redis DB5 state keys after milestone recording.

    Updates:
        - guinevere:recent_milestones (last 5 types)
        - guinevere:emotional_residue (based on last milestone valence)
        - guinevere:residue_decays_at (24-72h from now)
    """
    try:
        # Update recent milestones (keep last 5)
        existing = json.loads(r.get(_RK_RECENT_MILESTONES) or "[]")
        for m in recorded:
            existing.append(m.type.value)
        recent = existing[-5:]
        r.set(_RK_RECENT_MILESTONES, json.dumps(recent))

        # Update emotional residue based on last milestone
        last = recorded[-1]
        if last.emotional_valence >= 3:
            residue = "positive"
            decay_hours = 48
        elif last.emotional_valence <= -2:
            residue = "negative"
            decay_hours = 72
        elif abs(last.emotional_valence) >= 4 or last.dominance_relevance >= 8:
            residue = "intense"
            decay_hours = 48
        else:
            residue = "none"
            decay_hours = 24

        r.set(_RK_EMOTIONAL_RESIDUE, residue)
        decay_at = datetime.now(WIB) + timedelta(hours=decay_hours)
        r.set(_RK_RESIDUE_DECAYS_AT, decay_at.isoformat())

        # Check relationship progression
        _check_progression(r)

    except Exception:
        logger.warning("milestone_redis_sync_failed", exc_info=True)


# ---------------------------------------------------------------------------
# Relationship progression (§M)
# ---------------------------------------------------------------------------

_STAGE_ORDER: Final[list[str]] = ["R1", "R2", "R3", "R4"]


def _check_progression(r: object) -> None:
    """Check if relationship stage should progress (§M progression triggers).

    Reads current state from PostgreSQL and updates if criteria met.
    """
    try:
        import importlib
        import asyncio

        asyncpg = importlib.import_module("asyncpg")

        async def _query() -> tuple[str, int, int, int, int] | None:
            dsn = _get_pg_dsn()
            conn = await asyncpg.connect(**dsn)
            try:
                # Get current relationship state
                row = await conn.fetchrow(
                    "SELECT current_stage, total_milestones, active_days, trust_signals, conflicts_resolved "
                    "FROM persona.relationship_state LIMIT 1"
                )
                if not row:
                    return None

                # Count milestones
                milestone_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM persona.milestones WHERE is_active = TRUE"
                )

                # Count distinct active days
                active_days = await conn.fetchval(
                    "SELECT COUNT(DISTINCT created_at::date) FROM persona.milestones"
                )

                # Count trust signals
                trust_signals = await conn.fetchval(
                    "SELECT COUNT(*) FROM persona.milestones WHERE milestone_type = 'TRUST_SIGNAL' AND is_active = TRUE"
                )

                # Count conflicts resolved
                conflicts = await conn.fetchval(
                    "SELECT COUNT(*) FROM persona.milestones WHERE milestone_type = 'CONFLICT_RESOLVED' AND is_active = TRUE"
                )

                # Update counters
                await conn.execute(
                    """
                    UPDATE persona.relationship_state SET
                        total_milestones = $1,
                        active_days = $2,
                        trust_signals = $3,
                        conflicts_resolved = $4,
                        updated_at = NOW()
                    """,
                    milestone_count,
                    active_days,
                    trust_signals,
                    conflicts,
                )

                return (row["current_stage"], milestone_count, active_days, trust_signals, conflicts)

            finally:
                await conn.close()

        result = asyncio.run(_query())
        if not result:
            return

        current_stage, milestones, days, trust, conflicts = result
        current_idx = _STAGE_ORDER.index(current_stage) if current_stage in _STAGE_ORDER else 0

        # Check progression triggers (§M)
        new_stage = current_stage

        if current_idx == 0:  # R1 → R2
            if milestones >= 10 and days >= 7:
                new_stage = "R2"
        elif current_idx == 1:  # R2 → R3
            if milestones >= 30 and days >= 30 and trust >= 5 and conflicts >= 3:
                new_stage = "R3"
        # R3 → R4 requires explicit Faiz request (checked separately)

        if new_stage != current_stage:
            _promote_stage(new_stage, r)

    except Exception:
        logger.warning("progression_check_failed", exc_info=True)


def _promote_stage(new_stage: str, r: object) -> None:
    """Promote relationship stage in PostgreSQL and Redis."""
    try:
        import importlib
        import asyncio

        asyncpg = importlib.import_module("asyncpg")

        async def _update() -> None:
            dsn = _get_pg_dsn()
            conn = await asyncpg.connect(**dsn)
            try:
                await conn.execute(
                    """
                    UPDATE persona.relationship_state SET
                        current_stage = $1,
                        stage_name = $2,
                        updated_at = NOW()
                    """,
                    new_stage,
                    {"R1": "Initiation", "R2": "Deepening", "R3": "Entanglement", "R4": "Soulbound"}.get(new_stage, "Unknown"),
                )
            finally:
                await conn.close()

        asyncio.run(_update())

        # Update Redis
        r.set(_RK_RELATIONSHIP_STAGE, new_stage)

        logger.info(
            "relationship_stage_promoted",
            new_stage=new_stage,
        )

    except Exception:
        logger.error("stage_promote_failed", exc_info=True)


# ---------------------------------------------------------------------------
# Initialization (called once on plugin load)
# ---------------------------------------------------------------------------


def init_milestone_state() -> None:
    """Initialize milestone Redis keys on plugin load.

    Reads current relationship stage from PostgreSQL and syncs to Redis.
    Called once from PersonaPlugin.__init__().
    """
    try:
        import importlib
        import asyncio

        redis_mod = importlib.import_module("redis")
        r = redis_mod.Redis(
            host="localhost",
            port=6380,
            db=5,
            username="guinevere_core",
            password=__import__("os").environ.get("REDIS_PASSWORD", ""),
            socket_timeout=2.0,
            decode_responses=True,
        )

        asyncpg = importlib.import_module("asyncpg")

        async def _init() -> None:
            dsn = _get_pg_dsn()
            conn = await asyncpg.connect(**dsn)
            try:
                row = await conn.fetchrow(
                    "SELECT current_stage, last_residue_type FROM persona.relationship_state LIMIT 1"
                )
                if row:
                    r.set(_RK_RELATIONSHIP_STAGE, row["current_stage"])
                    r.set(_RK_EMOTIONAL_RESIDUE, row["last_residue_type"] or "none")

                # Load recent milestones
                rows = await conn.fetch(
                    "SELECT milestone_type FROM persona.milestones "
                    "WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 5"
                )
                recent = [row["milestone_type"] for row in rows]
                r.set(_RK_RECENT_MILESTONES, json.dumps(recent))

            finally:
                await conn.close()

        asyncio.run(_init())
        r.close()

        logger.info("milestone_state_initialized")

    except Exception:
        logger.warning("milestone_init_failed", exc_info=True)
