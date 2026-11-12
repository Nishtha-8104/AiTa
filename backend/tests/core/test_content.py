import json
from collections import Counter

from app.core import content
from app.core.topics import TOPIC_LABELS, TOPICS
from app.features.onboarding.logic import content as diagnostic


def test_every_topic_has_every_file_valid_and_the_schemas_are_current():
    for topic in TOPICS:
        meta = content.read(topic, "topic")
        assert (meta["title"], meta["order"]) == (TOPIC_LABELS[topic], TOPICS.index(topic) + 1)
        for kind in content.KINDS[1:]:
            content.read(topic, kind)
    for kind in content.KINDS:
        path = content.root() / "schemas" / f"{kind}.schema.json"
        assert json.loads(path.read_text("utf-8")) == content.json_schema(kind), kind


def test_item_ids_are_unique_and_diagnostic_ids_follow_concept_and_language():
    ids = Counter(item["id"] for topic in TOPICS for kind in content.KINDS[1:]
                  for item in content.items(topic, kind))
    assert [i for i, n in ids.items() if n > 1] == []
    for topic in TOPICS:
        for item in content.items(topic, "diagnostic"):
            assert item["id"] == diagnostic.item_id(item)


def test_diagnostic_bank_survives_a_write_and_read(monkeypatch, tmp_path):
    shipped = diagnostic.load()
    monkeypatch.setattr("app.core.config.settings.CONTENT_DIR", tmp_path)
    diagnostic.save(shipped)
    assert diagnostic.load() == shipped
