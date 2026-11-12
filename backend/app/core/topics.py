"""The fixed learner-model vocabulary: 12 topics, their prerequisites, and the
misconception tags. Mastery is only ever tracked against these ids."""

import re

TOPICS: tuple[str, ...] = (
    "basics_io",
    "conditionals",
    "loops",
    "functions",
    "arrays",
    "strings",
    "hashing_sets",
    "recursion",
    "sorting",
    "searching",
    "stacks_queues",
    "dynamic_programming",
)

TOPIC_LABELS: dict[str, str] = {
    "basics_io": "Basics & I/O",
    "conditionals": "Conditionals",
    "loops": "Loops",
    "functions": "Functions",
    "arrays": "Arrays",
    "strings": "Strings",
    "hashing_sets": "Hashing & Sets",
    "recursion": "Recursion",
    "sorting": "Sorting",
    "searching": "Searching",
    "stacks_queues": "Stacks & Queues",
    "dynamic_programming": "Dynamic Programming",
}

PREREQUISITES: dict[str, tuple[str, ...]] = {
    "basics_io": (),
    "conditionals": ("basics_io",),
    "loops": ("conditionals",),
    "functions": ("basics_io",),
    "arrays": ("loops",),
    "strings": ("loops",),
    "hashing_sets": ("arrays",),
    "recursion": ("functions",),
    "sorting": ("arrays",),
    "searching": ("arrays",),
    "stacks_queues": ("arrays",),
    "dynamic_programming": ("recursion", "arrays"),
}

MISCONCEPTIONS: tuple[str, ...] = (
    "off_by_one",
    "empty_input_unhandled",
    "wrong_initial_value",
    "wrong_comparison_operator",
    "integer_division",
    "missing_base_case",
    "mutate_while_iterating",
    "uninitialised_variable",
    "wrong_loop_bound",
    "return_vs_print",
    "index_out_of_range",
    "infinite_loop",
)

_SYNONYMS: dict[str, str] = {
    "arithmetic": "basics_io",
    "numbers": "basics_io",
    "math": "basics_io",
    "maths": "basics_io",
    "mathematics": "basics_io",
    "basics": "basics_io",
    "input output": "basics_io",
    "io": "basics_io",
    "variables": "basics_io",
    "if else": "conditionals",
    "branching": "conditionals",
    "iteration": "loops",
    "for loop": "loops",
    "while loop": "loops",
    "function": "functions",
    "methods": "functions",
    "array": "arrays",
    "list": "arrays",
    "lists": "arrays",
    "two pointers": "arrays",
    "two pointer": "arrays",
    "sliding window": "arrays",
    "prefix sum": "arrays",
    "matrix": "arrays",
    "string": "strings",
    "text processing": "strings",
    "hashing": "hashing_sets",
    "sets": "hashing_sets",
    "set": "hashing_sets",
    "hash map": "hashing_sets",
    "hashmap": "hashing_sets",
    "hash table": "hashing_sets",
    "dictionary": "hashing_sets",
    "dictionaries": "hashing_sets",
    "recursive": "recursion",
    "backtracking": "recursion",
    "sort": "sorting",
    "search": "searching",
    "binary search": "searching",
    "linear search": "searching",
    "stack": "stacks_queues",
    "stacks": "stacks_queues",
    "queue": "stacks_queues",
    "queues": "stacks_queues",
    "deque": "stacks_queues",
    "dp": "dynamic_programming",
    "memoization": "dynamic_programming",
    "memoisation": "dynamic_programming",
    "tabulation": "dynamic_programming",
}


def _key(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-/&]+", " ", raw.strip().lower())).strip()


_LOOKUP: dict[str, str] = {_key(t): t for t in TOPICS}
_LOOKUP.update({_key(label): t for t, label in TOPIC_LABELS.items()})
_LOOKUP.update({_key(k): v for k, v in _SYNONYMS.items()})


def normalise_topic(raw: str | None) -> str | None:
    """One of TOPICS, or None when the text names nothing on the list."""
    if not raw:
        return None
    return _LOOKUP.get(_key(raw))


def clean_misconceptions(tags) -> list[str]:
    """Known tags only, deduplicated, in the order given."""
    known = set(MISCONCEPTIONS)
    return list(dict.fromkeys(t for t in (tags or []) if t in known))
