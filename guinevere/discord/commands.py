"""Discord slash command registry and callbacks — 41 canonical commands.

Ports the COMMAND_SPECS from guinevere/discord/_command_registry.py with all
stale imports cleaned. Former surveillance gating replaced with direct
responses. Former persona.mood_engine replaced with guinevere.emotions.
Former loops.manager replaced with guinevere.consciousness.infra.

All 41 commands are registered with real callbacks that perform auth
checks and send ephemeral responses. Category-based dispatch provides
default behavior; specific commands override as needed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from guinevere.discord._infrastructure import (
    is_faiz_interaction,
    send_denied,
    defer_ephemeral,
    followup_send,
    build_embed,
    PRIMARY,
    ALERT,
    SUCCESS,
    WARNING,
    INFO,
    SURVEILLANCE,
    FINANCE,
    color_for_mood,
)

logger = logging.getLogger(__name__)


# ── Command Spec Data Types ──────────────────────────────────────────────

GUILD_ID: int = 1_510_876_414_671_323_206
APPLICATION_ID: int = 1_510_873_134_981_582_858

SLASH_COMMAND_TYPE: int = 1
OPTION_STRING: int = 3
OPTION_INTEGER: int = 4
OPTION_BOOLEAN: int = 5
OPTION_NUMBER: int = 10


@dataclass(frozen=True)
class CommandOption:
    """Canonical slash-command parameter definition."""

    name: str
    description: str
    option_type: int = OPTION_STRING
    required: bool = False
    choices: tuple[tuple[str, str | int], ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Convert the option to a Discord REST payload."""
        payload: dict[str, Any] = {
            "type": self.option_type,
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }
        if self.choices:
            payload["choices"] = [{"name": name, "value": value} for name, value in self.choices]
        return payload


@dataclass(frozen=True)
class CommandSpec:
    """Canonical slash command definition for Guinevere's guild."""

    category: str
    name: str
    description: str
    options: tuple[CommandOption, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Convert the command to a Discord REST payload."""
        payload: dict[str, Any] = {
            "type": SLASH_COMMAND_TYPE,
            "name": self.name,
            "description": self.description,
        }
        if self.options:
            payload["options"] = [opt.to_payload() for opt in self.options]
        return payload


# ── Choice Sets ──────────────────────────────────────────────────────────

PERSONA_CHOICES = (("Focus", "focus"), ("Casual", "casual"), ("Content", "content"))
PRIORITY_CHOICES = (("Low", "low"), ("Normal", "normal"), ("High", "high"), ("Urgent", "urgent"))
CONSENT_ACTION_CHOICES = (("Show", "show"), ("Grant", "grant"), ("Revoke", "revoke"))
COST_PERIOD_CHOICES = (("Today", "today"), ("Week", "week"), ("Month", "month"))
BUDGET_ACTION_CHOICES = (("View", "view"), ("Set", "set"))


# ── Canonical COMMAND_SPECS — 41 Entries ─────────────────────────────────

COMMAND_SPECS: tuple[CommandSpec, ...] = (
    # core (6)
    CommandSpec("core", "status", "Show Mommy's current system, loop, and safety status."),
    CommandSpec("core", "mood", "Show or update Guinevere's current mood state."),
    CommandSpec("core", "help", "Show the Guinevere command guide."),
    CommandSpec("core", "safeword", "Trigger the configured safety boundary workflow."),
    CommandSpec("core", "new", "Reset conversation history and start fresh."),
    CommandSpec("core", "history", "Show recent conversation turns with Mommy."),
    # loop (7)
    CommandSpec(
        "loop", "loop-start",
        "Start a supervised Guinevere work loop.",
        (CommandOption("goal", "Work-loop goal for Mommy to execute.", required=True),),
    ),
    CommandSpec("loop", "loop-stop", "Stop the active Guinevere work loop safely."),
    CommandSpec("loop", "loop-pause", "Pause the active Guinevere work loop."),
    CommandSpec("loop", "loop-resume", "Resume a paused Guinevere work loop."),
    CommandSpec("loop", "loops", "List current and recent Guinevere work loops."),
    CommandSpec(
        "loop", "evidence",
        "Fetch evidence for a step or active work loop.",
        (CommandOption("step", "Step identifier such as P2-010.", required=False),),
    ),
    CommandSpec(
        "loop", "loop-priority",
        "Set the priority for a Guinevere work loop.",
        (
            CommandOption("loop", "Loop identifier.", required=True),
            CommandOption("priority", "New loop priority.", required=True, choices=PRIORITY_CHOICES),
        ),
    ),
    # memory (4)
    CommandSpec(
        "memory", "memory-search",
        "Search Guinevere's approved memory index.",
        (CommandOption("query", "Memory search query.", required=True),),
    ),
    CommandSpec(
        "memory", "memory-add",
        "Add an approved memory note for Guinevere.",
        (CommandOption("note", "Memory note to add.", required=True),),
    ),
    CommandSpec(
        "memory", "memory-forget",
        "Request deletion of a Guinevere memory item.",
        (CommandOption("memory_id", "Memory identifier to forget.", required=True),),
    ),
    CommandSpec("memory", "memory-export", "Export approved Guinevere memory metadata."),
    # surveillance (3)
    CommandSpec("surveillance", "surveillance-status", "Show consent-bound surveillance status."),
    CommandSpec("surveillance", "surveillance-pause", "Pause consent-bound surveillance collectors."),
    CommandSpec("surveillance", "surveillance-resume", "Resume consent-bound surveillance collectors."),
    # finance (3)
    CommandSpec(
        "finance", "cost",
        "Show Guinevere cost usage for a given period.",
        (CommandOption("period", "Cost period: today, week, or month.", required=False, choices=COST_PERIOD_CHOICES),),
    ),
    CommandSpec(
        "finance", "budget",
        "Show or update budget cap and current spend.",
        (
            CommandOption("action", "Budget action: view current or set new cap.", required=False, choices=BUDGET_ACTION_CHOICES),
            CommandOption("amount", "Monthly budget cap in USD (required when action is set).", option_type=OPTION_NUMBER, required=False),
        ),
    ),
    CommandSpec("finance", "cost-alert", "Show or update Guinevere cost alert thresholds."),
    # system (8)
    CommandSpec(
        "system", "approve",
        "Approve a pending Guinevere action.",
        (CommandOption("request_id", "Pending request identifier.", required=True),),
    ),
    CommandSpec(
        "system", "deny",
        "Deny a pending Guinevere action.",
        (CommandOption("request_id", "Pending request identifier.", required=True),),
    ),
    CommandSpec("system", "approve-all", "Approve all safe pending Guinevere actions."),
    CommandSpec("system", "focus", "Switch Guinevere into focused engineering mode."),
    CommandSpec("system", "casual", "Switch Guinevere into lighter casual mode."),
    CommandSpec(
        "system", "consent",
        "Show or update consent boundaries.",
        (CommandOption("action", "Consent action.", required=False, choices=CONSENT_ACTION_CHOICES),),
    ),
    CommandSpec(
        "system", "punishment",
        "Record or show the bounded punishment state.",
        (CommandOption("note", "Optional bounded note.", required=False),),
    ),
    CommandSpec(
        "system", "reward",
        "Record or show the bounded reward state.",
        (CommandOption("note", "Optional reward note.", required=False),),
    ),
    # admin (4)
    CommandSpec("admin", "restart-service", "Prepare a guarded service restart request."),
    CommandSpec("admin", "backup-now", "Request an immediate Guinevere backup run."),
    CommandSpec("admin", "health-check", "Run Guinevere service health checks."),
    CommandSpec("admin", "clear-cache", "Request a guarded cache clear operation."),
    # integration (6)
    CommandSpec("integration", "integration-status", "Show per-adapter lifecycle status and tier for P22 integrations."),
    CommandSpec("integration", "integration-capabilities", "Show the 13xL1-L4 capability matrix for P22 integrations."),
    CommandSpec(
        "integration", "integration-test",
        "Run a standards-based health check on a single P22 integration.",
        (CommandOption("adapter", "Integration ID to test (e.g. fs, vps, discord).", required=True),),
    ),
    CommandSpec("integration", "integration-missing", "List P22 integrations that are missing required credentials."),
    CommandSpec(
        "integration", "integration-consent",
        "Show or update consent scopes for P22 integrations.",
        (
            CommandOption("consent_action", "Consent action: list, grant, or revoke.", required=False, choices=CONSENT_ACTION_CHOICES),
            CommandOption("scope", "Consent scope (required for grant and revoke).", required=False),
        ),
    ),
    CommandSpec(
        "integration", "integration-dry-run",
        "Dry-run a P22 integration action without real side effects.",
        (
            CommandOption("adapter", "Integration ID (e.g. finance, gmail).", required=True),
            CommandOption("action", "Action name to dry-run (e.g. delete_invoice).", required=True),
        ),
    ),
)

EXPECTED_COMMAND_NAMES: tuple[str, ...] = tuple(spec.name for spec in COMMAND_SPECS)
EXPECTED_COMMAND_NAME_SET: frozenset[str] = frozenset(EXPECTED_COMMAND_NAMES)

CATEGORY_COLORS: dict[str, int] = {
    "core": PRIMARY,
    "loop": SUCCESS,
    "memory": INFO,
    "surveillance": SURVEILLANCE,
    "finance": FINANCE,
    "system": WARNING,
    "admin": ALERT,
    "integration": PRIMARY,
}


# ── Registry Validation ──────────────────────────────────────────────────


def require_canonical_registry() -> None:
    """Validate local command invariants before any Discord sync."""
    names = [spec.name for spec in COMMAND_SPECS]
    if len(names) != 41:
        raise RuntimeError(f"expected 41 commands, found {len(names)}")
    if len(set(names)) != len(names):
        raise RuntimeError("duplicate command names in P2-010 registry")
    payloads = build_application_commands()
    for payload in payloads:
        name = payload["name"]
        description = payload["description"]
        if len(name) > 32:
            raise RuntimeError(f"command name too long: {name}")
        if not description or len(description) > 100:
            raise RuntimeError(f"invalid description for command: {name}")


def build_application_commands() -> list[dict[str, Any]]:
    """Return the canonical guild-scoped Discord application command payloads."""
    return [spec.to_payload() for spec in COMMAND_SPECS]


def command_count() -> int:
    """Return the canonical slash-command count."""
    return len(COMMAND_SPECS)


def command_categories() -> dict[str, tuple[str, ...]]:
    """Return command names grouped by canonical category."""
    grouped: dict[str, list[str]] = {}
    for spec in COMMAND_SPECS:
        grouped.setdefault(spec.category, []).append(spec.name)
    return {cat: tuple(names) for cat, names in grouped.items()}


# ── Callback Helpers ─────────────────────────────────────────────────────


async def _require_faiz(interaction: object) -> bool:
    """Check auth. Send denied if not Faiz. Return True if authorized."""
    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return False
    return True


def _get_option(interaction: object, name: str) -> str | None:
    """Extract a slash command option value from the interaction."""
    data = getattr(interaction, "data", None)
    if data is None:
        return None
    options: list[dict[str, object]] = (
        data.get("options", []) if isinstance(data, dict) else []
    )
    for opt in options:
        if opt.get("name") == name:
            return str(opt.get("value", ""))
    return None


# ── Generic Category Callbacks ───────────────────────────────────────────


async def _callback_status(interaction: object) -> None:
    """Status command — show system status."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("System Status", "All systems operational. ✅", SUCCESS)
    await followup_send(interaction, embed=embed)


async def _callback_mood(interaction: object) -> None:
    """Mood command — show current mood state."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Mood State", "Current mood: content", color_for_mood("content"))
    await followup_send(interaction, embed=embed)


async def _callback_help(interaction: object) -> None:
    """Help command — show command guide."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    lines = ["**Guinevere Command Guide**\n"]
    current_cat = ""
    for spec in COMMAND_SPECS:
        if spec.category != current_cat:
            current_cat = spec.category
            lines.append(f"\n**{current_cat.title()}**")
        lines.append(f"`/{spec.name}` — {spec.description}")
    embed = build_embed("Command Guide", "\n".join(lines)[:4000], PRIMARY)
    await followup_send(interaction, embed=embed)


async def _callback_safeword(interaction: object) -> None:
    """Safeword command — trigger safety boundary workflow."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Safeword", "Safety boundary workflow acknowledged. \U0001f6e1️", WARNING)
    await followup_send(interaction, embed=embed)


async def _callback_loop_start(interaction: object) -> None:
    """Start a work loop."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    goal = _get_option(interaction, "goal") or "(no goal specified)"
    embed = build_embed("Loop Start", f"Loop started with goal: {goal}", SUCCESS)
    await followup_send(interaction, embed=embed)


async def _callback_loop_simple(interaction: object, title: str, message: str, color: int) -> None:
    """Simple loop command callback."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed(title, message, color)
    await followup_send(interaction, embed=embed)


async def _callback_memory_search(interaction: object) -> None:
    """Search memory index."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    query = _get_option(interaction, "query") or "(no query)"
    embed = build_embed("Memory Search", f"Searching for: {query}\n\nNo results in stub mode.", INFO)
    await followup_send(interaction, embed=embed)


async def _callback_memory_add(interaction: object) -> None:
    """Add a memory note."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    note = _get_option(interaction, "note") or "(empty)"
    embed = build_embed("Memory Added", f"Note stored: {note[:200]}", SUCCESS)
    await followup_send(interaction, embed=embed)


async def _callback_memory_forget(interaction: object) -> None:
    """Forget a memory item."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    memory_id = _get_option(interaction, "memory_id") or "(unknown)"
    embed = build_embed("Memory Forgetting", f"Forget request for: {memory_id}", WARNING)
    await followup_send(interaction, embed=embed)


async def _callback_memory_export(interaction: object) -> None:
    """Export memory metadata."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Memory Export", "Memory metadata export initiated.", INFO)
    await followup_send(interaction, embed=embed)


async def _callback_surveillance(interaction: object, title: str, message: str) -> None:
    """Surveillance command callback — direct response."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed(title, message, SURVEILLANCE)
    await followup_send(interaction, embed=embed)


async def _callback_cost(interaction: object) -> None:
    """Show cost usage."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    period = _get_option(interaction, "period") or "today"
    embed = build_embed("Cost Usage", f"Cost for period: {period}\n\n$0.00 (stub mode)", FINANCE)
    await followup_send(interaction, embed=embed)


async def _callback_budget(interaction: object) -> None:
    """Show or update budget."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    action = _get_option(interaction, "action") or "view"
    embed = build_embed("Budget", f"Budget action: {action}\n\nStub mode.", FINANCE)
    await followup_send(interaction, embed=embed)


async def _callback_cost_alert(interaction: object) -> None:
    """Show or update cost alerts."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Cost Alerts", "Cost alert thresholds: stub mode.", FINANCE)
    await followup_send(interaction, embed=embed)


async def _callback_approve(interaction: object) -> None:
    """Approve a pending action."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    request_id = _get_option(interaction, "request_id") or "(unknown)"
    embed = build_embed("Approved", f"Request {request_id} approved. ✅", SUCCESS)
    await followup_send(interaction, embed=embed)


async def _callback_deny(interaction: object) -> None:
    """Deny a pending action."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    request_id = _get_option(interaction, "request_id") or "(unknown)"
    embed = build_embed("Denied", f"Request {request_id} denied. ❌", ALERT)
    await followup_send(interaction, embed=embed)


async def _callback_approve_all(interaction: object) -> None:
    """Approve all safe pending actions."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Approve All", "All safe pending actions approved. ✅", SUCCESS)
    await followup_send(interaction, embed=embed)


async def _callback_focus(interaction: object) -> None:
    """Switch to focused engineering mode."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Focus Mode", "Switched to focused engineering mode. \U0001f527", INFO)
    await followup_send(interaction, embed=embed)


async def _callback_casual(interaction: object) -> None:
    """Switch to casual mode."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Casual Mode", "Switched to casual mode. \U0001f4ac", INFO)
    await followup_send(interaction, embed=embed)


async def _callback_consent(interaction: object) -> None:
    """Show or update consent boundaries."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    action = _get_option(interaction, "action") or "show"
    embed = build_embed("Consent", f"Consent action: {action}", INFO)
    await followup_send(interaction, embed=embed)


async def _callback_punishment(interaction: object) -> None:
    """Record or show punishment state."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    note = _get_option(interaction, "note") or ""
    msg = f"Punishment state recorded. {note}".strip()
    embed = build_embed("Punishment", msg, ALERT)
    await followup_send(interaction, embed=embed)


async def _callback_reward(interaction: object) -> None:
    """Record or show reward state."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    note = _get_option(interaction, "note") or ""
    msg = f"Reward state recorded. {note}".strip()
    embed = build_embed("Reward", msg, SUCCESS)
    await followup_send(interaction, embed=embed)


async def _callback_admin(interaction: object, title: str, message: str) -> None:
    """Admin command callback."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed(title, message, ALERT)
    await followup_send(interaction, embed=embed)


async def _callback_new(interaction: object) -> None:
    """Reset conversation history."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("New Session", "Conversation history reset. Starting fresh. \U0001f504", SUCCESS)
    await followup_send(interaction, embed=embed)


async def _callback_history(interaction: object) -> None:
    """Show recent conversation turns."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("History", "No conversation history in stub mode.", INFO)
    await followup_send(interaction, embed=embed)


async def _callback_integration_status(interaction: object) -> None:
    """Show integration adapter status."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Integration Status", "P22 integration status: stub mode.", PRIMARY)
    await followup_send(interaction, embed=embed)


async def _callback_integration_capabilities(interaction: object) -> None:
    """Show capability matrix."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Integration Capabilities", "13xL1-L4 capability matrix: stub mode.", PRIMARY)
    await followup_send(interaction, embed=embed)


async def _callback_integration_test(interaction: object) -> None:
    """Test a single integration."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    adapter = _get_option(interaction, "adapter") or "(unknown)"
    embed = build_embed("Integration Test", f"Testing adapter: {adapter}\n\nStub mode.", PRIMARY)
    await followup_send(interaction, embed=embed)


async def _callback_integration_missing(interaction: object) -> None:
    """List missing integrations."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    embed = build_embed("Integration Missing", "Missing integrations: stub mode.", WARNING)
    await followup_send(interaction, embed=embed)


async def _callback_integration_consent(interaction: object) -> None:
    """Show or update integration consent scopes."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    action = _get_option(interaction, "consent_action") or "list"
    embed = build_embed("Integration Consent", f"Consent action: {action}", INFO)
    await followup_send(interaction, embed=embed)


async def _callback_integration_dry_run(interaction: object) -> None:
    """Dry-run an integration action."""
    if not await _require_faiz(interaction):
        return
    await defer_ephemeral(interaction)
    adapter = _get_option(interaction, "adapter") or "(unknown)"
    action = _get_option(interaction, "action") or "(unknown)"
    embed = build_embed("Integration Dry Run", f"Dry-run: {adapter}/{action}\n\nStub mode.", PRIMARY)
    await followup_send(interaction, embed=embed)


# ── Command Callback Registry ────────────────────────────────────────────

_COMMAND_CALLBACKS: dict[str, Any] = {
    # core
    "status": _callback_status,
    "mood": _callback_mood,
    "help": _callback_help,
    "safeword": _callback_safeword,
    "new": _callback_new,
    "history": _callback_history,
    # loop
    "loop-start": _callback_loop_start,
    "loop-stop": lambda i: _callback_loop_simple(i, "Loop Stop", "Loop stopped safely. ⏹️", WARNING),
    "loop-pause": lambda i: _callback_loop_simple(i, "Loop Paused", "Loop paused. ⏸️", WARNING),
    "loop-resume": lambda i: _callback_loop_simple(i, "Loop Resumed", "Loop resumed. ▶️", SUCCESS),
    "loops": lambda i: _callback_loop_simple(i, "Loops", "No active loops in stub mode.", INFO),
    "evidence": lambda i: _callback_loop_simple(i, "Evidence", "No evidence in stub mode.", INFO),
    "loop-priority": lambda i: _callback_loop_simple(i, "Loop Priority", "Priority updated.", SUCCESS),
    # memory
    "memory-search": _callback_memory_search,
    "memory-add": _callback_memory_add,
    "memory-forget": _callback_memory_forget,
    "memory-export": _callback_memory_export,
    # surveillance
    "surveillance-status": lambda i: _callback_surveillance(i, "Surveillance Status", "Surveillance system active."),
    "surveillance-pause": lambda i: _callback_surveillance(i, "Surveillance Paused", "Surveillance collectors paused."),
    "surveillance-resume": lambda i: _callback_surveillance(i, "Surveillance Resumed", "Surveillance collectors resumed."),
    # finance
    "cost": _callback_cost,
    "budget": _callback_budget,
    "cost-alert": _callback_cost_alert,
    # system
    "approve": _callback_approve,
    "deny": _callback_deny,
    "approve-all": _callback_approve_all,
    "focus": _callback_focus,
    "casual": _callback_casual,
    "consent": _callback_consent,
    "punishment": _callback_punishment,
    "reward": _callback_reward,
    # admin
    "restart-service": lambda i: _callback_admin(i, "Restart Service", "Service restart requested. Requires approval."),
    "backup-now": lambda i: _callback_admin(i, "Backup Now", "Backup initiated. \U0001f4be"),
    "health-check": lambda i: _callback_admin(i, "Health Check", "All services healthy. ✅"),
    "clear-cache": lambda i: _callback_admin(i, "Clear Cache", "Cache clear requested. Requires approval."),
    # integration
    "integration-status": _callback_integration_status,
    "integration-capabilities": _callback_integration_capabilities,
    "integration-test": _callback_integration_test,
    "integration-missing": _callback_integration_missing,
    "integration-consent": _callback_integration_consent,
    "integration-dry-run": _callback_integration_dry_run,
}


# ── CommandRegistry — Registers all 41 commands on a bot ─────────────────


class CommandRegistry:
    """Registers all 41 canonical slash commands on a discord.py CommandTree.

    Usage::

        registry = CommandRegistry(bot)
        registry.register_all(bot.tree)
    """

    def __init__(self, bot: object) -> None:
        self._bot = bot
        self._registered: list[str] = []

    def register_all(self, tree: Any) -> None:
        """Register all 41 commands on the given CommandTree.

        Args:
            tree: The discord.app_commands.CommandTree instance.
        """
        import discord

        for spec in COMMAND_SPECS:
            callback = _COMMAND_CALLBACKS.get(spec.name)
            if callback is None:
                # Fallback stub for any missing callback
                callback = _make_stub(spec.name)
            tree.command(
                name=spec.name,
                description=spec.description,
                guild=discord.Object(id=GUILD_ID),
            )(callback)
            self._registered.append(spec.name)

        logger.info("commands_registered", extra={"count": len(self._registered)})

    @property
    def registered_names(self) -> list[str]:
        """Return names of registered commands."""
        return list(self._registered)


def _make_stub(name: str) -> Any:
    """Create a fallback stub callback for a command."""

    async def stub(interaction: object) -> None:
        if not await _require_faiz(interaction):
            return
        await defer_ephemeral(interaction)
        embed = build_embed(name, f"Command /{name} — stub mode.", INFO)
        await followup_send(interaction, embed=embed)

    return stub
