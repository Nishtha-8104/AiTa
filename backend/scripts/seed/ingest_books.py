import argparse
import hashlib
import pathlib
import re
import tempfile
import time
from collections.abc import Callable
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

from app.features.chat.logic.rag.chunker import Chunk, Section, chunk
from app.features.chat.logic.rag.sources import SOURCES, SourceSpec, load_local, parse_html, parse_pdf
from scripts._local_db import LOCAL_DB_HINT, require_local_db

USER_AGENT = "PET-book-ingest/1.0 (academic research; +https://github.com/mananchhabhaya)"
DEFAULT_CACHE = pathlib.Path(tempfile.gettempdir()) / "pet-book-cache"
EMBED_BATCH = 64

Fetcher = Callable[[str], bytes]


class HttpFetcher:
    def __init__(self, cache_dir: pathlib.Path, delay: float = 1.0):
        import httpx

        self.cache_dir = cache_dir
        self.delay = delay
        self.client = httpx.Client(follow_redirects=True, timeout=60,
                                   headers={"User-Agent": USER_AGENT})
        cache_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self, url: str) -> bytes:
        path = self.cache_dir / hashlib.sha1(url.encode()).hexdigest()
        if path.exists():
            return path.read_bytes()
        time.sleep(self.delay)
        response = self.client.get(url)
        response.raise_for_status()
        path.write_bytes(response.content)
        return response.content

    def close(self) -> None:
        self.client.close()


class DbSink:
    def __init__(self, db):
        self.db = db

    def write(self, source_id: str, rows: list[dict]) -> None:
        from sqlalchemy import delete
        from sqlalchemy.dialects.postgresql import insert

        from app.features.chat.models import BookChunk

        try:
            for start in range(0, len(rows), 500):
                stmt = insert(BookChunk).values(rows[start:start + 500])
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_book_chunks_source_position",
                    set_={col: stmt.excluded[col] for col in rows[0]
                          if col not in ("source_id", "position")},
                )
                self.db.execute(stmt)
            self.db.execute(delete(BookChunk).where(BookChunk.source_id == source_id,
                                                    BookChunk.position >= len(rows)))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise


def _discover(spec: SourceSpec, fetch: Fetcher) -> list[str]:
    pattern = re.compile(spec.follow) if spec.follow else None
    seen: dict[str, None] = {}
    for index in spec.index_urls:
        soup = BeautifulSoup(fetch(index), "html.parser")
        for a in soup.select("a[href]"):
            url = urldefrag(urljoin(index, a["href"])).url
            if pattern and pattern.match(url):
                seen.setdefault(url)
    for url in spec.entry_urls:
        seen.setdefault(url)
    return list(seen)


def collect_sections(spec: SourceSpec, fetch: Fetcher) -> list[Section]:
    if spec.fetch == "local":
        return load_local(list(spec.local_paths))
    if spec.fetch == "pdf":
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "book.pdf"
            path.write_bytes(fetch(spec.pdf_url))
            return parse_pdf(path)
    import httpx

    sections: list[Section] = []
    for url in _discover(spec, fetch):
        try:
            html = fetch(url).decode("utf-8", errors="replace")
        except httpx.HTTPError as exc:
            print(f"  {spec.id}: skipped {url} ({exc})")
            continue
        for section in parse_html(html, spec.html_selectors):
            section.url = url
            sections.append(section)
    return sections


def _rows(spec: SourceSpec, chunks: list[Chunk], vectors: list[list[float]]) -> list[dict]:
    return [
        {"source_id": spec.id, "source_title": spec.title, "license": spec.license,
         "url": c.url or spec.url or None, "chapter": c.chapter[:255], "section": c.section[:255],
         "lang_tag": spec.lang_tag, "position": c.position, "text": c.text,
         "tokens": c.tokens, "embedding": v}
        for c, v in zip(chunks, vectors, strict=True)
    ]


def ingest_source(spec: SourceSpec, *, fetch: Fetcher, embed_fn, sink, dry_run: bool) -> int:
    chunks = chunk(collect_sections(spec, fetch))
    if dry_run or not chunks:
        return len(chunks)
    vectors: list[list[float]] = []
    for start in range(0, len(chunks), EMBED_BATCH):
        vectors.extend(embed_fn([c.text for c in chunks[start:start + EMBED_BATCH]]))
    sink.write(spec.id, _rows(spec, chunks, vectors))
    return len(chunks)


def select_sources(sources: list[SourceSpec], wanted: str | None) -> list[SourceSpec]:
    if wanted is None:
        return [s for s in sources if s.enabled]
    picked = [s for s in sources if s.id == wanted or s.id.startswith(wanted + "-")]
    if not picked:
        raise SystemExit(f"unknown source: {wanted}")
    return picked


def run(argv: list[str] | None = None, *, sources: list[SourceSpec] | None = None,
        fetch: Fetcher | None = None, embed_fn=None, sink=None) -> dict[str, int]:
    parser = argparse.ArgumentParser(description="Chunk, embed and store the chatbot's books.")
    parser.add_argument("--source", default=None, help="source id, or a prefix like pet-guide")
    parser.add_argument("--dry-run", action="store_true", help="parse and chunk only")
    parser.add_argument("--missing", action="store_true",
                        help="skip sources that are already in the database")
    parser.add_argument("--cache-dir", type=pathlib.Path, default=DEFAULT_CACHE)
    parser.add_argument("--allow-remote", action="store_true",
                        help="write even when DATABASE_URL is not a local database")
    args = parser.parse_args(argv)

    if not args.dry_run and sink is None and not args.allow_remote:
        require_local_db(hint=LOCAL_DB_HINT + ", or pass --allow-remote.")
    own_fetcher = HttpFetcher(args.cache_dir) if fetch is None else None
    fetch = fetch or own_fetcher
    db = None
    if not args.dry_run and sink is None:
        from app.core.database import SessionLocal

        db = SessionLocal()
        sink = DbSink(db)
    if not args.dry_run and embed_fn is None:
        from app.features.chat.logic.rag.embedder import embed as embed_fn

    done: set[str] = set()
    if args.missing and db is not None:
        from app.features.chat.models import BookChunk

        done = {sid for (sid,) in db.query(BookChunk.source_id).distinct()}

    counts: dict[str, int] = {}
    try:
        for spec in select_sources(sources if sources is not None else SOURCES, args.source):
            if spec.id in done:
                continue
            try:
                counts[spec.id] = ingest_source(spec, fetch=fetch, embed_fn=embed_fn,
                                                sink=sink, dry_run=args.dry_run)
            except Exception as exc:
                print(f"{spec.id}: FAILED ({type(exc).__name__}: {exc})")
                continue
            print(f"{spec.id}: {counts[spec.id]} chunks")
    finally:
        if db is not None:
            db.close()
        if own_fetcher is not None:
            own_fetcher.close()
    return counts


if __name__ == "__main__":
    run()
