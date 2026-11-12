from app.features.chat.logic.rag.search import search
from app.features.chat.models import EMBED_DIM, BookChunk


def _vec(*head: float) -> list[float]:
    return list(head) + [0.0] * (EMBED_DIM - len(head))


def _add(db, source_id, position, lang, vec):
    db.add(BookChunk(
        source_id=source_id, source_title=source_id.title(), license="CC BY 4.0",
        url=f"https://x/{source_id}", chapter="Ch", section="Sec", lang_tag=lang,
        position=position, text=f"{source_id}-{position}", embedding=vec,
    ))


def _fake_embed(calls):
    def embed(text):
        calls.append(text)
        return _vec(1.0, 0.0)
    return embed


def test_orders_by_similarity_and_filters_language(session):
    _add(session, "beej", 0, "c", _vec(1.0, 0.1))
    _add(session, "modernc", 0, "c", _vec(1.0, 0.5))
    _add(session, "guide", 0, "general", _vec(1.0, 1.0))
    _add(session, "py4e", 0, "python", _vec(1.0, 0.0))
    session.commit()

    hits = search(session, "what is a pointer", language="c", embed=_fake_embed([]))
    assert [h.source_id for h in hits] == ["beej", "modernc", "guide"]
    assert hits[0].score > hits[1].score > hits[2].score
    assert hits[0].url == "https://x/beej" and hits[0].license == "CC BY 4.0"

    top2 = search(session, "pointer", language="nonsense", k=2, embed=_fake_embed([]))
    assert [h.source_id for h in top2] == ["py4e", "beej"]


def test_adjacent_overlap_chunks_collapse_to_best(session):
    _add(session, "beej", 4, "c", _vec(1.0, 0.0))
    _add(session, "beej", 5, "c", _vec(1.0, 0.05))
    _add(session, "beej", 9, "c", _vec(1.0, 0.2))
    _add(session, "modernc", 5, "c", _vec(1.0, 0.1))
    session.commit()

    hits = search(session, "pointer", language="c", embed=_fake_embed([]))
    assert [h.text for h in hits] == ["beej-4", "modernc-5", "beej-9"]


def test_empty_query_or_table_returns_nothing(session):
    calls: list[str] = []
    assert search(session, "   ", language="c", embed=_fake_embed(calls)) == []
    assert calls == []
    assert search(session, "pointer", embed=_fake_embed(calls)) == []
