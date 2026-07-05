"""M8 Social backend -- X (Twitter) + Telegram real I/O.

7 actions: 2 L1 READ, 3 L2 WRITE, 1 L3 DESTRUCTIVE, 1 L2 WRITE (edit).
Ported from P22 telegram_adapter, X-poster creds.

X API v2: https://api.twitter.com/2/
Telegram Bot API: https://api.telegram.org/bot<token>/

All external calls go through httpx.AsyncClient. OAuth 1.0a signing for
X write operations (post_x, reply_x). Bearer token for X read (read_mentions).
Telegram uses simple Bot API token in URL.

FAIL-SOFT: dispatch() catches ALL exceptions and returns {ok: False, error: ...}.
dispatch NEVER raises to caller.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse
import uuid
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# X API endpoints
_X_TWEETS_URL = "https://api.twitter.com/2/tweets"
_X_MENTIONS_URL = "https://api.twitter.com/2/users/{}/mentions"

# Telegram Bot API base
_TG_API = "https://api.telegram.org/bot{token}/{method}"


# ---------------------------------------------------------------------------
# OAuth 1.0a helpers (pure stdlib, no tweepy dependency)
# ---------------------------------------------------------------------------


def _percent_encode(s: str) -> str:
    """RFC 5849 percent encoding."""
    return urllib.parse.quote(str(s), safe="")


def _build_oauth_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
    params: dict[str, str] | None = None,
) -> str:
    """Build an OAuth 1.0a Authorization header value."""
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    all_params: dict[str, str] = {}
    if params:
        all_params.update(params)
    all_params.update(oauth_params)

    sorted_params = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}"
        for k, v in sorted(all_params.items())
    )
    base_string = f"{method.upper()}&{_percent_encode(url)}&{_percent_encode(sorted_params)}"

    signing_key = f"{_percent_encode(consumer_secret)}&{_percent_encode(access_token_secret)}"
    signature = base64.b64encode(
        hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
    ).decode("utf-8")

    oauth_params["oauth_signature"] = signature

    header = "OAuth " + ", ".join(
        f'{_percent_encode(k)}="{_percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    )
    return header


# ---------------------------------------------------------------------------
# SocialBackend
# ---------------------------------------------------------------------------


class SocialBackend(ToolBackend):
    """Social media backend (L1/L2/L3).

    Actions: post_x, read_mentions, reply_x, send_telegram,
    get_telegram_updates, edit_telegram, delete_telegram.
    """

    @property
    def name(self) -> str:
        return "social"

    def actions(self) -> list[Action]:
        return [
            Action("post_x", ActionTier.L2_WRITE,
                   description="Post a tweet via X API v2"),
            Action("read_mentions", ActionTier.L1_READ,
                   description="Read mentions via X API v2"),
            Action("reply_x", ActionTier.L2_WRITE,
                   description="Reply to a tweet via X API v2"),
            Action("send_telegram", ActionTier.L2_WRITE,
                   description="Send a Telegram message via Bot API"),
            Action("get_telegram_updates", ActionTier.L1_READ,
                   description="Get Telegram updates via Bot API"),
            Action("edit_telegram", ActionTier.L2_WRITE,
                   description="Edit a Telegram message via Bot API"),
            Action("delete_telegram", ActionTier.L3_DESTRUCTIVE,
                   description="Delete a Telegram message via Bot API"),
        ]

    def is_available(self) -> bool:
        """Available if httpx is installed (creds may be config_missing at runtime)."""
        return httpx is not None

    # ------------------------------------------------------------------
    # Credential helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _x_write_creds() -> dict[str, str] | None:
        """Return OAuth 1.0a creds dict or None if incomplete."""
        creds = {
            "api_key": os.environ.get("X_POSTER_X_API_KEY", ""),
            "api_secret": os.environ.get("X_POSTER_X_API_SECRET", ""),
            "access_token": os.environ.get("X_POSTER_X_OAUTH1_ACCESS_TOKEN", ""),
            "access_token_secret": os.environ.get("X_POSTER_X_OAUTH1_ACCESS_TOKEN_SECRET", ""),
        }
        if all(creds.values()):
            return creds
        return None

    @staticmethod
    def _x_bearer_token() -> str | None:
        """Return Bearer token or None."""
        token = os.environ.get("X_POSTER_X_ACCESS_TOKEN", "")
        return token if token else None

    @staticmethod
    def _telegram_token() -> str | None:
        """Return Telegram bot token or None."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        return token if token else None

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a social media action.  NEVER raises to caller."""
        action_lower = action.lower()
        try:
            if action_lower == "post_x":
                return await self._post_x(args)
            if action_lower == "read_mentions":
                return await self._read_mentions(args)
            if action_lower == "reply_x":
                return await self._reply_x(args)
            if action_lower == "send_telegram":
                return await self._send_telegram(args)
            if action_lower == "get_telegram_updates":
                return await self._get_telegram_updates(args)
            if action_lower == "edit_telegram":
                return await self._edit_telegram(args)
            if action_lower == "delete_telegram":
                return await self._delete_telegram(args)
            return {"ok": False, "error": f"unknown social action: {action}"}
        except Exception as exc:
            logger.error("social.dispatch failed action=%s: %s", action, exc, exc_info=True)
            return {"ok": False, "action": action, "error": str(exc)}

    # ------------------------------------------------------------------
    # X / Twitter -- OAuth 1.0a (write) + Bearer (read)
    # ------------------------------------------------------------------

    async def _post_x(self, args: dict[str, Any]) -> dict[str, Any]:
        """Post a tweet. Requires OAuth 1.0a credentials."""
        text = args.get("text", "").strip()
        if not text:
            return {"ok": False, "action": "post_x", "error": "text is empty"}

        creds = self._x_write_creds()
        if not creds:
            return {"ok": False, "action": "post_x",
                    "config_missing": True,
                    "error": "X OAuth 1.0a credentials not configured "
                             "(X_POSTER_X_API_KEY, X_POSTER_X_API_SECRET, "
                             "X_POSTER_X_OAUTH1_ACCESS_TOKEN, "
                             "X_POSTER_X_OAUTH1_ACCESS_TOKEN_SECRET)"}

        payload = {"text": text}

        auth_header = _build_oauth_header(
            "POST", _X_TWEETS_URL,
            creds["api_key"], creds["api_secret"],
            creds["access_token"], creds["access_token_secret"],
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _X_TWEETS_URL,
                json=payload,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

        if resp.status_code >= 400:
            return {"ok": False, "action": "post_x",
                    "error": f"X API error {resp.status_code}: {resp.text}",
                    "status_code": resp.status_code}

        data = resp.json()
        tweet = data.get("data", {})
        return {"ok": True, "action": "post_x",
                "tweet_id": tweet.get("id", ""),
                "text": tweet.get("text", "")}

    async def _read_mentions(self, args: dict[str, Any]) -> dict[str, Any]:
        """Read mentions for a user. Requires Bearer token."""
        user_id = args.get("user_id", "")
        if not user_id:
            return {"ok": False, "action": "read_mentions", "error": "user_id is required"}

        bearer = self._x_bearer_token()
        if not bearer:
            return {"ok": False, "action": "read_mentions",
                    "config_missing": True,
                    "error": "X Bearer token not configured (X_POSTER_X_ACCESS_TOKEN)"}

        max_results = args.get("max_results", 10)
        url = _X_MENTIONS_URL.format(user_id)
        params = {"max_results": max_results}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {bearer}"},
                timeout=30.0,
            )

        if resp.status_code >= 400:
            return {"ok": False, "action": "read_mentions",
                    "error": f"X API error {resp.status_code}: {resp.text}",
                    "status_code": resp.status_code}

        data = resp.json()
        mentions = data.get("data", [])
        meta = data.get("meta", {})
        return {"ok": True, "action": "read_mentions",
                "user_id": user_id,
                "mentions": mentions,
                "count": meta.get("result_count", len(mentions))}

    async def _reply_x(self, args: dict[str, Any]) -> dict[str, Any]:
        """Reply to a tweet. Requires OAuth 1.0a credentials."""
        text = args.get("text", "").strip()
        in_reply_to = args.get("in_reply_to_tweet_id", "").strip()

        if not text:
            return {"ok": False, "action": "reply_x", "error": "text is empty"}
        if not in_reply_to:
            return {"ok": False, "action": "reply_x",
                    "error": "in_reply_to_tweet_id is required"}

        creds = self._x_write_creds()
        if not creds:
            return {"ok": False, "action": "reply_x",
                    "config_missing": True,
                    "error": "X OAuth 1.0a credentials not configured "
                             "(X_POSTER_X_API_KEY, X_POSTER_X_API_SECRET, "
                             "X_POSTER_X_OAUTH1_ACCESS_TOKEN, "
                             "X_POSTER_X_OAUTH1_ACCESS_TOKEN_SECRET)"}

        payload = {
            "text": text,
            "reply": {"in_reply_to_tweet_id": in_reply_to},
        }

        auth_header = _build_oauth_header(
            "POST", _X_TWEETS_URL,
            creds["api_key"], creds["api_secret"],
            creds["access_token"], creds["access_token_secret"],
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _X_TWEETS_URL,
                json=payload,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

        if resp.status_code >= 400:
            return {"ok": False, "action": "reply_x",
                    "error": f"X API error {resp.status_code}: {resp.text}",
                    "status_code": resp.status_code}

        data = resp.json()
        tweet = data.get("data", {})
        return {"ok": True, "action": "reply_x",
                "tweet_id": tweet.get("id", ""),
                "text": tweet.get("text", ""),
                "in_reply_to": in_reply_to}

    # ------------------------------------------------------------------
    # Telegram Bot API
    # ------------------------------------------------------------------

    async def _send_telegram(self, args: dict[str, Any]) -> dict[str, Any]:
        """Send a text message via Telegram Bot API."""
        chat_id = args.get("chat_id", "")
        text = args.get("text", "").strip()

        if not chat_id:
            return {"ok": False, "action": "send_telegram", "error": "chat_id is required"}
        if not text:
            return {"ok": False, "action": "send_telegram", "error": "text is empty"}

        token = self._telegram_token()
        if not token:
            return {"ok": False, "action": "send_telegram",
                    "config_missing": True,
                    "error": "Telegram bot token not configured (TELEGRAM_BOT_TOKEN)"}

        url = _TG_API.format(token=token, method="sendMessage")
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}

        if args.get("parse_mode"):
            payload["parse_mode"] = args["parse_mode"]
        if args.get("reply_to_message_id"):
            payload["reply_to_message_id"] = args["reply_to_message_id"]

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)

        data = resp.json()
        if not data.get("ok"):
            return {"ok": False, "action": "send_telegram",
                    "error": data.get("description", f"HTTP {resp.status_code}")}

        result = data.get("result", {})
        return {"ok": True, "action": "send_telegram",
                "message_id": result.get("message_id"),
                "chat_id": chat_id}

    async def _get_telegram_updates(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get updates (new messages) via Telegram Bot API."""
        token = self._telegram_token()
        if not token:
            return {"ok": False, "action": "get_telegram_updates",
                    "config_missing": True,
                    "error": "Telegram bot token not configured (TELEGRAM_BOT_TOKEN)"}

        url = _TG_API.format(token=token, method="getUpdates")
        params: dict[str, Any] = {}
        if "offset" in args:
            params["offset"] = args["offset"]
        if "limit" in args:
            params["limit"] = args["limit"]
        if "timeout" in args:
            params["timeout"] = args["timeout"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=60.0)

        data = resp.json()
        if not data.get("ok"):
            return {"ok": False, "action": "get_telegram_updates",
                    "error": data.get("description", f"HTTP {resp.status_code}")}

        updates = data.get("result", [])
        return {"ok": True, "action": "get_telegram_updates",
                "updates": updates,
                "count": len(updates)}

    async def _edit_telegram(self, args: dict[str, Any]) -> dict[str, Any]:
        """Edit an existing message via Telegram Bot API."""
        chat_id = args.get("chat_id", "")
        message_id = args.get("message_id")
        text = args.get("text", "").strip()

        if not chat_id:
            return {"ok": False, "action": "edit_telegram", "error": "chat_id is required"}
        if message_id is None:
            return {"ok": False, "action": "edit_telegram", "error": "message_id is required"}
        if not text:
            return {"ok": False, "action": "edit_telegram", "error": "text is empty"}

        token = self._telegram_token()
        if not token:
            return {"ok": False, "action": "edit_telegram",
                    "config_missing": True,
                    "error": "Telegram bot token not configured (TELEGRAM_BOT_TOKEN)"}

        url = _TG_API.format(token=token, method="editMessageText")
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if args.get("parse_mode"):
            payload["parse_mode"] = args["parse_mode"]

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)

        data = resp.json()
        if not data.get("ok"):
            return {"ok": False, "action": "edit_telegram",
                    "error": data.get("description", f"HTTP {resp.status_code}")}

        result = data.get("result", {})
        return {"ok": True, "action": "edit_telegram",
                "edited": True,
                "message_id": result.get("message_id", message_id)}

    async def _delete_telegram(self, args: dict[str, Any]) -> dict[str, Any]:
        """Delete a message via Telegram Bot API."""
        chat_id = args.get("chat_id", "")
        message_id = args.get("message_id")

        if not chat_id:
            return {"ok": False, "action": "delete_telegram", "error": "chat_id is required"}
        if message_id is None:
            return {"ok": False, "action": "delete_telegram", "error": "message_id is required"}

        token = self._telegram_token()
        if not token:
            return {"ok": False, "action": "delete_telegram",
                    "config_missing": True,
                    "error": "Telegram bot token not configured (TELEGRAM_BOT_TOKEN)"}

        url = _TG_API.format(token=token, method="deleteMessage")
        payload = {"chat_id": chat_id, "message_id": message_id}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)

        data = resp.json()
        if not data.get("ok"):
            return {"ok": False, "action": "delete_telegram",
                    "error": data.get("description", f"HTTP {resp.status_code}")}

        return {"ok": True, "action": "delete_telegram",
                "deleted": True,
                "message_id": message_id,
                "restore_method": "message deleted from Telegram; no native restore"}
