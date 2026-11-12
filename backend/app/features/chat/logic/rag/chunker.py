"""Heading-aware chunking of parsed book sections for the book_chunks table."""

import math
from dataclasses import dataclass, field
from typing import Literal

TOKENS_PER_WORD = 1.3


@dataclass
class Block:
    kind: Literal["text", "code"]
    text: str


@dataclass
class Section:
    chapter: str
    section: str
    blocks: list[Block] = field(default_factory=list)
    url: str = ""


@dataclass
class Chunk:
    chapter: str
    section: str
    text: str
    tokens: int
    position: int
    url: str = ""


def count_tokens(text: str) -> int:
    """Whitespace words x 1.3: close enough to bge's WordPiece for sizing, without loading it."""
    return math.ceil(len(text.split()) * TOKENS_PER_WORD)


def prefix(chapter: str, section: str) -> str:
    return f"{chapter} › {section}\n"


def _section_bodies(blocks: list[Block], target_words: int, overlap_words: int) -> list[str]:
    bodies: list[str] = []
    parts: list[str] = []
    used = 0
    has_content = False
    text_tail: list[str] = []

    def flush() -> None:
        nonlocal parts, used, has_content
        if has_content:
            bodies.append("\n\n".join(parts))
        carry = text_tail[-overlap_words:] if overlap_words else []
        parts = [" ".join(carry)] if carry else []
        used = len(carry)
        has_content = False

    for block in blocks:
        if block.kind == "code":
            code = block.text.strip("\n")
            words = len(code.split())
            if not words:
                continue
            if used + words > target_words and has_content:
                flush()
            if used + words > target_words:
                parts, used = [], 0
            if words > target_words:
                bodies.append(code)
                continue
            parts.append(code)
            used += words
            has_content = True
            continue

        words = block.text.split()
        while words:
            room = target_words - used
            if room <= 0:
                flush()
                continue
            taken, words = words[:room], words[room:]
            parts.append(" ".join(taken))
            used += len(taken)
            has_content = True
            text_tail.extend(taken)
            del text_tail[:-overlap_words or None]

    if has_content:
        bodies.append("\n\n".join(parts))
    return bodies


def chunk(sections: list[Section], *, target_tokens: int = 400,
          overlap_tokens: int = 60) -> list[Chunk]:
    target_words = max(1, int(target_tokens / TOKENS_PER_WORD))
    overlap_words = min(round(overlap_tokens / TOKENS_PER_WORD), target_words // 2)
    chunks: list[Chunk] = []
    for sec in sections:
        head = prefix(sec.chapter, sec.section)
        for body in _section_bodies(sec.blocks, target_words, overlap_words):
            text = head + body
            chunks.append(Chunk(sec.chapter, sec.section, text, count_tokens(text), len(chunks),
                                sec.url))
    return chunks
