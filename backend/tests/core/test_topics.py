import json

import pytest

from app.core import content
from app.core.topics import (
    MISCONCEPTIONS,
    PREREQUISITES,
    TOPIC_LABELS,
    TOPICS,
    clean_misconceptions,
    normalise_topic,
)


def test_twelve_topics_each_with_label_and_prerequisites():
    assert len(TOPICS) == 12
    assert set(TOPIC_LABELS) == set(TOPICS)
    assert set(PREREQUISITES) == set(TOPICS)
    for prereqs in PREREQUISITES.values():
        assert set(prereqs) <= set(TOPICS)


def test_prerequisite_graph_has_no_cycles():
    seen: dict[str, int] = {}

    def depth(topic: str, path: tuple = ()) -> int:
        assert topic not in path, f"cycle through {topic}"
        if topic not in seen:
            seen[topic] = 1 + max((depth(p, path + (topic,)) for p in PREREQUISITES[topic]),
                                  default=0)
        return seen[topic]

    for topic in TOPICS:
        depth(topic)


@pytest.mark.parametrize("raw, expected", [
    ("arithmetic", "basics_io"),
    ("numbers", "basics_io"),
    ("sets", "hashing_sets"),
    ("hashing", "hashing_sets"),
    ("two pointers", "arrays"),
    ("stacks", "stacks_queues"),
    ("dynamic programming", "dynamic_programming"),
    ("Dynamic_Programming", "dynamic_programming"),
    ("  Loops ", "loops"),
    ("Hashing & Sets", "hashing_sets"),
    ("memoization", "dynamic_programming"),
])
def test_normalise_maps_bank_tags_and_synonyms(raw, expected):
    assert normalise_topic(raw) == expected


@pytest.mark.parametrize("raw", ["graph traversal", "bit manipulation", "", None])
def test_normalise_returns_none_for_off_list_topics(raw):
    assert normalise_topic(raw) is None


def test_every_bank_problem_topic_is_on_the_list():
    bank = json.loads((content.root() / "imported" / "problems.json").read_text("utf-8"))
    for problem in bank:
        assert problem["topic"] in TOPICS, problem["external_id"]


def test_clean_misconceptions_drops_unknown_and_duplicates():
    assert clean_misconceptions(
        ["off_by_one", "made_up", "off_by_one", "wrong_initial_value"]
    ) == ["off_by_one", "wrong_initial_value"]
    assert clean_misconceptions(None) == []
    assert len(MISCONCEPTIONS) == 12
