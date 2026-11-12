# chat

The chat tutor. A LangChain agent with four tools: search the course books (RAG over
pgvector), query the student's learning data, evaluate code through `grading`, and get a
hint through `hints`. Messages pass a local moderation check first; it nudges rather than
blocks. A turn runs on its own worker and streams back as Server-Sent Events, so the reply
is saved even if the tab closes.

## Endpoints

`router.py`, under `/api/v1/chat`: `POST /threads`, `GET /threads`, `GET /threads/{id}`,
`POST /threads/{id}/messages` (SSE), `PATCH /messages/{id}/thumbs`.

## Tables

- Writes: `chat_threads`, `chat_messages`; `book_chunks` is filled by
  `scripts/seed/ingest_books.py`
- Through tools: `code_submissions`, `code_evaluations`, `hint_events`, `learning_events`
- Reads: `book_chunks`, `problems`, every learning table (via `learner_model` learning data)

## Files

```
router.py
service.py           run_turn(): one chat turn, streamed events, saved messages
agent/agent.py       the agent; middleware.py, prompts.py, context.py around it
agent/tools.py       the four tools
logic/moderation.py  term-list moderation (content/moderation/terms.txt)
logic/rag/           sources, chunker, embedder, search
models.py            ChatThread, ChatMessage, BookChunk
schemas.py
```
