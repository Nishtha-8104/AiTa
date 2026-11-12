from app.core.topics import MISCONCEPTIONS
from app.features.chat.logic.rag.sources import load_local


def test_guides_cover_every_misconception_and_enough_errors_per_language():
    general = {s.section for s in load_local(["general.md"])}
    assert set(MISCONCEPTIONS) <= general

    for lang in ("c", "cpp", "python"):
        sections = load_local([f"{lang}.md"])
        assert len({s.section for s in sections}) >= 12
        assert any(b.kind == "code" for s in sections for b in s.blocks)
