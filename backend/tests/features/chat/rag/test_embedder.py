import numpy as np
import pytest

from app.features.chat.logic.rag import embedder
from app.features.chat.models import BookChunk


class FakeModel:
    def __init__(self):
        self.seen: list[str] = []

    def encode(self, texts, batch_size, normalize_embeddings, show_progress_bar):
        assert batch_size == 32 and normalize_embeddings
        self.seen.extend(texts)
        rows = np.random.default_rng(0).random((len(texts), embedder.EMBED_DIM))
        return rows / np.linalg.norm(rows, axis=1, keepdims=True)


@pytest.fixture
def fake_model(monkeypatch):
    model, loads = FakeModel(), []
    monkeypatch.setattr(embedder, "_model", None)
    monkeypatch.setattr(embedder, "_load_model", lambda: loads.append(1) or model)
    return model, loads


def test_embed_unit_vectors_query_prefix_and_single_load(fake_model):
    model, loads = fake_model

    vectors = embedder.embed(["pointers", "arrays", "loops"])
    query = embedder.embed_query("what is a pointer")

    assert len(vectors) == 3
    for v in vectors + [query]:
        assert len(v) == 384
        assert np.linalg.norm(v) == pytest.approx(1.0)
    assert model.seen[-1] == embedder.QUERY_PREFIX + "what is a pointer"
    assert len(loads) == 1


def test_background_warm_up_loads_once_and_never_raises(fake_model, monkeypatch):
    model, loads = fake_model
    embedder.warm_up_in_background().join(10)
    assert loads == [1] and model.seen == [embedder.QUERY_PREFIX + "warmup"]

    monkeypatch.setattr(embedder, "_model", None)
    monkeypatch.setattr(embedder, "_load_model", lambda: 1 / 0)
    embedder.warm_up()


def test_book_chunk_round_trips_on_sqlite(session):
    session.add(BookChunk(
        source_id="kr", source_title="C Book", license="CC-BY", chapter="1", section="1.1",
        lang_tag="c", position=0, text="int main(void)", tokens=4, embedding=[0.5] * 384,
    ))
    session.commit()
    assert session.query(BookChunk).one().embedding == [0.5] * 384
