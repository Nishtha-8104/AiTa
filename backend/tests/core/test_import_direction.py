import ast
import pathlib
import re

APP = pathlib.Path(__file__).resolve().parents[2] / "app"
CORE = APP / "core"
FEATURE_MODELS = re.compile(r"^app\.features\.\w+\.models(\.\w+)?$")
ROUTER = re.compile(r"^app\.features\.\w+\.router(_\w+)?(\.\w+)?$")


def _imported_names(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                yield f"{node.module}.{alias.name}"


def test_core_imports_only_feature_models():
    offenders = []
    for path in CORE.glob("*.py"):
        for name in _imported_names(path):
            if name.startswith("app.features") and not FEATURE_MODELS.match(name):
                offenders.append(f"{path.name} -> {name}")
    assert offenders == [], f"core/ may import only app.features.<x>.models: {offenders}"


def test_only_main_imports_routers():
    offenders = []
    for path in APP.rglob("*.py"):
        if path == APP / "main.py":
            continue
        for name in _imported_names(path):
            if ROUTER.match(name):
                offenders.append(f"{path.relative_to(APP)} -> {name}")
    assert offenders == [], f"routers are wired in main.py only: {offenders}"
