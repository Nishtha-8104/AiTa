"""Vector search over the embedded book chunks for the chatbot's search_books tool."""

import math
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.features.chat.logic.rag import embedder
from app.features.chat.models import BookChunk

LANGUAGES = {"c", "cpp", "python"}
ALIASES = {"c++": "cpp"}
CANDIDATE_FACTOR = 3


@dataclass(frozen=True)
class Hit:
    text: str
    source_id: str
    source_title: str
    chapter: str
    section: str
    url: str | None
    license: str
    score: float


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return 1.0 - dot / norm if norm else 1.0


def _candidates(db: Session, vec: list[float], language: str | None, limit: int):
    query = db.query(BookChunk).filter(BookChunk.embedding.isnot(None))
    if language:
        query = query.filter(BookChunk.lang_tag.in_([language, "general"]))

    if db.get_bind().dialect.name == "postgresql":
        # Without iterative scan, HNSW returns ef_search rows before the lang_tag filter.
        db.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
        db.execute(text("SET LOCAL hnsw.ef_search = 100"))
        distance = BookChunk.embedding.cosine_distance(vec)
        rows = query.add_columns(distance).order_by(distance).limit(limit).all()
        return sorted(rows, key=lambda pair: pair[1])

    scored = [(row, _cosine_distance(row.embedding, vec)) for row in query.all() if row.embedding]
    scored.sort(key=lambda pair: pair[1])
    return scored[:limit]


def search(db: Session, query: str, *, language: str | None = None, k: int = 5,
           embed=None) -> list[Hit]:
    if not query or not query.strip() or k <= 0:
        return []
    language = (language or "").strip().lower()
    language = ALIASES.get(language, language)
    if language not in LANGUAGES:
        language = None
    vec = (embed or embedder.embed_query)(query.strip())

    hits: list[Hit] = []
    kept: list[tuple[str, int]] = []
    for row, distance in _candidates(db, vec, language, k * CANDIDATE_FACTOR):
        if any(sid == row.source_id and abs(pos - row.position) <= 1 for sid, pos in kept):
            continue
        kept.append((row.source_id, row.position))
        hits.append(Hit(
            text=row.text, source_id=row.source_id, source_title=row.source_title,
            chapter=row.chapter, section=row.section, url=row.url, license=row.license,
            score=1.0 - float(distance),
        ))
        if len(hits) == k:
            break
    return hits
