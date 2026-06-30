import structlog
from datetime import datetime, date, time, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Any
from uuid import UUID

from .config import get_xposter_settings
from .db import DatabaseManager
from .exceptions import ScheduleSlotUnavailableError, ScheduleOverflowError, DatabaseQueryError
from .metrics import set_schedule_total, set_schedule_used

_logger = structlog.get_logger(__name__)


class ScheduleManager:
    """Allocates posts to schedule slots. Supports rapid test mode (1-minute intervals)."""
    
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._settings = get_xposter_settings()
        self._tz = ZoneInfo(self._settings.schedule_timezone)
        # Check for rapid test mode (env var X_POSTER_RAPID_TEST=1)
        self._rapid_test = getattr(self._settings, "rapid_test_mode", False)
        if self._rapid_test:
            # Generate 1-minute interval slots for current hour only (to avoid 500k+ rows)
            self._slot_times: list[time] = []
            now = datetime.now(self._tz)
            current_hour = now.hour
            for minute in range(0, 60, 1):
                self._slot_times.append(time(current_hour, minute))
            _logger.info("x_poster.schedule.rapid_test_mode", slots=len(self._slot_times), hour=current_hour)
        else:
            # Parse slot times from config (list[str] like ["00:00", "03:00", ...])
            self._slot_times = []
            for slot_str in self._settings.schedule_slots:
                h, m = slot_str.split(":")
                self._slot_times.append(time(int(h), int(m)))
    
    async def initialize_schedule(self, target_date: date) -> None:
        """Create schedule slots for a given date if they don't exist.
        INSERT INTO p13_schedule (slot_time, slot_date, state) VALUES ($1, $2, 'available')
        ON CONFLICT (slot_time, slot_date) DO NOTHING
        """
        set_schedule_total(len(self._slot_times))
        for slot_time in self._slot_times:
            await self._db.execute(
                """
                INSERT INTO p13_schedule (slot_time, slot_date, state) 
                VALUES ($1, $2, 'available')
                ON CONFLICT (slot_time, slot_date) DO NOTHING
                """,
                slot_time, target_date
            )
    
    async def assign_next_slot(self, post_id: UUID) -> datetime:
        """Find next available slot and assign post to it.
        1. Get current WIB time
        2. Find future slots today that are 'available'
        3. If none, overflow to tomorrow's first available slot
        4. UPDATE p13_schedule SET post_id=$1, state='allocated' WHERE slot_time=$2 AND slot_date=$3 AND state='available'
        5. UPDATE p13_posts SET state='scheduled', scheduled_slot=$4 WHERE id=$1
        6. Return the scheduled datetime
        Raises ScheduleOverflowError if all slots full for the look-ahead window.
        """
        now_wib = self._now_wib()
        current_date = now_wib.date()
        current_time = now_wib.time()
        look_ahead_days = getattr(self._settings, "schedule_look_ahead_days", 365)
        max_date = current_date + timedelta(days=look_ahead_days)

        query = """
            SELECT slot_time, slot_date 
            FROM p13_schedule 
            WHERE state = 'available' 
              AND (slot_date > $1 OR (slot_date = $1 AND slot_time >= $2))
              AND slot_date <= $3
            ORDER BY slot_date ASC, slot_time ASC
            LIMIT 1
        """
        row = await self._db.fetchrow(query, current_date, current_time, max_date)
        if not row:
            raise ScheduleOverflowError(
                f"All schedule slots are full for the next {look_ahead_days} days"
            )

        slot_time: time = row["slot_time"]
        slot_date: date = row["slot_date"]

        # Update schedule
        await self._db.execute(
            """
            UPDATE p13_schedule 
            SET post_id = $1, state = 'allocated' 
            WHERE slot_time = $2 AND slot_date = $3 AND state = 'available'
            """,
            post_id, slot_time, slot_date
        )

        # Update post
        scheduled_slot_dt = datetime.combine(slot_date, slot_time, tzinfo=self._tz)
        await self._db.execute(
            """
            UPDATE p13_posts 
            SET state = 'scheduled', scheduled_slot = $1 
            WHERE id = $2
            """,
            scheduled_slot_dt, post_id
        )

        # Metrics and logging
        used = await self.get_slots_used_today(current_date)
        set_schedule_used(used)
        
        if slot_date > current_date:
            _logger.info(
                "x_poster.schedule.overflow",
                post_id=str(post_id),
                slot_date=str(slot_date),
                slot_time=str(slot_time)
            )
        else:
            _logger.info(
                "x_poster.schedule.slot_assigned",
                post_id=str(post_id),
                slot_date=str(slot_date),
                slot_time=str(slot_time)
            )

        return datetime.combine(slot_date, slot_time, tzinfo=self._tz)
    
    async def get_slot_posts(self, slot_time: time, slot_date: date) -> list[dict[str, Any]]:
        """Get all posts assigned to a specific slot.
        SELECT p.* FROM p13_posts p JOIN p13_schedule s ON p.id = s.post_id
        WHERE s.slot_time=$1 AND s.slot_date=$2 AND s.state='allocated'
        """
        query = """
            SELECT p.* 
            FROM p13_posts p 
            JOIN p13_schedule s ON p.id = s.post_id
            WHERE s.slot_time = $1 AND s.slot_date = $2 AND s.state = 'allocated'
        """
        return await self._db.fetch(query, slot_time, slot_date)
    
    async def mark_slot_executed(self, slot_time: time, slot_date: date) -> None:
        """Mark a slot as executed after posting.
        UPDATE p13_schedule SET state='executed' WHERE slot_time=$1 AND slot_date=$2 AND state='allocated'
        """
        await self._db.execute(
            """
            UPDATE p13_schedule 
            SET state = 'executed' 
            WHERE slot_time = $1 AND slot_date = $2 AND state = 'allocated'
            """,
            slot_time, slot_date
        )
        _logger.info(
            "x_poster.schedule.slot_executed",
            slot_date=str(slot_date),
            slot_time=str(slot_time)
        )
    
    async def get_slots_used_today(self, target_date: date | None = None) -> int:
        """Count allocated/executed slots for today."""
        if target_date is None:
            target_date = self._now_wib().date()
        
        query = """
            SELECT COUNT(*) 
            FROM p13_schedule 
            WHERE slot_date = $1 AND state IN ('allocated', 'executed')
        """
        row = await self._db.fetchrow(query, target_date)
        count = row.get("count") if row else None
        return int(count) if count is not None else 0
    
    async def get_next_due_slot(self) -> tuple[time, date] | None:
        """Find the next slot whose scheduled time has passed and is 'allocated' (not yet executed).
        Returns (slot_time, date) or None if nothing due.
        """
        now_wib = self._now_wib()
        current_date = now_wib.date()
        current_time = now_wib.time()
        
        query = """
            SELECT slot_time, slot_date
            FROM p13_schedule
            WHERE state = 'allocated'
              AND (slot_date < $1 OR (slot_date = $1 AND slot_time <= $2))
            ORDER BY slot_date ASC, slot_time ASC
            LIMIT 1
        """
        row = await self._db.fetchrow(query, current_date, current_time)
        if row:
            return row["slot_time"], row["slot_date"]
        return None
    
    async def get_next_upcoming_slot(self) -> tuple[time, date] | None:
        """Find the earliest allocated slot (next post to fire), regardless of due status.
        Returns (slot_time, date) or None if no allocated slots exist.
        """
        query = """
            SELECT slot_time, slot_date
            FROM p13_schedule
            WHERE state = 'allocated'
            ORDER BY slot_date ASC, slot_time ASC
            LIMIT 1
        """
        row = await self._db.fetchrow(query)
        if row:
            return row["slot_time"], row["slot_date"]
        return None

    def _now_wib(self) -> datetime:
        """Current datetime in WIB timezone."""
        return datetime.now(self._tz)
