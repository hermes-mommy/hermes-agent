"""P22.3 Onboarding manifest (B5) — per-adapter onboarding metadata.

Surfaces env-var NAMES (never values), pip packages, OAuth steps, consent
scopes, docs_url. Used by /integrations/missing (B1 endpoint) + Wave G
tutorial generator. INVARIANT: pure static metadata — never reads the process
environment. EnvVarHint.name is safe to print; the VALUE is never stored.
"""

from __future__ import annotations

from pydantic import BaseModel


class EnvVarHint(BaseModel):
    """A single environment variable hint (NAME + description, never value)."""

    name: str
    description: str
    sensitive: bool = True
    example_format: str | None = None


class AdapterOnboarding(BaseModel):
    """Onboarding metadata for one integration adapter."""

    integration_id: str
    pip_packages: tuple[str, ...] = ()
    env_vars: tuple[EnvVarHint, ...] = ()
    oauth_steps: tuple[str, ...] = ()
    docs_url: str | None = None
    consent_scopes: tuple[str, ...] = ()
    minimum_l_tier: str = "L1_READ"
    notes: str = ""


def _ev(name: str, desc: str, fmt: str | None = None, sensitive: bool = True) -> EnvVarHint:
    return EnvVarHint(name=name, description=desc, example_format=fmt, sensitive=sensitive)


ONBOARDING_MANIFEST: dict[str, AdapterOnboarding] = {
    "discord": AdapterOnboarding(
        integration_id="discord",
        env_vars=(_ev("DISCORD_BOT_TOKEN", "Discord bot token (already provisioned).", "<bot_token>"),),
        oauth_steps=("Token from Discord Developer Portal (already provisioned).",),
        docs_url="https://discord.com/developers/docs",
        consent_scopes=("consent.comms.discord.read", "consent.comms.discord.write", "consent.comms.discord.delete"),
        notes="Already ACTIVE on VPS via .env.core DISCORD_BOT_TOKEN.",
    ),
    "gmail": AdapterOnboarding(
        integration_id="gmail",
        pip_packages=("google-api-python-client", "google-auth-oauthlib"),
        env_vars=(_ev("GMAIL_OAUTH_TOKEN_PATH", "Path to Gmail OAuth token JSON (SOPS-decrypted).", "/run/guinevere/gmail-token.json"),),
        oauth_steps=(
            "Google Cloud Console -> Desktop app OAuth client.",
            "Scope: gmail.modify (covers trash/untrash/modify/send, NOT permanent delete).",
            "InstalledAppFlow one-shot consent -> SOPS /run/guinevere/gmail-token.json (0600).",
        ),
        docs_url="https://developers.google.com/workspace/gmail/api/auth/scopes",
        consent_scopes=("consent.comms.gmail.read", "consent.comms.gmail.write", "consent.comms.gmail.delete"),
        notes="guinevere-gmail.service exists; token at /run/guinevere/gmail-token.json.",
    ),
    "github": AdapterOnboarding(
        integration_id="github",
        env_vars=(_ev("GITHUB_PAT", "GitHub fine-grained PAT (Administration:write for L4; Contents/Issues/Pull_requests write).", "ghp_<40 chars>"),),
        oauth_steps=(
            "GitHub Settings -> Developer settings -> Fine-grained PAT.",
            "Permissions: Administration:write (L4), Contents/Issues/Pull_requests:write (L2).",
            "SOPS sec-github-pat (already provisioned). L2/L3 proof needs operator-designated TEST REPO.",
        ),
        docs_url="https://docs.github.com/en/rest/overview/authenticating-to-the-rest-api",
        consent_scopes=("consent.sourcecode.github.read", "consent.sourcecode.github.write", "consent.sourcecode.github.delete"),
        notes="L1 ACTIVE (GITHUB_PAT via SOPS). L4 delete_repo/force_push require operator-designated test repo.",
    ),
    "calendar": AdapterOnboarding(
        integration_id="calendar",
        pip_packages=("google-api-python-client", "google-auth-oauthlib"),
        env_vars=(_ev("CALENDAR_OAUTH_TOKEN_PATH", "Path to Google Calendar OAuth token JSON (SOPS-decrypted).", "/run/guinevere/calendar-token.json"),),
        oauth_steps=(
            "Shared Google Cloud OAuth Desktop app (with gmail/drive).",
            "Scopes: calendar.events.owned + calendar.calendars + calendar.calendarlist + calendar.acls + calendar.settings.readonly (Sensitive, no CASA).",
            "InstalledAppFlow one-shot -> SOPS /run/guinevere/calendar-token.json (0600).",
        ),
        docs_url="https://developers.google.com/workspace/calendar/api/auth-scopes",
        consent_scopes=("consent.cloud.calendar.read", "consent.cloud.calendar.write", "consent.cloud.calendar.delete"),
        notes="NO native undelete. calendars.clear/delete = L4 irreversible.",
    ),
    "drive": AdapterOnboarding(
        integration_id="drive",
        pip_packages=("google-api-python-client", "google-auth-oauthlib"),
        env_vars=(_ev("DRIVE_OAUTH_TOKEN_PATH", "Path to Google Drive OAuth token JSON (SOPS-decrypted).", "/run/guinevere/drive-token.json"),),
        oauth_steps=(
            "Shared Google Cloud OAuth Desktop app (with gmail/calendar).",
            "Scope: drive.file (Sensitive, no CASA; per-file only).",
            "InstalledAppFlow one-shot -> SOPS /run/guinevere/drive-token.json (0600).",
        ),
        docs_url="https://developers.google.com/workspace/drive/api/api-specific-auth",
        consent_scopes=("consent.cloud.drive.read", "consent.cloud.drive.write", "consent.cloud.drive.delete"),
        notes="Trash-first (30d). files.delete = L3 permanent. empty_trash = L4.",
    ),
    "notion": AdapterOnboarding(
        integration_id="notion",
        env_vars=(_ev("NOTION_TOKEN", "Notion internal integration token (ntn_ or secret_ prefix).", "ntn_<43 chars>"),),
        oauth_steps=(
            "notion.so/my-integrations -> New connection -> Internal integration.",
            "Capabilities: Read content, Update content, Insert content, Read user info.",
            "Share target pages/databases with the integration.",
            "SOPS sec-notion-integration-token.",
        ),
        docs_url="https://developers.notion.com/reference/authentication",
        consent_scopes=("consent.notes.notion.read", "consent.notes.notion.write", "consent.notes.notion.delete"),
        notes="Archive-not-delete (in_trash:true, restorable). delete_view = L4 sole permanent. Notion-Version: 2026-03-11.",
    ),
    "telegram": AdapterOnboarding(
        integration_id="telegram",
        env_vars=(
            _ev("TELEGRAM_BOT_TOKEN", "Telegram bot token from BotFather (bot_id:35-char-auth).", "<digits>:<35 chars>"),
            _ev("TELEGRAM_WEBHOOK_SECRET", "Optional webhook HMAC secret.", "<64 hex>"),
        ),
        oauth_steps=(
            "BotFather /newbot -> @username (ends in bot) -> token.",
            "/setprivacy.",
            "SOPS sec-telegram-bot-token.",
        ),
        docs_url="https://core.telegram.org/bots/api",
        consent_scopes=("consent.comms.telegram.read", "consent.comms.telegram.write", "consent.comms.telegram.delete"),
        notes="Token-in-URL (no Bearer). promoteChatMember = L4. deleteMessage irreversible.",
    ),
    "whatsapp": AdapterOnboarding(
        integration_id="whatsapp",
        env_vars=(
            _ev("WHATSAPP_BRIDGE_URL", "guinevere-whatsapp.service HTTP bridge URL (loopback).", "http://127.0.0.1:8095", sensitive=False),
            _ev("WA_TEST_JID", "Operator-designated test JID for L2 send_text proof.", "<jid>@s.whatsapp.net"),
        ),
        oauth_steps=(
            "guinevere-whatsapp.service owns the Baileys session.",
            "WA_TEST_JID env knob for L2 send_text proof.",
        ),
        docs_url="https://core.telegram.org/bots/api",
        consent_scopes=("consent.comms.whatsapp.read", "consent.comms.whatsapp.write", "consent.comms.whatsapp.delete"),
        notes="L1 health ACTIVE. L2 send_text needs WA_TEST_JID. L3 delete_for_everyone = DEFERRED (service-bus gap).",
    ),
    "vps": AdapterOnboarding(
        integration_id="vps",
        env_vars=(_ev("DATABASE_URL", "Postgres async URL for metrics (already provisioned).", "postgresql://...", sensitive=False),),
        oauth_steps=("docker CLI + shell_tool + psutil in-tree; DATABASE_URL for metrics.",),
        docs_url="https://docs.docker.com/engine/api/",
        consent_scopes=("consent.ops.vps.read", "consent.ops.vps.write", "consent.ops.vps.delete"),
        notes="system_prune/docker_rm_all = L4. remove_container L3.",
    ),
    "finance": AdapterOnboarding(
        integration_id="finance",
        env_vars=(_ev("DATABASE_URL", "Postgres URL for finance.* tables (already provisioned).", "postgresql://...", sensitive=False),),
        oauth_steps=("Postgres finance.* tables; _BLOCKED_ACTIONS regex blocks pay/transfer/withdraw/invest L4.",),
        docs_url="https://www.postgresql.org/docs/",
        consent_scopes=("consent.finance.read", "consent.finance.write", "consent.finance.delete"),
        notes="L1 read ACTIVE. L2 record_transaction DEFERRED_FOR_SAFETY. L4 pay/transfer blocked.",
    ),
    "browser": AdapterOnboarding(
        integration_id="browser",
        env_vars=(
            _ev("BRAVE_API_KEY", "Brave Search API key (optional).", "BSA<chars>"),
            _ev("EXA_API_KEY", "Exa Search API key (optional).", "<hex>"),
            _ev("OBSCURA_CDP_URL", "Obscura CDP WebSocket URL (live).", "ws://127.0.0.1:9222", sensitive=False),
        ),
        oauth_steps=(
            "Obscura CDP at ws://127.0.0.1:9222 (live, no key).",
            "Brave/Exa keys optional for search.",
            "httpbin for L2 fill_form/click test.",
        ),
        docs_url="https://developers.google.com/workspace",
        consent_scopes=("consent.research.browser.read", "consent.research.browser.write"),
        notes="fetch/navigate L1 ACTIVE. search CONFIG_MISSING without Brave/Exa. No delete tier.",
    ),
    "memory": AdapterOnboarding(
        integration_id="memory",
        env_vars=(_ev("DATABASE_URL", "Postgres URL (p22_session_factory) for memory + pgvector.", "postgresql://...", sensitive=False),),
        oauth_steps=("p22_session_factory from DATABASE_URL; mark_dnr preserves DNR auth whitelist.",),
        docs_url="https://www.postgresql.org/docs/",
        consent_scopes=("consent.memory.read", "consent.memory.write", "consent.memory.delete"),
        notes="recall/search_kg L1 ACTIVE. store/store_fact L2. mark_dnr L3. delete_memory L4.",
    ),
    "filesystem": AdapterOnboarding(
        integration_id="filesystem",
        oauth_steps=("Self-contained workspace_root; _FORBIDDEN_PATHS enforced.",),
        consent_scopes=("consent.filesystem.read", "consent.filesystem.write", "consent.filesystem.delete"),
        notes="list_dir L1 ACTIVE. write L2. delete L3 (content_hash, git-restore if tracked). forbidden_path L4.",
    ),
}
