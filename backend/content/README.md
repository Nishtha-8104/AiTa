# content

Everything students see that is written rather than computed: question banks, lessons,
the chatbot's guides. The backend reads it from here (`CONTENT_DIR`, default
`backend/content`); the seed scripts load it into the database.

## Layout

```
topics/<topic>/          the same 7 files in all 12 topic folders
  topic.json             title and order
  explanation.json       the topic lesson in C, C++ and Python
  problems.json          coding problems: statement, Python reference, tests
  mcq.json               multiple-choice questions ("any" = concept question, no code)
  debug.json             find-the-bug challenges on a problem from problems.json
  theory.json            written questions with a model answer and key points
  diagnostic.json        onboarding diagnostic items
schemas/                 JSON Schema for each of the 7 files
guides/                  c.md, cpp.md, python.md, general.md (chatbot book search)
imported/problems.json   DSA and MBPP problems, original format
moderation/terms.txt     chat moderation term list
eval/chat/*.jsonl        chatbot evaluation sets
legacy/assessments.json  the first generated bank (seed_assessments), kept for reference
_drafts/                 raw LLM replies cached by the generators, never served
```

## File format

Every topic file is

```json
{"schema": "<kind>/v1", "topic": "<topic>", "items": [ ... ]}
```

(`topic.json` has `title` and `order` instead of `items`.) The topic comes from the
folder and must match. Every item has an explicit `id`; ids are unique across all files
and never derived from position, so items can be reordered freely.

Code and other multi-line text is a list of lines: `["int main(void) {", "    return 0;",
"}", ""]`. A trailing `""` means the text ends with a newline. The loaders join the lines
with `\n` and get back exactly the text that is stored in the database.

| File | Item fields |
|---|---|
| explanation | `id, language, title, markdown[]` (the lesson is `# title` followed by the lines) |
| problems | `id, title, difficulty, statement, constraints, reference{language, code[]}, tests[{input[], output[]}]` (first test is the shown sample; `title` is a short Title Case name, never "Topic #n") |
| mcq | `id, language, difficulty, stem[], options[{text, misconception}], answer_index, explanation, verify_code[]` |
| debug | `id, language, problem_id, bug_type, fixed_code[], buggy_code[]` |
| theory | `id, language, difficulty, question, model_answer, key_points[]` |
| diagnostic | `id, concept_key, tier, kind, language, difficulty, body{}, key{}`; `id` is `concept_key:language`; code, outputs and test streams in `body`/`key` are line lists |

The schemas are generated from the models in `app/core/content.py`;
`tests/core/test_content.py` fails if a file is invalid, a topic is missing a file, an id
repeats, or a schema file is out of date.

## Counts

| | C | C++ | Python | any | Total |
|---|---|---|---|---|---|
| explanations | 12 | 12 | 12 | | 36 |
| problems (Python reference) | | | | | 86 |
| mcq | 72 | 72 | 72 | 36 | 252 |
| debug | 72 | 72 | 72 | | 216 |
| theory | 72 | 72 | 72 | | 216 |
| diagnostic | 39 | 40 | 41 | | 120 |

Plus 25 imported problems (13 DSA, 12 MBPP) and 251 chatbot evaluation rows.

## Loading

```bash
docker compose exec backend python -m scripts.seed.ingest_problems   # imported/
docker compose exec backend python -m scripts.seed.seed_practice     # problems, mcq, debug
docker compose exec backend python -m scripts.seed.seed_theory       # theory
docker compose exec backend python -m scripts.seed.seed_diagnostic   # diagnostic
docker compose exec backend python -m scripts.seed.ingest_books      # guides/ + books
```

Explanations, guides and moderation terms are read at runtime. `scripts.generate.generate_diagnostic`
writes `diagnostic.json` files in this format.
