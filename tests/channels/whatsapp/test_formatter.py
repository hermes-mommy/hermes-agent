from src.channels.whatsapp.formatter import WhatsAppFormatter


def test_formatter_converts_markdown_and_chunks() -> None:
    formatter = WhatsAppFormatter()
    raw = "# Header\n\n**bold** and *italic* and ~~gone~~\n\n- one\n- two\n\n[site](https://example.com)"
    chunks = formatter.format(raw)
    assert len(chunks) == 1
    assert "*Header*" in chunks[0]
    assert "*bold*" in chunks[0]
    assert "_italic_" in chunks[0]
    assert "~gone~" in chunks[0]
    assert "• one" in chunks[0]
    assert "site (https://example.com)" in chunks[0]


def test_formatter_preserves_code_blocks() -> None:
    formatter = WhatsAppFormatter()
    raw = "```python\nprint('x')\n```"
    chunks = formatter.format(raw)
    assert chunks == [raw]


def test_formatter_adds_sequence_prefixes_when_chunked() -> None:
    formatter = WhatsAppFormatter()
    long_text = ("paragraph " * 200).strip()
    chunks = formatter.format(long_text)
    assert len(chunks) > 1
    assert chunks[0].startswith("(1/")
