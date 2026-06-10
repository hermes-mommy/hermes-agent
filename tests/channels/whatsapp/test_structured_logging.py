from src.channels.whatsapp.structured_logging import _redact_body_processor, jid_hash


def test_jid_hash_is_deterministic() -> None:
    jid = "628123456789@s.whatsapp.net"
    assert jid_hash(jid) == jid_hash(jid)
    assert len(jid_hash(jid)) == 12


def test_redact_body_processor_removes_content_fields() -> None:
    event = {
        "body": "secret",
        "text": "secret",
        "content": "secret",
        "message": "secret",
        "raw_message": "secret",
        "keep": "ok",
    }
    redacted = _redact_body_processor(None, "info", event)
    assert "body" not in redacted
    assert "text" not in redacted
    assert "content" not in redacted
    assert "message" not in redacted
    assert "raw_message" not in redacted
    assert redacted["keep"] == "ok"
