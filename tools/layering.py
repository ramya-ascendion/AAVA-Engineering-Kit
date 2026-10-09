#!/usr/bin/env python
#
# The layering gate: which area of the package may import which.
#
# An "area" is a top-level folder under the package directory
# (`KIT_PACKAGE_DIR` in `.kit/config.env`). The rule is that an import that
# crosses from one area into another must be a named crossing, with a reason,
# so the dependency graph is something a person decided rather than something
# that happened. This file decides it; the tables below hold the decisions.
#
# **A fresh project starts with both tables empty**, which means every
# cross-area import is refused until it is named. That is the point: the first
# time an area reaches into another, somebody writes down why. A project with a
# single area, or one that does not want this gate, leaves the package
# directory absent. Put code in area folders: a module sitting directly in the
# package root is an area of its own, so two such modules importing each other
# are a crossing.

from __future__ import annotations

import ast
import pathlib
import sys

from kit_config import load, package_dir

SETTINGS = load()
PACKAGE = package_dir(SETTINGS)
# The name the package is imported by. `import <name>.x.y` and `from <name>.x
# import y` are the two spellings the gate reads.
IMPORT_NAME = SETTINGS["KIT_PYTHON_PACKAGE"]

# **Folders under the package that hold no Python source of this project,
# named by their path from the package root.** A bare folder name matched at any
# depth, and a skipped folder is invisible in both directions (imports *of* it
# vanish too), so a path is the only safe spelling. `__pycache__` stays a name
# because it appears at every depth by design and holds no source.
SKIP_PATHS: set[str] = set()
SKIP_NAMES = {"__pycache__", "node_modules"}

# **Leaves: areas importable from anywhere, because they reach no other area.**
# The gate proves that second clause rather than trusting it, so the set cannot
# quietly stop being true. Example: `LEAVES = {"domain", "config"}`.
LEAVES: set[str] = set()

# **Every edge that crosses into something that is not a leaf.**
#
# Format, one entry per edge:
#
#     ("importing_area", "imported_area"): (
#         "the reason this edge exists, in a sentence a stranger could check",
#         {"imported_area.module", "imported_area.other.module"},  # or None
#     ),
#
# The reason is required reading, not decoration. The second element names the
# modules the edge may import; `None` means any module in that area. Restricting
# it is what turns "A may use B" from a sentence in a design note into something
# that fails when A reaches for a part of B nobody agreed to.
CROSSINGS: dict[tuple[str, str], tuple[str, set[str] | None]] = {}

# Crossings only an area's own tests may make. The allowed set on a crossing
# names what may be imported, never who may import it, so an edge that exists
# for a test suite reads as permission for the whole area without this. An
# entry is the same `(importing, imported)` pair as in CROSSINGS.
TESTS_ONLY: set[tuple[str, str]] = set()

# Areas that may import nothing from any other area. Example: a `domain` area
# of plain shapes.
NO_IMPORT_AREAS: set[str] = set()


def area_of(module: str) -> str:
    """The part of the tree a module belongs to: its top-level folder."""
    return module.split(".")[0]


def modules() -> dict[str, pathlib.Path]:
    """Every module the walk classifies, keyed by its dotted name."""
    found = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        parts = path.relative_to(PACKAGE).parts
        if parts[0] in SKIP_PATHS or any(part in SKIP_NAMES for part in parts):
            continue
        if any("." in part for part in parts[:-1]) or parts[-1].count(".") > 1:
            # A file named `a.b.py` keys as the module `a.b` and silently
            # replaces it, hiding every import the real one makes.
            raise ValueError(
                f"{path} has a dot in a path segment, which collides with a "
                "module name. Rename it."
            )
        # as_posix: a Windows path would otherwise key every module with a backslash
        # and no import would ever match one.
        name = path.relative_to(PACKAGE).as_posix()[:-3].replace("/", ".")
        if name == "__init__":
            continue
        found[name[:-9] if name.endswith(".__init__") else name] = path
    return found


def importable() -> set[str]:
    """Every name `import <package>.X` can reach, which is more than `modules()`.

    A folder with no `__init__.py` is still a package to Python, and the root
    package itself is a name. Treating either as unknown made the unresolved
    check refuse imports that run — the one failure a gate must not have.
    """
    names = set(modules())
    names.add("")
    for path in PACKAGE.rglob("*"):
        if not path.is_dir():
            continue
        parts = path.relative_to(PACKAGE).parts
        if parts and (parts[0] in SKIP_PATHS or any(p in SKIP_NAMES for p in parts)):
            continue
        names.add(".".join(parts))
    return names


def imports_of(
    name: str,
    path: pathlib.Path,
    known: set[str],
    *,
    unresolved: set[str] | None = None,
    unreadable: set[str] | None = None,
    reachable: set[str] | None = None,
    at_runtime: bool = False,
) -> set[str]:
    """Every module of the package this one imports, by whichever form it used.

    **Both statement forms.** `from x import y` is what the package uses today,
    and reading only that made the gate blind to `import <package>.x.y` — which is
    the same edge written the other way.
    """
    reachable = known if reachable is None else reachable
    package = name.rsplit(".", 1)[0] if "." in name else ""
    if path.name == "__init__.py":
        package = name
    out: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as bad:
        # A file the walk cannot read is a file whose edges nobody knows, so it
        # is a fault rather than a traceback about something else.
        if unreadable is not None:
            unreadable.add(f"{bad.__class__.__name__}: {bad}")
        return out
    guarded: set[int] = set()
    if at_runtime:
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.dump(node.test):
                for statement in node.body:
                    guarded.update(id(one) for one in ast.walk(statement))
    for node in ast.walk(tree):
        if id(node) in guarded:
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".") if package else []
                up = node.level - 1
                base = base[: len(base) - up] if up else base
                target = ".".join(base + ([node.module] if node.module else []))
            elif node.module and (
                node.module == IMPORT_NAME
                or node.module.startswith(f"{IMPORT_NAME}.")
            ):
                target = (
                    node.module[len(IMPORT_NAME) + 1 :] if "." in node.module else ""
                )
            else:
                continue
            asked = {
                f"{target}.{alias.name}" if target else alias.name
                for alias in node.names
            }
            named = asked & known
            if unresolved is not None and not named and target not in reachable:
                # Naming nothing is not the same as naming nothing forbidden.
                unresolved |= asked
            if named:
                # `from x import y` where `y` is a module names `x.y`, not `x`.
                # Recording both let a bare-package entry into the allow-list,
                # and a bare package makes the narrowing beside it decoration.
                out |= named
            elif target in known:
                out.add(target)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(f"{IMPORT_NAME}."):
                    inner = alias.name[len(IMPORT_NAME) + 1 :]
                    if inner in known:
                        out.add(inner)
                    elif unresolved is not None and inner not in reachable:
                        unresolved.add(inner)
    return out


def faults() -> list[str]:
    """Every import that crosses a boundary nothing names."""
    known = modules()
    reachable = importable()
    if not known:
        return [
            f"no Python found under {PACKAGE}, so nothing was checked. "
            "A gate handed nothing fails rather than passes."
        ]
    bad = []
    for name, path in sorted(known.items()):
        here = area_of(name)
        unresolved: set[str] = set()
        unreadable: set[str] = set()
        for target in sorted(
            imports_of(
                name,
                path,
                set(known),
                unresolved=unresolved,
                unreadable=unreadable,
                reachable=reachable,
            )
        ):
            there = area_of(target)
            if there == here:
                continue
            if here in NO_IMPORT_AREAS:
                bad.append(
                    f"{name} imports {target}: {here}/ is listed in NO_IMPORT_AREAS, "
                    "so it may import nothing from another area"
                )
                continue
            if here in LEAVES and there not in LEAVES:
                # Never nameable: a leaf anything may import must not drag a
                # non-leaf area in behind it.
                bad.append(
                    f"{name} imports {target}: {here}/ is a leaf, so anything may "
                    "import it — it may not reach a non-leaf area"
                )
                continue
            if there in LEAVES:
                continue
            named = CROSSINGS.get((here, there))
            if named is None:
                bad.append(
                    f"{name} imports {target}: {here} -> {there} is not a named crossing"
                )
            elif named[1] is not None and not any(
                target == one or target.startswith(f"{one}.") for one in named[1]
            ):
                bad.append(
                    f"{name} imports {target}: {here} -> {there} is named, but only "
                    f"for {sorted(named[1])}"
                )
            elif (here, there) in TESTS_ONLY and ".tests." not in f"{name}.":
                bad.append(
                    f"{name} imports {target}: {here} -> {there} is named for "
                    f"{here}/'s own tests, and this is not one of them"
                )
        for why in sorted(unreadable):
            bad.append(f"{name} cannot be read, so its imports are unknown — {why}")
        for missing in sorted(unresolved):
            bad.append(
                f"{name} imports {IMPORT_NAME}.{missing}, which is no module here — "
                "the gate cannot say which side of a boundary it falls on"
            )
    return bad + cycles(known) + leaves_reach_no_other_area(known)


def leaves_reach_no_other_area(known: dict[str, pathlib.Path]) -> list[str]:
    """Prove the leaf claim instead of trusting it.

    "Anything may import a leaf" is only safe if the whole closure below a leaf
    stays among leaves. Checking one hop let a leaf reach a non-leaf area two
    hops out through a crossing somebody had named.
    """
    edges = {name: imports_of(name, path, set(known)) for name, path in known.items()}
    bad = []
    for leaf in sorted(LEAVES):
        seen: set[str] = set()
        stack = [n for n in known if area_of(n) == leaf]
        while stack:
            for target in edges.get(stack.pop(), ()):
                if target in seen:
                    continue
                seen.add(target)
                stack.append(target)
        reached = sorted({area_of(t) for t in seen if area_of(t) not in LEAVES})
        if reached:
            bad.append(
                f"{leaf}/ is a leaf, so anything may import it — but it reaches "
                f"{', '.join(reached)}. Either it is not a leaf, or that path is."
            )
    return bad


def cycles(known: dict[str, pathlib.Path]) -> list[str]:
    """Import cycles between modules, which no layering rule would catch.

    Two folders may point at each other and stay honest as long as no *module*
    closes the loop. A comment saying so is not a check.
    """
    edges = {
        name: imports_of(name, path, set(known), at_runtime=True)
        for name, path in known.items()
    }
    found: list[str] = []
    seen: set[str] = set()
    stack: list[str] = []

    def walk(node: str) -> None:
        if node in stack:
            loop = stack[stack.index(node) :] + [node]
            found.append("import cycle: " + " -> ".join(loop))
            return
        if node in seen:
            return
        seen.add(node)
        stack.append(node)
        for target in sorted(edges.get(node, ())):
            walk(target)
        stack.pop()

    for node in sorted(known):
        walk(node)
    return found


def main() -> int:
    """Print what crosses a boundary nothing names. Exit 1 if anything does."""
    bad = faults()
    for line in bad:
        print(f"  {line}")
    if bad and not modules():
        # Nothing was read, so "imports cross a boundary" would be the one thing
        # the operator must not conclude.
        return 1
    if bad:
        print(f"{len(bad)} import(s) cross a boundary nothing names.")
        print("Name the edge, with its reason, in CROSSINGS here, or move the module.")
        return 1
    print("every import runs the way the layering tables say")
    return 0


if __name__ == "__main__":
    sys.exit(main())
