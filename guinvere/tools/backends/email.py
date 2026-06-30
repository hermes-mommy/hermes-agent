"""M8 Email backend — Gmail API (google-api-python-client).

Ported from: P22 gmail_adapter.py, P23 email_executor (Section 4.8).
Channel-adjacent (M14 shares).

10 actions: 3 L1 READ, 7 L2 WRITE.

Real Gmail API calls via googleapiclient + OAuth2 credentials.
Creds loaded from GMAIL_CREDENTIALS_PATH (default: secrets/gmail-token.json).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credential paths (env overridable, production defaults)
# ---------------------------------------------------------------------------

_CREDENTIALS_PATH = os.environ.get(
    "GMAIL_CREDENTIALS_PATH",
    "/home/guinevere/code/guinevere/secrets/gmail-token.json",
)

# Scope used by the Gmail token
_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _build_gmail_service():
    """Build an authenticated Gmail API service object.

    Reads OAuth2 credentials (client_id, client_secret, refresh_token) from
    the credentials JSON file.  The access token is refreshed automatically
    by the google-auth library if expired.

    Raises:
        FileNotFoundError: if credentials file does not exist.
        KeyError / json.JSONDecodeError: if credentials file is malformed.
        google.auth.exceptions.RefreshError: if the refresh token is revoked.
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds_path = Path(_CREDENTIALS_PATH)
    if not creds_path.exists():
        raise FileNotFoundError(f"Gmail credentials not found: {creds_path}")

    token_data = json.loads(creds_path.read_text(encoding="utf-8"))

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", _GMAIL_SCOPES),
    )

    return build("gmail", "v1", credentials=creds)


def _extract_headers(payload: dict[str, Any]) -> dict[str, str]:
    """Extract From/To/Subject/Date from a Gmail payload headers list."""
    headers = {}
    for h in payload.get("headers", []):
        name = h.get("name", "").lower()
        if name in ("from", "to", "subject", "date"):
            headers[name] = h.get("value", "")
    return headers


def _decode_body(payload: dict[str, Any]) -> str:
    """Decode the body from a Gmail message payload.

    Handles both simple (payload.body.data) and multipart messages
    (walks parts recursively for text/plain first, then text/html).
    """
    # Simple body
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    # Multipart — prefer text/plain
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            pd = part.get("body", {}).get("data")
            if pd:
                return base64.urlsafe_b64decode(pd).decode("utf-8", errors="replace")

    # Fallback: text/html
    for part in parts:
        if part.get("mimeType") == "text/html":
            pd = part.get("body", {}).get("data")
            if pd:
                return base64.urlsafe_b64decode(pd).decode("utf-8", errors="replace")

    # Recurse into nested multipart
    for part in parts:
        nested = _decode_body(part)
        if nested:
            return nested

    return ""


def _summarize_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Build a summary dict from a Gmail message resource."""
    payload = msg.get("payload", {})
    headers = _extract_headers(payload)
    return {
        "id": msg.get("id", ""),
        "thread_id": msg.get("threadId", ""),
        "label_ids": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
    }


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


class EmailBackend(ToolBackend):
    """Email backend (Gmail API, L1/L2).

    Actions: list_inbox, search, read, send, reply, forward,
    create_draft, modify_labels, mark_read, flag.
    """

    @property
    def name(self) -> str:
        return "email"

    def actions(self) -> list[Action]:
        return [
            Action("list_inbox", ActionTier.L1_READ, description="List inbox messages"),
            Action("search", ActionTier.L1_READ, description="Search emails"),
            Action("read", ActionTier.L1_READ, description="Read message by id"),
            Action("send", ActionTier.L2_WRITE, description="Send email"),
            Action("reply", ActionTier.L2_WRITE, description="Reply to email"),
            Action("forward", ActionTier.L2_WRITE, description="Forward email"),
            Action("create_draft", ActionTier.L2_WRITE, description="Create draft"),
            Action("modify_labels", ActionTier.L2_WRITE, description="Modify message labels"),
            Action("mark_read", ActionTier.L2_WRITE, description="Mark as read"),
            Action("flag", ActionTier.L2_WRITE, description="Flag/star message"),
        ]

    def is_available(self) -> bool:
        """Return True if Gmail credentials file exists."""
        return Path(_CREDENTIALS_PATH).exists()

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a Gmail action via google-api-python-client.

        All actions make REAL Gmail API calls.  Errors are caught and returned
        as ``{"ok": False, "error": ...}`` (fail-soft — never raise to caller).
        """
        action_lower = action.lower()

        try:
            svc = _build_gmail_service()
            messages = svc.messages()
            threads = svc.threads()
            drafts = svc.drafts()

            # -----------------------------------------------------------------
            # L1 READ actions
            # -----------------------------------------------------------------

            if action_lower == "list_inbox":
                max_results = args.get("max_results", 20)
                query = args.get("query", "in:inbox")
                resp = messages.list(userId="me", q=query, maxResults=max_results).execute()
                msg_summaries = resp.get("messages", [])
                # Enrich with headers
                enriched = []
                for m in msg_summaries[:max_results]:
                    try:
                        full = messages.get(userId="me", id=m["id"], format="metadata",
                                            metadataHeaders=["From", "To", "Subject", "Date"]).execute()
                        enriched.append(_summarize_message(full))
                    except Exception:
                        enriched.append({"id": m["id"], "thread_id": m.get("threadId", "")})
                return {
                    "ok": True,
                    "action": action,
                    "messages": enriched,
                    "count": len(enriched),
                    "result_size_estimate": resp.get("resultSizeEstimate", 0),
                }

            if action_lower == "search":
                query = args.get("query", "")
                max_results = args.get("max_results", 20)
                if not query:
                    return {"ok": False, "action": action, "error": "query is required"}
                resp = messages.list(userId="me", q=query, maxResults=max_results).execute()
                msg_summaries = resp.get("messages", [])
                enriched = []
                for m in msg_summaries[:max_results]:
                    try:
                        full = messages.get(userId="me", id=m["id"], format="metadata",
                                            metadataHeaders=["From", "To", "Subject", "Date"]).execute()
                        enriched.append(_summarize_message(full))
                    except Exception:
                        enriched.append({"id": m["id"], "thread_id": m.get("threadId", "")})
                return {
                    "ok": True,
                    "action": action,
                    "query": query,
                    "results": enriched,
                    "count": len(enriched),
                    "result_size_estimate": resp.get("resultSizeEstimate", 0),
                }

            if action_lower == "read":
                msg_id = args.get("msg_id", "")
                if not msg_id:
                    return {"ok": False, "action": action, "error": "msg_id is required"}
                msg = messages.get(userId="me", id=msg_id, format="full").execute()
                payload = msg.get("payload", {})
                headers = _extract_headers(payload)
                body = _decode_body(payload)
                return {
                    "ok": True,
                    "action": action,
                    "msg_id": msg_id,
                    "thread_id": msg.get("threadId", ""),
                    "label_ids": msg.get("labelIds", []),
                    "from": headers.get("from", ""),
                    "to": headers.get("to", ""),
                    "subject": headers.get("subject", ""),
                    "date": headers.get("date", ""),
                    "body": body,
                    "snippet": msg.get("snippet", ""),
                }

            if action_lower == "get_thread":
                thread_id = args.get("thread_id", "")
                if not thread_id:
                    return {"ok": False, "action": action, "error": "thread_id is required"}
                thread = threads.get(userId="me", id=thread_id, format="full").execute()
                thread_messages = thread.get("messages", [])
                summaries = []
                for m in thread_messages:
                    payload = m.get("payload", {})
                    headers = _extract_headers(payload)
                    body = _decode_body(payload)
                    summaries.append({
                        "id": m.get("id", ""),
                        "from": headers.get("from", ""),
                        "to": headers.get("to", ""),
                        "subject": headers.get("subject", ""),
                        "date": headers.get("date", ""),
                        "body": body,
                        "snippet": m.get("snippet", ""),
                    })
                return {
                    "ok": True,
                    "action": action,
                    "thread_id": thread_id,
                    "messages": summaries,
                    "message_count": len(summaries),
                }

            # -----------------------------------------------------------------
            # L2 WRITE actions
            # -----------------------------------------------------------------

            if action_lower == "send":
                to = args.get("to", "")
                subject = args.get("subject", "")
                body = args.get("body", "")
                if not to:
                    return {"ok": False, "action": action, "error": "'to' is required"}
                mime = MIMEText(body)
                mime["to"] = to
                if subject:
                    mime["subject"] = subject
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
                resp = messages.send(userId="me", body={"raw": raw}).execute()
                return {
                    "ok": True,
                    "action": action,
                    "msg_id": resp.get("id", ""),
                    "thread_id": resp.get("threadId", ""),
                    "label_ids": resp.get("labelIds", []),
                    "sent": True,
                }

            if action_lower == "reply":
                msg_id = args.get("msg_id", "")
                body = args.get("body", "")
                if not msg_id:
                    return {"ok": False, "action": action, "error": "msg_id is required"}
                # Fetch original to get headers for proper threading
                original = messages.get(userId="me", id=msg_id, format="metadata",
                                        metadataHeaders=["From", "To", "Subject", "Message-ID"]).execute()
                orig_headers = _extract_headers(original.get("payload", {}))
                thread_id = original.get("threadId", "")
                reply_to = orig_headers.get("from", "")
                reply_subject = orig_headers.get("subject", "")
                if reply_subject and not reply_subject.lower().startswith("re:"):
                    reply_subject = "Re: " + reply_subject

                mime = MIMEText(body)
                mime["to"] = reply_to
                mime["subject"] = reply_subject
                mime["In-Reply-To"] = msg_id
                mime["References"] = msg_id
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
                resp = messages.send(userId="me", body={"raw": raw, "threadId": thread_id}).execute()
                return {
                    "ok": True,
                    "action": action,
                    "msg_id": resp.get("id", ""),
                    "thread_id": resp.get("threadId", ""),
                    "sent": True,
                }

            if action_lower == "forward":
                msg_id = args.get("msg_id", "")
                to = args.get("to", "")
                if not msg_id:
                    return {"ok": False, "action": action, "error": "msg_id is required"}
                if not to:
                    return {"ok": False, "action": action, "error": "'to' is required"}
                # Fetch original
                original = messages.get(userId="me", id=msg_id, format="full").execute()
                orig_headers = _extract_headers(original.get("payload", {}))
                orig_body = _decode_body(original.get("payload", {}))
                fwd_subject = orig_headers.get("subject", "")
                if fwd_subject and not fwd_subject.lower().startswith("fwd:"):
                    fwd_subject = "Fwd: " + fwd_subject
                fwd_body = (
                    f"---------- Forwarded message ---------\n"
                    f"From: {orig_headers.get('from', '')}\n"
                    f"Date: {orig_headers.get('date', '')}\n"
                    f"Subject: {fwd_subject}\n"
                    f"To: {orig_headers.get('to', '')}\n\n"
                    f"{orig_body}"
                )
                mime = MIMEText(fwd_body)
                mime["to"] = to
                mime["subject"] = fwd_subject
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
                resp = messages.send(userId="me", body={"raw": raw}).execute()
                return {
                    "ok": True,
                    "action": action,
                    "msg_id": resp.get("id", ""),
                    "thread_id": resp.get("threadId", ""),
                    "forwarded": True,
                }

            if action_lower == "create_draft":
                to = args.get("to", "")
                subject = args.get("subject", "")
                body = args.get("body", "")
                if not to:
                    return {"ok": False, "action": action, "error": "'to' is required"}
                if not subject:
                    return {"ok": False, "action": action, "error": "'subject' is required"}
                mime = MIMEText(body)
                mime["to"] = to
                mime["subject"] = subject
                raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
                resp = drafts.create(userId="me", body={"message": {"raw": raw}}).execute()
                return {
                    "ok": True,
                    "action": action,
                    "draft_id": resp.get("id", ""),
                    "msg_id": resp.get("message", {}).get("id", ""),
                    "to": to,
                    "subject": subject,
                }

            if action_lower == "modify_labels":
                msg_id = args.get("msg_id", "")
                add_labels = args.get("add_labels", [])
                remove_labels = args.get("remove_labels", [])
                if not msg_id:
                    return {"ok": False, "action": action, "error": "msg_id is required"}
                body = {"addLabelIds": add_labels, "removeLabelIds": remove_labels}
                resp = messages.modify(userId="me", id=msg_id, body=body).execute()
                return {
                    "ok": True,
                    "action": action,
                    "msg_id": msg_id,
                    "label_ids": resp.get("labelIds", []),
                    "add_labels": add_labels,
                    "remove_labels": remove_labels,
                }

            if action_lower == "mark_read":
                msg_id = args.get("msg_id", "")
                if not msg_id:
                    return {"ok": False, "action": action, "error": "msg_id is required"}
                body = {"removeLabelIds": ["UNREAD"]}
                messages.modify(userId="me", id=msg_id, body=body).execute()
                return {
                    "ok": True,
                    "action": action,
                    "msg_id": msg_id,
                    "marked": True,
                }

            if action_lower == "flag":
                msg_id = args.get("msg_id", "")
                if not msg_id:
                    return {"ok": False, "action": action, "error": "msg_id is required"}
                body = {"addLabelIds": ["STARRED"]}
                resp = messages.modify(userId="me", id=msg_id, body=body).execute()
                return {
                    "ok": True,
                    "action": action,
                    "msg_id": msg_id,
                    "label_ids": resp.get("labelIds", []),
                    "flagged": True,
                }

            return {"ok": False, "error": f"unknown email action: {action}"}

        except FileNotFoundError as e:
            return {"ok": False, "action": action, "error": f"credentials not found: {e}"}
        except (json.JSONDecodeError, KeyError) as e:
            return {"ok": False, "action": action, "error": f"malformed credentials: {e}"}
        except Exception as e:
            return {"ok": False, "action": action, "error": f"{type(e).__name__}: {e}"}
