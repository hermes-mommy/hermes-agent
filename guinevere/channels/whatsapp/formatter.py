from __future__ import annotations

"""P11-012 — WhatsApp formatting + chunking."""

import re
from dataclasses import dataclass

_CODE_BLOCK_RE = re.compile(r"```(.*?)```", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_LINK_MD_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)")
_STRIKE_RE = re.compile(r"~~(.+?)~~")
_LIST_RE = re.compile(r"^(\s*)[-*]\s+", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|.*\|$", re.MULTILINE)
_SEQUENCE_PREFIX_TEMPLATE = "({index}/{total}) "


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    target_size: int = 1000
    hard_floor: int = 100
    max_chunks: int = 10
    overflow_suffix: str = "\n\n[truncated]"


class WhatsAppFormatter:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()

    def format(self, raw_response: str) -> list[str]:
        cleaned = raw_response.strip()
        if not cleaned:
            return [""]

        protected, code_blocks = self._protect_code_blocks(cleaned)
        converted = self._convert_markdown_to_whatsapp(protected)
        restored = self._restore_code_blocks(converted, code_blocks)
        chunks = self._auto_chunk(restored)
        return self._add_sequence_prefixes(chunks)

    def _convert_markdown_to_whatsapp(self, value: str) -> str:
        text = value
        text = _IMAGE_MD_RE.sub("", text)
        text = _LINK_MD_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})", text)
        text = _HEADER_RE.sub(lambda m: f"§§HEADER§§{m.group(1).strip()}§§ENDHEADER§§", text)
        text = _BOLD_RE.sub(lambda m: f"§§BOLD§§{m.group(1)}§§ENDBOLD§§", text)
        text = _ITALIC_RE.sub(lambda m: f"_{m.group(1)}_", text)
        text = _STRIKE_RE.sub(lambda m: f"~{m.group(1)}~", text)
        text = _LIST_RE.sub(lambda m: f"{m.group(1)}• ", text)
        text = _TABLE_ROW_RE.sub("", text)
        text = _HTML_TAG_RE.sub("", text)
        text = text.replace("§§HEADER§§", "*").replace("§§ENDHEADER§§", "*")
        text = text.replace("§§BOLD§§", "*").replace("§§ENDBOLD§§", "*")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _protect_code_blocks(self, value: str) -> tuple[str, list[str]]:
        code_blocks: list[str] = []

        def repl(match: re.Match[str]) -> str:
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        return _CODE_BLOCK_RE.sub(repl, value), code_blocks

    def _restore_code_blocks(self, value: str, code_blocks: list[str]) -> str:
        restored = value
        for idx, block in enumerate(code_blocks):
            restored = restored.replace(f"__CODE_BLOCK_{idx}__", block)
        return restored

    def _auto_chunk(self, value: str) -> list[str]:
        if len(value) <= self._config.target_size:
            return [value]

        chunks: list[str] = []
        remaining = value
        while remaining and len(chunks) < self._config.max_chunks:
            if len(remaining) <= self._config.target_size:
                chunks.append(remaining.strip())
                break
            split_at = self._find_split_point(remaining)
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].lstrip()

        if remaining:
            if chunks:
                chunks[-1] = self._truncate_with_suffix(chunks[-1], remaining)
            else:
                chunks.append(self._truncate_with_suffix("", remaining))

        return [chunk for chunk in chunks if chunk]

    def _find_split_point(self, text: str) -> int:
        target = self._config.target_size
        candidates = [
            text.rfind("\n\n", self._config.hard_floor, target),
            text.rfind("\n", self._config.hard_floor, target),
            text.rfind(". ", self._config.hard_floor, target),
            text.rfind(" ", self._config.hard_floor, target),
        ]
        split_at = max(candidates)
        if split_at <= 0:
            return target
        if text[split_at:split_at + 2] == ". ":
            return split_at + 1
        return split_at

    def _truncate_with_suffix(self, current: str, remaining: str) -> str:
        suffix = self._config.overflow_suffix
        base = current or remaining[: self._config.target_size]
        max_len = max(0, self._config.target_size - len(suffix))
        return base[:max_len].rstrip() + suffix

    def _add_sequence_prefixes(self, chunks: list[str]) -> list[str]:
        if len(chunks) <= 1:
            return chunks
        total = len(chunks)
        return [
            _SEQUENCE_PREFIX_TEMPLATE.format(index=index, total=total) + chunk
            for index, chunk in enumerate(chunks, start=1)
        ]
