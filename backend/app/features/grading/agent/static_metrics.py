"""Static code metrics via lizard (lines of code, cyclomatic complexity, comment ratio) and
rule-based style issues."""

import re

import lizard
from pydantic import BaseModel

from app.core.languages import spec_for
from app.features.grading.models import Language, SeverityLevel


class StaticMetrics(BaseModel):
    lines_of_code: int = 0
    comment_ratio: float = 0.0
    cyclomatic_complexity: int = 1
    max_function_length: int = 0
    max_parameter_count: int = 0
    function_count: int = 0
    token_count: int = 0


class Issue(BaseModel):
    line: int | None = None
    severity: str
    category: str
    message: str
    suggestion: str


def _is_comment(line: str, prefixes: tuple[str, ...]) -> bool:
    stripped = line.strip()
    return bool(stripped) and stripped.startswith(prefixes)


def measure(code: str, language: Language) -> StaticMetrics:
    spec = spec_for(language)
    lines = code.splitlines()
    comment_lines = sum(1 for line in lines if _is_comment(line, spec.comment_prefixes))

    if spec.lizard_name is None:
        code_lines = [line for line in lines
                      if line.strip() and not _is_comment(line, spec.comment_prefixes)]
        return StaticMetrics(
            lines_of_code=len(code_lines),
            comment_ratio=round(comment_lines / max(len(lines), 1), 3),
        )

    analysis = lizard.analyze_file.analyze_source_code(
        f"submission{spec.extension}", code
    )
    functions = analysis.function_list
    return StaticMetrics(
        lines_of_code=analysis.nloc,
        comment_ratio=round(comment_lines / max(len(lines), 1), 3),
        cyclomatic_complexity=max(
            [f.cyclomatic_complexity for f in functions] or [1]
        ),
        max_function_length=max([f.nloc for f in functions] or [0]),
        max_parameter_count=max([len(f.parameters) for f in functions] or [0]),
        function_count=len(functions),
        token_count=analysis.token_count,
    )


def find_issues(code: str, language: Language, metrics: StaticMetrics) -> list[Issue]:
    """Style and quality checks salvaged from the v1 StaticAnalyser.

    Correctness and security checks are deliberately gone: correctness is measured by
    execution now, and v1's regex security rules produced false positives on beginner
    code without ever affecting the score.
    """
    lines = code.splitlines()
    issues: list[Issue] = []

    if metrics.max_function_length > 40:
        issues.append(Issue(
            severity=SeverityLevel.WARNING, category="complexity",
            message=f"Longest function is {metrics.max_function_length} lines (over 40).",
            suggestion="Break it into smaller, single-responsibility functions.",
        ))

    if metrics.max_parameter_count > 5:
        issues.append(Issue(
            severity=SeverityLevel.WARNING, category="complexity",
            message=f"A function takes {metrics.max_parameter_count} parameters.",
            suggestion="Group related parameters into a structure, or split the function.",
        ))

    if metrics.cyclomatic_complexity > 10:
        issues.append(Issue(
            severity=SeverityLevel.WARNING, category="complexity",
            message=f"Cyclomatic complexity is {metrics.cyclomatic_complexity} (over 10).",
            suggestion="Reduce branching, or extract nested logic into helpers.",
        ))

    for index, line in enumerate(lines, start=1):
        indent = len(line) - len(line.lstrip())
        if line.strip() and indent // 4 >= 4:
            issues.append(Issue(
                line=index, severity=SeverityLevel.WARNING, category="complexity",
                message=f"Line {index} is nested {indent // 4} levels deep.",
                suggestion="Extract the inner block into a helper to flatten the nesting.",
            ))
            break

    for index, line in enumerate(lines, start=1):
        if len(line) > 100:
            issues.append(Issue(
                line=index, severity=SeverityLevel.INFO, category="style",
                message=f"Line {index} is {len(line)} characters long (over 100).",
                suggestion="Keep lines under 100 characters for readability.",
            ))
            break

    for index, line in enumerate(lines, start=1):
        if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line):
            issues.append(Issue(
                line=index, severity=SeverityLevel.INFO, category="quality",
                message=f"Unresolved marker at line {index}: {line.strip()[:60]}",
                suggestion="Resolve it or track it outside the submission.",
            ))
            break

    if language is Language.PYTHON:
        for match in re.finditer(r"except[^:]*:\s*\n\s*(pass\s*\n|#.*\n)", code):
            line_no = code[: match.start()].count("\n") + 1
            issues.append(Issue(
                line=line_no, severity=SeverityLevel.WARNING, category="logic",
                message=f"Empty or bare except block at line {line_no} silences all errors.",
                suggestion="Catch a specific exception and handle or re-raise it.",
            ))
            break

        for match in re.finditer(r"\bclass\s+([a-z][a-zA-Z0-9_]*)\b", code):
            line_no = code[: match.start()].count("\n") + 1
            name = match.group(1)
            issues.append(Issue(
                line=line_no, severity=SeverityLevel.WARNING, category="naming",
                message=f"Class `{name}` should use PascalCase.",
                suggestion=f"PEP 8 names classes like `{name.capitalize()}`.",
            ))
            break

    return issues
