"""Curated open-licence books for the chatbot's search_books tool, and their parsers."""

import pathlib
import re
from dataclasses import dataclass, field
from typing import Literal

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import PreformattedString

from app.core.config import settings
from app.features.chat.logic.rag.chunker import Block, Section

GUIDES = settings.CONTENT_DIR / "guides"
DEFAULT_SECTION = "Introduction"

TEXT_TAGS = {"p", "li", "dt", "dd", "blockquote", "figcaption", "caption", "td", "th"}
CODE_TAGS = {"pre", "textarea"}
INLINE_TAGS = {"a", "abbr", "b", "cite", "code", "dfn", "em", "i", "kbd", "mark", "q", "s",
               "samp", "small", "span", "strong", "sub", "sup", "time", "tt", "u", "var"}
BLOCK_TAGS = ["p", "pre", "ul", "ol", "dl", "div", "table", "textarea", "li", "section"]
DEFAULT_DROP = ["script", "style", "nav", "footer", "header", "noscript", "button",
                ".headerlink"]


@dataclass(frozen=True)
class SourceSpec:
    id: str
    title: str
    license: str
    url: str
    lang_tag: str
    fetch: Literal["html", "pdf", "local"]
    entry_urls: tuple[str, ...] = ()
    index_urls: tuple[str, ...] = ()
    follow: str | None = None
    pdf_url: str | None = None
    local_paths: tuple[str, ...] = ()
    html_selectors: dict = field(default_factory=dict)
    enabled: bool = True


_RUNESTONE_SELECTORS = {
    "root": "div#main-content",
    "drop": DEFAULT_DROP + [".adcopy", ".ac_actions", ".ac_output"],
}


def _runestone(book: str) -> dict:
    base = f"https://runestone.academy/ns/books/published/{book}/"
    return {
        "url": base + "index.html",
        "index_urls": (base + "index.html",),
        "follow": rf"^{re.escape(base)}\w+/(?!toctree)\w+\.html$",
        "html_selectors": _RUNESTONE_SELECTORS,
    }


_PY4E = "https://www.py4e.com/html3/"
_PY4E_CHAPTERS = ("01-intro", "02-variables", "03-conditional", "04-functions", "05-iterations",
                  "06-strings", "07-files", "08-lists", "09-dictionaries", "10-tuples",
                  "11-regex", "12-network", "13-web", "14-objects", "15-database", "16-viz")
_OPENSTAX = "https://openstax.org/books/introduction-python-programming/pages/"
_BEEJ = "https://beej.us/guide/bgc/html/split/"

SOURCES: list[SourceSpec] = [
    SourceSpec(
        id="py4e", title="Python for Everybody (Severance)", license="CC BY-NC-SA",
        url=_PY4E, lang_tag="python", fetch="html",
        entry_urls=tuple(_PY4E + c for c in _PY4E_CHAPTERS),
        html_selectors={"root": "main#main-content",
                        "drop": DEFAULT_DROP + ["section.footnotes"]},
    ),
    SourceSpec(
        id="openstax-python", title="OpenStax Introduction to Python Programming",
        license="CC BY 4.0", url=_OPENSTAX + "preface", lang_tag="python", fetch="html",
        index_urls=tuple(f"{_OPENSTAX}{n}-introduction" for n in range(1, 16)),
        follow=rf"^{re.escape(_OPENSTAX)}\d+-[\w-]+$",
        html_selectors={"root": "div.main-content-styles", "drop": DEFAULT_DROP,
                        "chapter": "h2", "section": "h3", "subsection": "h4"},
    ),
    SourceSpec(
        id="pythonds",
        title="Problem Solving with Algorithms and Data Structures using Python (Miller, Ranum)",
        license="CC BY-NC-SA 4.0", lang_tag="python", fetch="html", **_runestone("pythonds"),
    ),
    SourceSpec(
        id="cppds",
        title="Problem Solving with Algorithms and Data Structures using C++ "
              "(Miller, Ranum, Pearce)",
        license="CC BY-NC-SA 4.0", lang_tag="cpp", fetch="html", **_runestone("cppds"),
    ),
    SourceSpec(
        id="beej-c", title="Beej's Guide to C Programming",
        license="CC BY-NC-ND 3.0 (code public domain)", url=_BEEJ + "index.html",
        lang_tag="c", fetch="html",
        index_urls=(_BEEJ + "index.html",),
        follow=rf"^{re.escape(_BEEJ)}(?!index)[\w-]+\.html$",
        html_selectors={"root": "body",
                        "drop": DEFAULT_DROP + ["body > div:not(.sourceCode)", "body > hr"]},
    ),
    SourceSpec(
        id="modern-c", title="Modern C (Gustedt)", license="CC BY-NC-ND 4.0",
        url="https://gustedt.gitlabpages.inria.fr/modern-c/", lang_tag="c", fetch="pdf",
        pdf_url="https://inria.hal.science/hal-02383654/document",
    ),
    SourceSpec(
        id="python-docs", title="The Python Tutorial and Built-in Exceptions (docs.python.org)",
        license="PSF documentation licence", url="https://docs.python.org/3/tutorial/",
        lang_tag="python", fetch="html",
        index_urls=("https://docs.python.org/3/tutorial/index.html",),
        follow=r"^https://docs\.python\.org/3/tutorial/(?!index)\w+\.html$",
        entry_urls=("https://docs.python.org/3/library/exceptions.html",),
        html_selectors={"root": "div.body", "drop": DEFAULT_DROP},
    ),
    *[
        SourceSpec(
            id=f"pet-guide-{tag}", title=title, license="PET (own work)", url="",
            lang_tag=tag, fetch="local", local_paths=(f"{tag}.md",),
        )
        for tag, title in (("general", "PET misconception guide"),
                           ("c", "PET guide to common C errors"),
                           ("cpp", "PET guide to common C++ errors"),
                           ("python", "PET guide to common Python errors"))
    ],
]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("¶", "")).strip()


class _SectionBuilder:
    def __init__(self, chapter: str):
        self.chapter = chapter
        self.section = ""
        self.parent = ""
        self.sections: list[Section] = []

    def heading(self, level: str, text: str) -> None:
        if level == "chapter":
            self.chapter, self.section, self.parent = text, "", ""
        elif level == "section":
            self.section = self.parent = text
        else:
            self.section = f"{self.parent} / {text}" if self.parent else text

    def add(self, kind: str, text: str) -> None:
        if not text.strip():
            return
        section = self.section or DEFAULT_SECTION
        last = self.sections[-1] if self.sections else None
        if last is None or (last.chapter, last.section) != (self.chapter, section):
            last = Section(self.chapter, section, [])
            self.sections.append(last)
        last.blocks.append(Block(kind, text))


def parse_html(html: str, selectors: dict | None = None) -> list[Section]:
    selectors = selectors or {}
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text() if soup.title else ""
    for sel in selectors.get("drop", DEFAULT_DROP):
        for node in soup.select(sel):
            node.decompose()
    root = soup.select_one(selectors["root"]) if "root" in selectors else None
    root = root or soup.body or soup

    levels = {selectors.get("chapter", "h1"): "chapter",
              selectors.get("section", "h2"): "section",
              selectors.get("subsection", "h3"): "subsection"}
    out = _SectionBuilder(_clean(re.split(r" [|\-–—] ", title)[0]))

    for br in root.find_all("br"):
        br.replace_with("\n")
    block_like = BLOCK_TAGS + list(levels)

    def walk(node: Tag) -> None:
        loose: list[str] = []

        def flush() -> None:
            out.add("text", _clean("".join(loose)))
            loose.clear()

        for child in node.children:
            if isinstance(child, PreformattedString):
                continue
            if isinstance(child, NavigableString):
                loose.append(str(child))
                continue
            if not isinstance(child, Tag):
                continue
            name = child.name
            if name in INLINE_TAGS and not child.find(block_like):
                loose.append(child.get_text())
                continue
            flush()
            if name in levels:
                out.heading(levels[name], _clean(child.get_text()))
            elif name in CODE_TAGS:
                out.add("code", child.get_text())
            elif name in TEXT_TAGS and not child.find(block_like):
                out.add("text", _clean(child.get_text()))
            else:
                walk(child)
        flush()

    walk(root)
    return out.sections


def parse_pdf(path: str | pathlib.Path) -> list[Section]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    starts: list[tuple[int, int, str]] = []

    def visit(items, depth: int) -> None:
        for item in items:
            if isinstance(item, list):
                visit(item, depth + 1)
            elif depth <= 1:
                try:
                    starts.append((reader.get_destination_page_number(item), depth,
                                   _clean(item.title)))
                except Exception:
                    continue

    try:
        visit(reader.outline, 0)
    except Exception:
        starts = []
    starts.sort(key=lambda s: s[0])

    fallback = _clean((reader.metadata or {}).get("/Title", "") or pathlib.Path(path).stem)
    out = _SectionBuilder(fallback)
    cursor = 0
    for number, page in enumerate(reader.pages):
        while cursor < len(starts) and starts[cursor][0] <= number:
            _, depth, title = starts[cursor]
            out.heading("chapter" if depth == 0 else "section", title)
            cursor += 1
        if not starts:
            out.heading("section", f"Page {number + 1}")
        text = page.extract_text() or ""
        lines = [ln.strip() for ln in text.splitlines()]
        kept = [ln for ln in lines if ln and not ln.isdigit()]
        out.add("text", " ".join(kept))
    return out.sections


def load_local(paths: list[str | pathlib.Path]) -> list[Section]:
    sections: list[Section] = []
    for path in paths:
        path = pathlib.Path(path)
        if not path.is_absolute():
            path = GUIDES / path
        out = _SectionBuilder(path.stem)
        para: list[str] = []
        code: list[str] | None = None

        def end_para() -> None:
            if para:
                out.add("text", " ".join(para))
                para.clear()

        for line in path.read_text(encoding="utf-8").splitlines():
            if code is not None:
                if line.strip().startswith("```"):
                    out.add("code", "\n".join(code))
                    code = None
                else:
                    code.append(line)
            elif line.strip().startswith("```"):
                end_para()
                code = []
            elif line.startswith("## "):
                end_para()
                out.heading("section", line[3:].strip())
            elif line.startswith("# "):
                end_para()
                out.heading("chapter", line[2:].strip())
            elif not line.strip():
                end_para()
            else:
                para.append(line.strip())
        end_para()
        sections.extend(out.sections)
    return sections
