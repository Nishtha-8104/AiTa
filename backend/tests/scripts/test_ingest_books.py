import pathlib
import types

import pytest
from sqlalchemy.engine import make_url

import app.core.database as database
from app.features.chat.logic.rag.sources import SourceSpec
from scripts.seed.ingest_books import run

FIXTURE = (pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "book_page.html").read_bytes()

SPECS = [
    SourceSpec(id=sid, title=sid, license="CC BY 4.0", url="https://example.test/",
               lang_tag="c", fetch="html", entry_urls=("https://example.test/loops.html",),
               html_selectors={"root": "main"})
    for sid in ("fixture-book", "other-book")
]


class FakeSink:
    def __init__(self):
        self.rows: dict[tuple[str, int], dict] = {}

    def write(self, source_id, rows):
        for row in rows:
            self.rows[(source_id, row["position"])] = row
        for key in [k for k in self.rows if k[0] == source_id and k[1] >= len(rows)]:
            del self.rows[key]


def fake_embed(texts):
    return [[0.1] * 384 for _ in texts]


def fetch(url):
    return FIXTURE


def test_dry_run_counts_without_touching_the_sink():
    sink = FakeSink()

    counts = run(["--dry-run"], sources=SPECS, fetch=fetch, embed_fn=None, sink=sink)

    assert counts == {"fixture-book": 4, "other-book": 4}
    assert sink.rows == {}


def test_rerun_is_idempotent_and_drops_stale_positions():
    sink = FakeSink()
    sink.rows[("fixture-book", 99)] = {"text": "stale"}

    run([], sources=SPECS, fetch=fetch, embed_fn=fake_embed, sink=sink)
    first = dict(sink.rows)
    run([], sources=SPECS, fetch=fetch, embed_fn=fake_embed, sink=sink)

    assert sink.rows == first
    assert sorted(k for k in sink.rows if k[0] == "fixture-book") == [
        ("fixture-book", i) for i in range(4)]
    texts = " ".join(r["text"] for r in sink.rows.values())
    assert "Skip to navigation" not in texts and "Copyright footer" not in texts
    assert "Loops › The while loop\n" in texts
    assert "while (i < 5) {" in texts
    for mixed in ("Nested parent item", "nested child item", "Cell text alpha",
                  "Loose div line one line two"):
        assert mixed in texts
    assert {r["url"] for r in sink.rows.values()} == {"https://example.test/loops.html"}


def test_refuses_a_remote_database_without_the_override(monkeypatch):
    monkeypatch.setattr(database, "engine", types.SimpleNamespace(
        url=make_url("postgresql://u:secret@ep-cool.neon.tech/pet")))

    with pytest.raises(SystemExit) as exc:
        run([], sources=SPECS, fetch=fetch, embed_fn=fake_embed)
    assert "--allow-remote" in str(exc.value) and "secret" not in str(exc.value)


def test_source_flag_filters():
    sink = FakeSink()

    counts = run(["--source", "other-book"], sources=SPECS, fetch=fetch,
                 embed_fn=fake_embed, sink=sink)

    assert list(counts) == ["other-book"]
    assert {k[0] for k in sink.rows} == {"other-book"}
