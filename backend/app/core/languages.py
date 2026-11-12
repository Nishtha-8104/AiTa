from dataclasses import dataclass

from app.features.grading.models import Language


@dataclass(frozen=True)
class LanguageSpec:
    extension: str
    compile_cmd: list[str] | None
    run_cmd: list[str]
    comment_prefixes: tuple[str, ...]
    func_pattern: str | None
    lizard_name: str | None
    executable: bool


def _inert(extension: str, prefixes: tuple[str, ...]) -> LanguageSpec:
    return LanguageSpec(
        extension=extension,
        compile_cmd=None,
        run_cmd=[],
        comment_prefixes=prefixes,
        func_pattern=None,
        lizard_name=None,
        executable=False,
    )


SPECS: dict[Language, LanguageSpec] = {
    Language.PYTHON: LanguageSpec(
        extension=".py",
        compile_cmd=["python", "-m", "py_compile", "{src}"],
        run_cmd=["python", "{src}"],
        comment_prefixes=("#",),
        func_pattern=r"^\s*def\s+\w+\s*\(",
        lizard_name="python",
        executable=True,
    ),
    Language.CPP: LanguageSpec(
        extension=".cpp",
        compile_cmd=["g++", "-O2", "-std=c++17", "{src}", "-o", "{bin}"],
        run_cmd=["{bin}"],
        comment_prefixes=("//", "/*", "*"),
        func_pattern=r"^\w[\w:*&<>]*\s+\w+\s*\(",
        lizard_name="cpp",
        executable=True,
    ),
    Language.C: LanguageSpec(
        extension=".c",
        compile_cmd=["gcc", "-O2", "-std=c17", "{src}", "-o", "{bin}", "-lm"],
        run_cmd=["{bin}"],
        comment_prefixes=("//", "/*", "*"),
        func_pattern=r"^\w[\w\s*]*[\s*]\w+\s*\(",
        lizard_name="c",
        executable=True,
    ),
    Language.JAVA: _inert(".java", ("//", "/*", "*")),
    Language.JAVASCRIPT: _inert(".js", ("//", "/*", "*")),
    Language.TYPESCRIPT: _inert(".ts", ("//", "/*", "*")),
    Language.GO: _inert(".go", ("//", "/*", "*")),
    Language.RUST: _inert(".rs", ("//", "/*", "*")),
    Language.SQL: _inert(".sql", ("--",)),
}

EXECUTABLE_LANGUAGES: frozenset[Language] = frozenset(
    lang for lang, spec in SPECS.items() if spec.executable
)


def spec_for(language: Language) -> LanguageSpec:
    return SPECS[language]
