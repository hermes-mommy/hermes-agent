"""Discord command registry — canonical slash-command spec and payload builders.

Extracted from ``guinvere.discord.commands`` (deprecated) into an independent
non-deprecated module so that ``bot.py`` and test files can import registry
members without referencing the deprecated ``commands.py`` module.

The command registry is intentionally represented as Discord REST payloads so the
P2-010 verifier can guild-sync the command surface without starting a long-lived
bot process or exposing the bot token through argv/environment logs. Runtime
handlers are implemented in later P2 steps and can reuse the same canonical
``COMMAND_SPECS`` table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NotRequired, TypedDict

GUILD_ID = 1_510_876_414_671_323_206
APPLICATION_ID = 1_510_873_134_981_582_858
SLASH_COMMAND_TYPE = 1
OPTION_STRING = 3
OPTION_INTEGER = 4
OPTION_BOOLEAN = 5
OPTION_NUMBER = 10


class ChoicePayload(TypedDict):
    """Discord application-command option choice payload."""

    name: str
    value: str | int


class OptionPayload(TypedDict):
    """Discord application-command option payload."""

    type: int
    name: str
    description: str
    required: bool
    choices: NotRequired[list[ChoicePayload]]


class CommandPayload(TypedDict):
    """Discord application-command REST payload."""

    type: int
    name: str
    description: str
    options: NotRequired[list[OptionPayload]]


@dataclass(frozen=True)
class CommandOption:
    """Canonical slash-command parameter definition."""

    name: str
    description: str
    option_type: int = OPTION_STRING
    required: bool = False
    choices: tuple[tuple[str, str | int], ...] = ()

    def to_payload(self) -> OptionPayload:
        """Convert the option to a Discord REST payload."""

        payload: OptionPayload = {
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

    def to_payload(self) -> CommandPayload:
        """Convert the command to a Discord REST payload."""

        payload: CommandPayload = {
            "type": SLASH_COMMAND_TYPE,
            "name": self.name,
            "description": self.description,
        }
        if self.options:
            payload["options"] = [option.to_payload() for option in self.options]
        return payload


PERSONA_CHOICES = (
    ("Focus", "focus"),
    ("Casual", "casual"),
    ("Content", "content"),
)

PRIORITY_CHOICES = (
    ("Low", "low"),
    ("Normal", "normal"),
    ("High", "high"),
    ("Urgent", "urgent"),
)

CONSENT_ACTION_CHOICES = (
    ("Show", "show"),
    ("Grant", "grant"),
    ("Revoke", "revoke"),
)

COST_PERIOD_CHOICES = (
    ("Today", "today"),
    ("Week", "week"),
    ("Month", "month"),
)

BUDGET_ACTION_CHOICES = (
    ("View", "view"),
    ("Set", "set"),
)

COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec("core", "status", "Show Mommy's current system, loop, and safety status."),
    CommandSpec("core", "mood", "Show or update Guinevere's current mood state."),
    CommandSpec("core", "help", "Show the Guinevere command guide."),
    CommandSpec("core", "safeword", "Trigger the configured safety boundary workflow."),
    CommandSpec(
        "loop",
        "loop-start",
        "Start a supervised Guinevere work loop.",
        (CommandOption("goal", "Work-loop goal for Mommy to execute.", required=True),),
    ),
    CommandSpec("loop", "loop-stop", "Stop the active Guinevere work loop safely."),
    CommandSpec("loop", "loop-pause", "Pause the active Guinevere work loop."),
    CommandSpec("loop", "loop-resume", "Resume a paused Guinevere work loop."),
    CommandSpec("loop", "loops", "List current and recent Guinevere work loops."),
    CommandSpec(
        "loop",
        "evidence",
        "Fetch evidence for a step or active work loop.",
        (CommandOption("step", "Step identifier such as P2-010.", required=False),),
    ),
    CommandSpec(
        "loop",
        "loop-priority",
        "Set the priority for a Guinevere work loop.",
        (
            CommandOption("loop", "Loop identifier.", required=True),
            CommandOption("priority", "New loop priority.", required=True, choices=PRIORITY_CHOICES),
        ),
    ),
    CommandSpec(
        "memory",
        "memory-search",
        "Search Guinevere's approved memory index.",
        (CommandOption("query", "Memory search query.", required=True),),
    ),
    CommandSpec(
        "memory",
        "memory-add",
        "Add an approved memory note for Guinevere.",
        (CommandOption("note", "Memory note to add.", required=True),),
    ),
    CommandSpec(
        "memory",
        "memory-forget",
        "Request deletion of a Guinevere memory item.",
        (CommandOption("memory_id", "Memory identifier to forget.", required=True),),
    ),
    CommandSpec("memory", "memory-export", "Export approved Guinevere memory metadata."),
    CommandSpec("surveillance", "surveillance-status", "Show consent-bound surveillance status."),
    CommandSpec("surveillance", "surveillance-pause", "Pause consent-bound surveillance collectors."),
    CommandSpec("surveillance", "surveillance-resume", "Resume consent-bound surveillance collectors."),
    CommandSpec(
        "finance",
        "cost",
        "Show Guinevere cost usage for a given period.",
        (CommandOption(
            "period",
            "Cost period: today, week, or month.",
            required=False,
            choices=COST_PERIOD_CHOICES,
        ),),
    ),
    CommandSpec(
        "finance",
        "budget",
        "Show or update budget cap and current spend.",
        (
            CommandOption(
                "action",
                "Budget action: view current or set new cap.",
                required=False,
                choices=BUDGET_ACTION_CHOICES,
            ),
            CommandOption(
                "amount",
                "Monthly budget cap in USD (required when action is set).",
                option_type=OPTION_NUMBER,
                required=False,
            ),
        ),
    ),
    CommandSpec("finance", "cost-alert", "Show or update Guinevere cost alert thresholds."),
    CommandSpec(
        "system",
        "approve",
        "Approve a pending Guinevere action.",
        (CommandOption("request_id", "Pending request identifier.", required=True),),
    ),
    CommandSpec(
        "system",
        "deny",
        "Deny a pending Guinevere action.",
        (CommandOption("request_id", "Pending request identifier.", required=True),),
    ),
    CommandSpec("system", "approve-all", "Approve all safe pending Guinevere actions."),
    CommandSpec("system", "focus", "Switch Guinevere into focused engineering mode."),
    CommandSpec("system", "casual", "Switch Guinevere into lighter casual mode."),
    CommandSpec(
        "system",
        "consent",
        "Show or update consent boundaries.",
        (CommandOption("action", "Consent action.", required=False, choices=CONSENT_ACTION_CHOICES),),
    ),
    CommandSpec(
        "system",
        "punishment",
        "Record or show the bounded punishment state.",
        (CommandOption("note", "Optional bounded note.", required=False),),
    ),
    CommandSpec(
        "system",
        "reward",
        "Record or show the bounded reward state.",
        (CommandOption("note", "Optional reward note.", required=False),),
    ),
    CommandSpec("admin", "restart-service", "Prepare a guarded service restart request."),
    CommandSpec("admin", "backup-now", "Request an immediate Guinevere backup run."),
    CommandSpec("admin", "health-check", "Run Guinevere service health checks."),
    CommandSpec("admin", "clear-cache", "Request a guarded cache clear operation."),
    # Hermes Phase 1: Conversation session commands
    CommandSpec("core", "new", "Reset conversation history and start fresh."),
    CommandSpec("core", "history", "Show recent conversation turns with Mommy."),
    # P22 Phase B: Life Integration Hub commands
    CommandSpec(
        "integration",
        "integration-status",
        "Show per-adapter lifecycle status and tier for P22 integrations.",
    ),
    CommandSpec(
        "integration",
        "integration-capabilities",
        "Show the 13×L1-L4 capability matrix for P22 integrations.",
    ),
    CommandSpec(
        "integration",
        "integration-test",
        "Run a standards-based health check on a single P22 integration.",
        (CommandOption("adapter", "Integration ID to test (e.g. fs, vps, discord).", required=True),),
    ),
    CommandSpec(
        "integration",
        "integration-missing",
        "List P22 integrations that are missing required credentials.",
    ),
    CommandSpec(
        "integration",
        "integration-consent",
        "Show or update consent scopes for P22 integrations.",
        (
            CommandOption(
                "consent_action",
                "Consent action: list, grant, or revoke.",
                required=False,
                choices=CONSENT_ACTION_CHOICES,
            ),
            CommandOption(
                "scope",
                "Consent scope (required for grant and revoke).",
                required=False,
            ),
        ),
    ),
    CommandSpec(
        "integration",
        "integration-dry-run",
        "Dry-run a P22 integration action without real side effects.",
        (
            CommandOption("adapter", "Integration ID (e.g. finance, gmail).", required=True),
            CommandOption("action", "Action name to dry-run (e.g. delete_invoice).", required=True),
        ),
    ),
)

EXPECTED_COMMAND_NAMES = tuple(spec.name for spec in COMMAND_SPECS)
EXPECTED_COMMAND_NAME_SET = frozenset(EXPECTED_COMMAND_NAMES)


def build_application_commands() -> list[CommandPayload]:
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
    return {category: tuple(names) for category, names in grouped.items()}


def unknown_command_names(names: set[str]) -> set[str]:
    """Return names that are not part of the canonical P2-010 command set."""

    return names - set(EXPECTED_COMMAND_NAME_SET)


def missing_command_names(names: set[str]) -> set[str]:
    """Return canonical command names absent from a synced guild command set."""

    return set(EXPECTED_COMMAND_NAME_SET) - names


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


def command_payloads_as_objects() -> list[dict[str, object]]:
    """Return payloads as plain dictionaries for the shared REST helper."""

    converted: list[dict[str, object]] = []
    for payload in build_application_commands():
        item: dict[str, object] = {
            "type": payload["type"],
            "name": payload["name"],
            "description": payload["description"],
        }
        options = payload.get("options")
        if options is not None:
            item["options"] = options
        converted.append(item)
    return converted
