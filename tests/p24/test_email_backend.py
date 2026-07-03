"""P6 email backend TDD tests — real I/O with mocked Gmail API.

Each action must perform REAL Gmail API calls via googleapiclient.
Tests monkeypatch the Gmail service to avoid live API calls.
"""
from __future__ import annotations

import asyncio
import json
import base64
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from email.mime.text import MIMEText

from guinevere.tools.backends.email import EmailBackend


@pytest.fixture
def backend():
    return EmailBackend()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_gmail_service(mock_messages=None, mock_threads=None, mock_drafts=None):
    """Build a mock googleapiclient Gmail service object."""
    svc = MagicMock()
    if mock_messages:
        svc.messages.return_value = mock_messages
    if mock_threads:
        svc.threads.return_value = mock_threads
    if mock_drafts:
        svc.drafts.return_value = mock_drafts
    return svc


def _msg_resource(msg_id="abc123", subject="Test Subject", sender="alice@example.com",
                  to="me@example.com", body="Hello there", snippet="Hello...",
                  thread_id="thread_1", label_ids=None, is_unread=True):
    """Build a Gmail API message resource dict."""
    if label_ids is None:
        label_ids = ["INBOX"] + (["UNREAD"] if is_unread else [])
    raw = MIMEText(body)
    raw["to"] = to
    raw["from"] = sender
    raw["subject"] = subject
    raw_bytes = raw.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("ascii")
    return {
        "id": msg_id,
        "threadId": thread_id,
        "labelIds": label_ids,
        "snippet": snippet,
        "payload": {
            "headers": [
                {"name": "From", "value": sender},
                {"name": "To", "value": to},
                {"name": "Subject", "value": subject},
            ],
            "body": {"data": raw_b64},
            "mimeType": "text/plain",
        },
    }


# ---------------------------------------------------------------------------
# L1 READ actions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_inbox_returns_messages(backend, monkeypatch):
    """list_inbox returns real message list from Gmail API."""
    messages_mock = MagicMock()
    messages_mock.list.return_value.execute.return_value = {
        "messages": [
            {"id": "msg1", "threadId": "t1"},
            {"id": "msg2", "threadId": "t2"},
        ],
        "resultSizeEstimate": 2,
    }
    messages_mock.get.return_value.execute.return_value = _msg_resource("msg1", subject="Hello")

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("list_inbox", {"max_results": 10})

    assert result["ok"] is True
    assert result["action"] == "list_inbox"
    assert result["count"] == 2
    assert len(result["messages"]) == 2
    messages_mock.list.assert_called_once()


@pytest.mark.asyncio
async def test_search_returns_matching_messages(backend, monkeypatch):
    """search queries Gmail and returns matching messages."""
    messages_mock = MagicMock()
    messages_mock.list.return_value.execute.return_value = {
        "messages": [{"id": "s1", "threadId": "st1"}],
        "resultSizeEstimate": 1,
    }
    messages_mock.get.return_value.execute.return_value = _msg_resource("s1", subject="Invoice #42")

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("search", {"query": "subject:Invoice", "max_results": 5})

    assert result["ok"] is True
    assert result["action"] == "search"
    assert result["count"] == 1
    assert result["results"][0]["id"] == "s1"


@pytest.mark.asyncio
async def test_read_returns_message_body(backend, monkeypatch):
    """read retrieves a single message by id with decoded body."""
    messages_mock = MagicMock()
    messages_mock.get.return_value.execute.return_value = _msg_resource(
        "m99", subject="RE: Meeting", body="Let's meet at 3pm"
    )

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("read", {"msg_id": "m99"})

    assert result["ok"] is True
    assert result["action"] == "read"
    assert result["msg_id"] == "m99"
    assert "subject" in result
    assert "body" in result
    assert result["subject"] == "RE: Meeting"


@pytest.mark.asyncio
async def test_get_thread_returns_thread_messages(backend, monkeypatch):
    """get_thread retrieves all messages in a thread."""
    threads_mock = MagicMock()
    threads_mock.get.return_value.execute.return_value = {
        "id": "thread_abc",
        "messages": [
            _msg_resource("m1", body="First message"),
            _msg_resource("m2", body="Second message"),
        ],
    }

    svc = _make_gmail_service(mock_threads=threads_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("get_thread", {"thread_id": "thread_abc"})

    assert result["ok"] is True
    assert result["action"] == "get_thread"
    assert result["thread_id"] == "thread_abc"
    assert result["message_count"] == 2


# ---------------------------------------------------------------------------
# L2 WRITE actions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_email_sends_message(backend, monkeypatch):
    """send creates and sends a Gmail message."""
    messages_mock = MagicMock()
    messages_mock.send.return_value.execute.return_value = {
        "id": "sent_001",
        "threadId": "new_thread_001",
        "labelIds": ["SENT"],
    }

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("send", {
        "to": "bob@example.com",
        "subject": "Project Update",
        "body": "Everything is on track.",
    })

    assert result["ok"] is True
    assert result["action"] == "send"
    assert result["msg_id"] == "sent_001"
    messages_mock.send.assert_called_once()


@pytest.mark.asyncio
async def test_reply_sends_reply_in_thread(backend, monkeypatch):
    """reply sends a reply within an existing thread."""
    # First: get the original message to find threadId
    messages_mock = MagicMock()
    messages_mock.get.return_value.execute.return_value = _msg_resource(
        "orig_1", subject="Hello", sender="alice@example.com", thread_id="thr_1"
    )
    messages_mock.send.return_value.execute.return_value = {
        "id": "reply_001",
        "threadId": "thr_1",
    }

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("reply", {
        "msg_id": "orig_1",
        "body": "Thanks for the update!",
    })

    assert result["ok"] is True
    assert result["action"] == "reply"
    assert result["msg_id"] == "reply_001"


@pytest.mark.asyncio
async def test_forward_forwards_message(backend, monkeypatch):
    """forward retrieves and forwards a message to a new recipient."""
    messages_mock = MagicMock()
    messages_mock.get.return_value.execute.return_value = _msg_resource(
        "fwd_1", subject="FYI", body="Original content"
    )
    messages_mock.send.return_value.execute.return_value = {
        "id": "fwd_sent_001",
        "threadId": "fwd_thread_001",
    }

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("forward", {
        "msg_id": "fwd_1",
        "to": "charlie@example.com",
    })

    assert result["ok"] is True
    assert result["action"] == "forward"
    assert result["msg_id"] == "fwd_sent_001"


@pytest.mark.asyncio
async def test_create_draft_creates_draft(backend, monkeypatch):
    """create_draft creates a Gmail draft."""
    drafts_mock = MagicMock()
    drafts_mock.create.return_value.execute.return_value = {
        "id": "draft_001",
        "message": {"id": "draft_msg_001", "threadId": "draft_thread_001"},
    }

    svc = _make_gmail_service(mock_drafts=drafts_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("create_draft", {
        "to": "dave@example.com",
        "subject": "Draft idea",
        "body": "Here is a thought...",
    })

    assert result["ok"] is True
    assert result["action"] == "create_draft"
    assert result["draft_id"] == "draft_001"


@pytest.mark.asyncio
async def test_modify_labels_changes_labels(backend, monkeypatch):
    """modify_labels adds and removes labels on a message."""
    messages_mock = MagicMock()
    messages_mock.modify.return_value.execute.return_value = {
        "id": "lbl_1",
        "labelIds": ["INBOX", "STARRED"],
    }

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("modify_labels", {
        "msg_id": "lbl_1",
        "add_labels": ["STARRED"],
        "remove_labels": ["UNREAD"],
    })

    assert result["ok"] is True
    assert result["action"] == "modify_labels"
    assert result["msg_id"] == "lbl_1"


@pytest.mark.asyncio
async def test_mark_read_removes_unread_label(backend, monkeypatch):
    """mark_read removes the UNREAD label."""
    messages_mock = MagicMock()
    messages_mock.modify.return_value.execute.return_value = {
        "id": "mr_1",
        "labelIds": ["INBOX"],
    }

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("mark_read", {"msg_id": "mr_1"})

    assert result["ok"] is True
    assert result["action"] == "mark_read"
    assert result["msg_id"] == "mr_1"
    assert result["marked"] is True


@pytest.mark.asyncio
async def test_flag_adds_starred_label(backend, monkeypatch):
    """flag adds the STARRED label."""
    messages_mock = MagicMock()
    messages_mock.modify.return_value.execute.return_value = {
        "id": "fl_1",
        "labelIds": ["INBOX", "STARRED"],
    }

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("flag", {"msg_id": "fl_1"})

    assert result["ok"] is True
    assert result["action"] == "flag"
    assert result["msg_id"] == "fl_1"
    assert result["flagged"] is True


# ---------------------------------------------------------------------------
# Error handling / fail-soft
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_never_raises_on_error(backend, monkeypatch):
    """dispatch() catches all exceptions and returns {ok: False, error: ...}."""
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service",
                        lambda: (_ for _ in ()).throw(ConnectionError("Gmail down")))

    result = await backend.dispatch("list_inbox", {})

    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_action_returns_error(backend):
    """An unknown action returns ok=False with error message."""
    result = await backend.dispatch("nonexistent_action", {})
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_api_error_returns_fail_soft(backend, monkeypatch):
    """Gmail API error is caught and returned as ok=False."""
    messages_mock = MagicMock()
    messages_mock.list.return_value.execute.side_effect = Exception("403 Forbidden")

    svc = _make_gmail_service(mock_messages=messages_mock)
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: svc)

    result = await backend.dispatch("list_inbox", {})

    assert result["ok"] is False
    assert "403" in result["error"]


@pytest.mark.asyncio
async def test_is_available_with_credentials(tmp_path, monkeypatch):
    """is_available returns True when credentials file exists."""
    import guinevere.tools.backends.email as email_mod

    creds_file = tmp_path / "token.json"
    creds_file.write_text("{}")
    monkeypatch.setattr(email_mod, "_CREDENTIALS_PATH", str(creds_file))

    backend = EmailBackend()
    assert backend.is_available() is True


@pytest.mark.asyncio
async def test_is_available_without_credentials(monkeypatch):
    """is_available returns False when credentials file missing."""
    import guinevere.tools.backends.email as email_mod
    monkeypatch.setattr(email_mod, "_CREDENTIALS_PATH", "/nonexistent/path.json")

    backend = EmailBackend()
    assert backend.is_available() is False


@pytest.mark.asyncio
async def test_read_requires_msg_id(backend, monkeypatch):
    """read with missing msg_id returns ok=False."""
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: MagicMock())

    result = await backend.dispatch("read", {})
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_send_requires_to(backend, monkeypatch):
    """send with missing 'to' returns ok=False."""
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: MagicMock())

    result = await backend.dispatch("send", {"subject": "x", "body": "y"})
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_reply_requires_msg_id(backend, monkeypatch):
    """reply with missing msg_id returns ok=False."""
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: MagicMock())

    result = await backend.dispatch("reply", {"body": "yo"})
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_forward_requires_to(backend, monkeypatch):
    """forward with missing 'to' returns ok=False."""
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: MagicMock())

    result = await backend.dispatch("forward", {"msg_id": "x"})
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_create_draft_requires_to(backend, monkeypatch):
    """create_draft with missing 'to' returns ok=False."""
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: MagicMock())

    result = await backend.dispatch("create_draft", {"subject": "x", "body": "y"})
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_create_draft_requires_subject(backend, monkeypatch):
    """create_draft with missing 'subject' returns ok=False."""
    monkeypatch.setattr("guinevere.tools.backends.email._build_gmail_service", lambda: MagicMock())

    result = await backend.dispatch("create_draft", {"to": "x@y.com", "body": "y"})
    assert result["ok"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# Actions catalogue
# ---------------------------------------------------------------------------

def test_actions_catalogue_has_all_actions(backend):
    """The backend declares all 10 expected actions."""
    names = {a.name for a in backend.actions()}
    expected = {
        "list_inbox", "search", "read", "send", "reply",
        "forward", "create_draft", "modify_labels", "mark_read", "flag",
    }
    assert expected == names


def test_name_is_email(backend):
    """Backend name is 'email'."""
    assert backend.name == "email"
