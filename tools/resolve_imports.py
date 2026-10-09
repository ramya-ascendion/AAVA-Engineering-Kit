"""Every import of the project's own package names a module and a name that exist.

**This is the only check that sees the whole tree.** mypy reads what
`[tool.mypy]` names, and the test runner imports only test modules, so a script,
a harness or a recorder that imports the package and is neither can carry a
broken import through a green run and fail when somebody runs it.

**It checks names, not only modules.** Resolving the module alone is not
enough. When `reads.py` becomes `reads/named.py`, `from pkg.reads import Found`
still resolves the package and fails only at the attribute, so a module-level
version of this check passes a tree that cannot run.

**The package is the project's own**: `KIT_PYTHON_PACKAGE` in
`.kit/config.env`, imported from the parent of `KIT_PACKAGE_DIR`.

**This tool is outside the quality bars**, the same way `tools/guarantees.py`
is: coverage and CRAP measure the package, not `tools/`. Measure it by hand:

    COVERAGE_FILE=/tmp/.cov-resolve coverage run --source=tools -m pytest -q       tests/unit/test_resolve_imports.py
    COVERAGE_FILE=/tmp/.cov-resolve coverage report --include="*resolve_imports.py*"
"""

from __future__ import annotations

import ast
import importlib
import pathlib
import sys

from kit_config import load, source_root

# `.claude` holds agent sessions' worktrees, each a whole checkout of some other
# branch, so a stale one would fail this tree for imports it does not have.
SKIP = {
    ".venv",
    "venv",
    "build",
    "node_modules",
    ".git",
    ".claude",
    "vendor",
    "__pycache__",
}


def _helper_paths(root: pathlib.Path) -> list[str]:
    """The directories `pytest.ini` puts on the path, so a test helper imports.

    `pythonpath` there is the owner. A test module imports its helpers from
    those directories, and the pre-commit gate runs this as a script, where
    pytest has not set the path.
    """
    ini = root / "pytest.ini"
    if not ini.is_file():
        return []
    for line in ini.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("pythonpath") and "=" in stripped:
            return [str(root / part) for part in stripped.split("=", 1)[1].split()]
    return []


def check(root: pathlib.Path) -> list[str]:
    """Return one line per unresolved import. Empty means the tree hangs together.

    The path entries are removed again on the way out, so this leaves the
    caller's `sys.path` no longer than it found it. That is hygiene and nothing
    more: resolution is decided by `sys.modules`, which this does not clear, so
    a second call in one process sees the first call's modules either way.
    """
    settings = load(root)
    added = [str(source_root(settings, root)), *_helper_paths(root)]

    for entry in reversed(added):
        sys.path.insert(0, entry)
    try:
        return _walk(root)
    finally:
        for entry in added:
            if entry in sys.path:
                sys.path.remove(entry)


def _walk(root: pathlib.Path) -> list[str]:
    """The walk itself, so `check` holds only the path bookkeeping."""
    settings = load(root)
    own = settings["KIT_PYTHON_PACKAGE"]
    # The project's own virtualenv is never source, whatever it is called.
    skip = SKIP | {settings["KIT_VENV_DIR"].split("/")[0]}
    fails: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in skip for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level or not node.module:
                continue
            if node.module != own and not node.module.startswith(f"{own}."):
                continue
            where = f"{path.relative_to(root)}:{node.lineno}"
            try:
                module = importlib.import_module(node.module)
            except Exception as exc:  # pylint: disable=broad-except
                fails.append(f"{where}: cannot import {node.module} -> {exc!r}")
                continue
            for alias in node.names:
                if alias.name == "*" or hasattr(module, alias.name):
                    continue
                try:
                    importlib.import_module(f"{node.module}.{alias.name}")
                except ModuleNotFoundError:
                    fails.append(f"{where}: {node.module} has no {alias.name!r}")
                except Exception as exc:  # pylint: disable=broad-except
                    fails.append(
                        f"{where}: {node.module}.{alias.name} exists but raised"
                        f" on import -> {exc!r}"
                    )
    return fails


def main() -> int:
    """Print what did not resolve. Exit 1 if anything did not."""
    root = pathlib.Path(__file__).resolve().parent.parent
    fails = check(root)
    for line in fails:
        print(f"  {line}")
    if fails:
        print(f"{len(fails)} unresolved imports of the project package")
        return 1
    print("every import of the project package resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
