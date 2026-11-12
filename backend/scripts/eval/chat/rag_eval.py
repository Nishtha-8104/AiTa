"""RAG quality of the pet chat on questions from the course books, scored with RAGAS.

    DATABASE_URL=postgresql://pet:pet@localhost:5433/pet_db \\
        python -m scripts.eval.chat.rag_eval [--out DIR] [--limit N] [--ids a,b]

Refuses to run against a non-local database. --ids reruns those ids even if done.

Each question is the first message of a new pet thread on the eval account. The passages
the model was shown are captured from search_books (clipped as the tool clips them).
RAGAS then scores faithfulness, answer relevancy, context precision and context recall:
the judge is the gateway's chat model under purpose "eval" (so every judge call lands in
llm_calls), wrapped in RAGAS's LangChain wrapper; embeddings are the local bge model.
RAGAS 0.4 only accepts a LangChain model through its legacy metrics and evaluate(), so
that is the path used. Answers that never searched the books are kept but not scored.

Needs scripts/eval/requirements-eval.txt, the local DB with the books ingested, and
spends free-tier LLM calls (about 10 judge calls per question): run it on purpose."""

import math
import os
import warnings
from unittest.mock import patch

from langchain_core.embeddings import Embeddings

from app.core.database import SessionLocal
from app.core.llm_gateway import gateway_chat_model
from app.features.chat.agent import tools as chat_tools
from app.features.chat.logic.rag import embedder
from scripts.eval.chat import harness
from scripts.eval.chat.results import Results, parser, pending
from scripts.eval.chat.scoring import RAG_METRICS, load_rag, rag_summary

EMAIL = "chat-eval-rag@example.com"


class LocalEmbeddings(Embeddings):
    # answer_relevancy compares the question with questions generated from the answer:
    # both sides are plain sentences, so neither gets the retrieval query prefix.
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embedder.embed(list(texts))

    def embed_query(self, text: str) -> list[float]:
        return embedder.embed([text])[0]


class RagasScorer:
    def __init__(self, user_id: int, max_workers: int):
        os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from ragas import EvaluationDataset, RunConfig, SingleTurnSample, evaluate
            from ragas.embeddings import LangchainEmbeddingsWrapper
            from ragas.llms import LangchainLLMWrapper
            from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

            self.run_config = RunConfig(timeout=300, max_retries=2, max_workers=max_workers)
            self.llm = LangchainLLMWrapper(gateway_chat_model("eval", user_id=user_id),
                                           run_config=self.run_config)
            self.embeddings = LangchainEmbeddingsWrapper(LocalEmbeddings())
            metrics = (Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall())
        self.metrics = dict(zip(RAG_METRICS, metrics))
        self._evaluate, self._dataset, self._sample = evaluate, EvaluationDataset, SingleTurnSample

    def score(self, question: str, answer: str, contexts: list[str],
              reference: str) -> dict[str, float | None]:
        sample = self._sample(user_input=question, response=answer,
                              retrieved_contexts=contexts, reference=reference)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = self._evaluate(self._dataset(samples=[sample]),
                                    metrics=list(self.metrics.values()), llm=self.llm,
                                    embeddings=self.embeddings, run_config=self.run_config,
                                    show_progress=False, raise_exceptions=False,
                                    allow_nest_asyncio=False)
        raw = result.scores[0]
        return {key: _number(raw.get(metric.name)) for key, metric in self.metrics.items()}


def _number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class SearchRecorder:
    def __init__(self, search):
        self._search = search
        self.hits = []

    def __call__(self, db, query, **kwargs):
        hits = self._search(db, query, **kwargs)
        self.hits.extend(hits)
        return hits


def main(argv=None) -> None:
    p = parser(__doc__.splitlines()[0], "rag", "rag_questions.jsonl")
    p.add_argument("--email", default=EMAIL, help="eval account (created if missing)")
    p.add_argument("--workers", type=int, default=4, help="parallel RAGAS judge calls")
    args = p.parse_args(argv)
    harness.require_local_db()

    rows = load_rag(args.data)
    results = Results(args.out)
    todo = pending(rows, results.done(), ids=args.ids, limit=args.limit)
    print(f"{len(todo)} of {len(rows)} questions to run -> {results.dir}")

    recorder = SearchRecorder(chat_tools.search)
    with SessionLocal() as db, patch.object(chat_tools, "search", recorder):
        user = harness.eval_user(db, args.email)
        scorer = RagasScorer(user.id, args.workers)
        for n, row in enumerate(todo, 1):
            recorder.hits.clear()
            thread = harness.new_thread(db, user.id, "pet")
            turn = harness.ask(db, user.id, thread, row["question"], row["language"])
            if turn.failed:
                print(f"[{n}/{len(todo)}] {row['id']}: turn failed ({turn.flag or turn.error}); "
                      "left for the next run")
                continue
            contexts = [harness.clip(h.text, chat_tools.PASSAGE_CHARS) for h in recorder.hits]
            searched = "search_books" in turn.tools
            scores = (scorer.score(row["question"], turn.content, contexts, row["reference_answer"])
                      if contexts else None)
            if scores is not None and None in scores.values():
                print(f"[{n}/{len(todo)}] {row['id']}: RAGAS left a metric unscored {scores}; "
                      "left for the next run")
                continue
            results.append({
                "id": row["id"], "language": row["language"], "source_id": row["source_id"],
                "question": row["question"], "answer": turn.content, "tools": turn.tools,
                "searched": searched,
                "retrieved_sources": [h.source_id for h in recorder.hits],
                "source_hit": any(h.source_id == row["source_id"] for h in recorder.hits),
                "contexts": contexts, "scores": scores,
            })
            print(f"[{n}/{len(todo)}] {row['id']}: tools={turn.tools} scores={scores}")

    results.finish(rag_summary(results.rows()))


if __name__ == "__main__":
    main()
