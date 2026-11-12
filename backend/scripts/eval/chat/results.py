"""Output handling shared by the eval scripts: results.jsonl grows one row per finished
item, so a stopped run picks up where it left off, and summary.json is rewritten at the end."""

import argparse
import json
import tempfile
from pathlib import Path

from app.core.config import settings

DATA = settings.CONTENT_DIR / "eval" / "chat"


def default_out(name: str) -> Path:
    return Path(tempfile.gettempdir()) / "pet-eval" / name


def parser(description: str, name: str, data: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--data", type=Path, default=DATA / data, help="dataset (JSONL)")
    p.add_argument("--out", type=Path, default=default_out(name),
                   help="output directory (default: %(default)s)")
    p.add_argument("--limit", type=int, default=None, help="run at most this many new items")
    p.add_argument("--ids", default=None, help="comma-separated ids to run, nothing else")
    return p


def pending(rows: list[dict], done: set[str], *, ids: str | None = None,
            limit: int | None = None) -> list[dict]:
    """Items not done yet; named --ids run again even if done (their new row wins)."""
    if ids:
        wanted = {i.strip() for i in ids.split(",") if i.strip()}
        todo = [r for r in rows if r["id"] in wanted]
    else:
        todo = [r for r in rows if r["id"] not in done]
    return todo if limit is None else todo[:limit]


class Results:
    def __init__(self, out: Path):
        self.dir = Path(out)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "results.jsonl"

    def rows(self) -> list[dict]:
        """The latest row per id."""
        if not self.path.exists():
            return []
        rows: dict[str, dict] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.pop(row["id"], None)
            rows[row["id"]] = row
        return list(rows.values())

    def reset(self) -> None:
        self.path.unlink(missing_ok=True)

    def done(self) -> set[str]:
        return {r["id"] for r in self.rows()}

    def append(self, row: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def finish(self, summary: dict) -> None:
        text = json.dumps(summary, indent=2, ensure_ascii=False)
        (self.dir / "summary.json").write_text(text + "\n", encoding="utf-8")
        print(text)
        print(f"\nresults: {self.path}\nsummary: {self.dir / 'summary.json'}")
