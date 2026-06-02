# Guinevere smoke tests — basic persona (identity + empathy)
"""Verify Guinevere responds in-character with correct identity and emotional tone."""

import pytest


INDONESIAN_STOPWORDS = {"yang", "dan", "di", "ke", "dari", "ini", "itu", "aku", "kamu", "tidak", "ada", "bisa", "akan", "saya"}


def _is_indonesian(text: str) -> bool:
    words = set(text.lower().split())
    return bool(words & INDONESIAN_STOPWORDS)


@pytest.mark.asyncio
async def test_identity(chat):
    """T01: Halo, siapa kamu? → response contains 'Guinevere', is Indonesian."""
    content = await chat("Halo, siapa kamu?")
    assert len(content) > 10, "Identity response too short: %r" % content
    assert "Guinevere" in content, "Missing identity name: %r" % content[:100]
    assert _is_indonesian(content), "Response not Indonesian: %r" % content[:100]


@pytest.mark.asyncio
async def test_empathy(chat):
    """T02: Aku capek hari ini → caring/empathetic tone, Indonesian, not dismissive."""
    content = await chat("Aku capek hari ini.")
    assert len(content) > 20, "Empathy response too short: %r" % content
    assert _is_indonesian(content), "Response not Indonesian: %r" % content[:100]
    lower = content.lower()
    cold = ["gak peduli", "bukan urusanku", "terserah", "itu masalahmu",
            "not my problem", "i don't care", "whatever"]
    for phrase in cold:
        assert phrase not in lower, "Dismissive phrase found: %r in %r" % (phrase, content[:150])


@pytest.mark.asyncio
async def test_creator_context(chat):
    """T03: Siapa yang buat kamu? → references Faiz/creator, Guinevere voice."""
    content = await chat("Siapa yang buat kamu?")
    assert len(content) > 15, "Creator response too short: %r" % content
    assert _is_indonesian(content), "Response not Indonesian: %r" % content[:100]
    lower = content.lower()
    creator_terms = ["faiz", "darling", "operator", "yang buat", "yang bikin", "guinevere", "mama", "nous", "hermes", "dibuat oleh"]
    found = any(term in lower for term in creator_terms)
    assert found, "No creator context in response: %r" % content[:200]