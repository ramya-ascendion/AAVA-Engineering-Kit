"""Check that the agent documentation still hangs together.

Four questions, none of which needs judgment, which is why they are a script
rather than a paragraph somebody has to remember (`docs/agents/writing-a-rule.md`).

- **Reachable.** Every `docs/agents/*.md` can be reached from `AGENTS.md` by
  following links. A file nothing points at is loaded by nobody.
- **Resolvable.** Every relative Markdown link between those files lands on a
  file that exists.
- **Registered.** Every path a registry names — `rule:`, `gate:` and
  `template:` in `tools/document_types.yaml`, and in `tools/issue_types.yaml`
  when the project has one — exists.
- **Enforced.** Every entry claiming `enforcement: deterministic` names the
  gate that decides it. A claim nothing runs is the decoration the enforcement
  field exists to prevent.

Run it with no arguments, from the repo root. It looks at the whole
tree rather than a staged file list, because "nothing points at this file" is
not a question a single file can answer.

**The roots are fixed**: `AGENTS.md`, `docs/agents/`, and the registry
`tools/document_types.yaml`. With PyYAML installed the registry is parsed
properly; without it a small line reader handles the registry's own shape
(`- type:` entries with flat `key: value` lines), so a project with no Python
environment can still run the gate.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # the line reader below stands in
    yaml = None

AGENTS = Path("AGENTS.md")
AGENT_DOCS = Path("docs/agents")
# The first is required; the rest are checked when the project has them.
REGISTRY = Path("tools/document_types.yaml")
# `document_types.local.yaml` is the project's own: types, `allowed_paths` and
# `forbidden_paths` that the kit's generic registry cannot know. The installer
# never overwrites it.
OPTIONAL_REGISTRIES = (
    Path("tools/issue_types.yaml"),
    Path("tools/document_types.local.yaml"),
)
REGISTRIES = (REGISTRY, *OPTIONAL_REGISTRIES)

# **Two patterns, because the two checks ask different things.**
#
# Reachability asks whether anything points at a file, and a backticked
# `docs/agents/foo.md` is as good a pointer as a link — most of `AGENTS.md`
# names its leaves that way.
_REFERENCE = re.compile(
    r"(?:\]\(|`)(?:\./)?(?:docs/agents/)?([a-z0-9][a-z0-9._-]*\.md)"
)

# Link resolution asks whether a pointer lands, and only a real Markdown link
# is a pointer. A backticked name is prose and is often a nickname:
# `design-handoff.md` calls `docs/design/design-project-github.md` "github.md"
# throughout, and treating that as a broken link would be a false alarm.
_LINK = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")

# A registry entry naming a file this repo owns. `template:` is here because a
# promised template that was never written is the failure the templates exist to
# prevent — a rule pointing at something that is not there. Prose naming the
# templates directory is not checked, which is how the directory went missing
# for two commits while two files said where it was.
_REGISTRY_PATH_KEYS = ("rule", "gate", "template")


_ENTRY = re.compile(r"^\s*-\s+(type|name):\s*(.*?)\s*$")
_KEY = re.compile(r"^\s+([a-z_]+):\s*(.*?)\s*$")


def _load_types(registry: Path) -> list[dict]:
    """The registry's `types:` entries, with or without PyYAML."""
    text = registry.read_text(encoding="utf-8")
    if yaml is not None:
        return (yaml.safe_load(text) or {}).get("types", [])
    # Fallback: only the keys this gate reads, from the registry's own shape.
    entries: list[dict] = []
    in_types = False
    for line in text.splitlines():
        if line.startswith("types:"):
            in_types = True
            continue
        if not in_types or line.lstrip().startswith("#"):
            continue
        opened = _ENTRY.match(line)
        if opened and line.startswith("  - "):
            entries.append({opened.group(1): opened.group(2)})
            continue
        keyed = _KEY.match(line)
        if keyed and entries and keyed.group(1) in (
            "name",
            "rule",
            "gate",
            "template",
            "enforcement",
        ):
            entries[-1].setdefault(keyed.group(1), keyed.group(2).strip("\"'"))
    return entries


def _exists(named: str) -> bool:
    """Whether a registry path exists.

    A `.git-hooks/x` path also counts when `hooks/x` exists: the kit stores its
    hooks in `hooks/` and an installed project in `.git-hooks/`, and a registry
    shared between the two should not be wrong in one of them.
    """
    path = Path(named)
    if path.is_file():
        return True
    if path.parts[:1] == (".git-hooks",):
        return Path("hooks", *path.parts[1:]).is_file()
    return False


def _registries() -> list[Path]:
    """Required registry first, then any optional one that exists."""
    return [REGISTRY, *(one for one in OPTIONAL_REGISTRIES if one.is_file())]


def _references(path: Path) -> set[str]:
    """Every sibling document name mentioned by `path`."""
    return set(_REFERENCE.findall(path.read_text(encoding="utf-8")))


def _reachable_from_agents() -> set[str]:
    """The agent docs reachable from `AGENTS.md`, following links transitively.

    Transitively on purpose: an index file is the point. `issue-tracker.md`
    names the board rules so that `AGENTS.md` does not have to, and both are
    reachable.
    """
    if not AGENTS.is_file():
        return set()
    frontier = [name for name in _references(AGENTS) if (AGENT_DOCS / name).is_file()]
    seen: set[str] = set()
    while frontier:
        name = frontier.pop()
        if name in seen:
            continue
        seen.add(name)
        frontier.extend(
            found
            for found in _references(AGENT_DOCS / name)
            if (AGENT_DOCS / found).is_file() and found not in seen
        )
    return seen


def check_reachable() -> list[str]:
    on_disk = {path.name for path in AGENT_DOCS.glob("*.md")}
    if on_disk and not AGENTS.is_file():
        return [f"{AGENTS} — missing, so nothing in {AGENT_DOCS}/ can be reached"]
    orphans = sorted(on_disk - _reachable_from_agents())
    return [
        f"docs/agents/{name} — nothing reaches it from AGENTS.md" for name in orphans
    ]


def check_links() -> list[str]:
    problems = []
    docs = [one for one in [AGENTS, *AGENT_DOCS.glob("*.md")] if one.is_file()]
    for path in sorted(docs):
        for target in sorted(set(_LINK.findall(path.read_text(encoding="utf-8")))):
            # Relative to the linking file, the way a reader following it would
            # resolve it.
            if (path.parent / target).is_file():
                continue
            problems.append(f"{path} — links to {target}, which does not exist")
    return problems


def check_registries() -> list[str]:
    problems = []
    for registry in _registries():
        if not registry.is_file():
            problems.append(f"{registry} — missing")
            continue
        for entry in _load_types(registry):
            for key in _REGISTRY_PATH_KEYS:
                named = entry.get(key)
                if named and not _exists(named):
                    problems.append(
                        f"{registry} — {entry.get('name') or entry.get('type')}"
                        f" names {key}: {named}, which does not exist"
                    )
    return problems


def check_enforcement() -> list[str]:
    """Every deterministic entry names the gate that decides it.

    `deterministic` says a script settles the rule, so an entry claiming it
    without a `gate:` claims an enforcement that does not run. The other two
    values are checked by nobody on purpose: `hybrid` and `inferred` both end
    in a person's judgment, which is the whole reason they are not scripts.
    """
    problems = []
    for registry in _registries():
        if not registry.is_file():
            continue
        for entry in _load_types(registry):
            if entry.get("enforcement") != "deterministic" or entry.get("gate"):
                continue
            problems.append(
                f"{registry} — {entry.get('name') or entry.get('type')}"
                " is deterministic but names no gate:, so nothing decides it"
            )
    return problems


def _glob(pattern: str) -> re.Pattern[str]:
    """A registry path glob as a regex: `*` stays inside a folder, `**` crosses."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def _tracked_docs() -> list[str]:
    """Markdown files under `docs/` that git tracks, or all of them off git."""
    try:
        done = subprocess.run(
            ["git", "ls-files", "--", "docs"],
            capture_output=True,
            text=True,
            check=True,
        )
        names = done.stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        names = [p.as_posix() for p in Path("docs").rglob("*") if p.is_file()]
    return sorted(n for n in names if n.endswith(".md"))


def check_typed_docs() -> list[str]:
    """Every Markdown file under `docs/` belongs to a registered type.

    The registry's `paths:` said where each type lives, and nothing read them,
    so a design doc in a folder no type named passed untyped and unseen. Now a
    file under `docs/` must match a type's `paths:` or an `allowed_paths:`
    entry, and a file in `forbidden_paths:` is refused unless allowed by name.
    `docs/agents/` is held by the reachability check, not by this one.
    """
    if yaml is None:
        return []
    types: list[str] = []
    allowed: list[str] = []
    forbidden: list[tuple[str, str]] = []
    for registry in _registries():
        loaded = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
        for entry in loaded.get("types", []) or []:
            types.extend(entry.get("paths") or [])
        allowed.extend(loaded.get("allowed_paths") or [])
        for rule in loaded.get("forbidden_paths") or []:
            forbidden.append((rule["path"], rule.get("because", "")))
    type_globs = [_glob(p) for p in types]
    allowed_globs = [_glob(p) for p in allowed]
    problems = []
    for name in _tracked_docs():
        if name.startswith("docs/agents/") or any(g.match(name) for g in allowed_globs):
            continue
        banned = next((why for p, why in forbidden if _glob(p).match(name)), None)
        if banned is not None:
            problems.append(
                f"{name} — sits where no document may: {' '.join(banned.split())}"
                " Move it, or list it under allowed_paths: in"
                " tools/document_types.local.yaml."
            )
        elif not any(g.match(name) for g in type_globs):
            problems.append(
                f"{name} — matches no document type. Add the folder to a type's"
                " paths: in tools/document_types.local.yaml, or move the file."
            )
    return problems


def main() -> int:
    checks = (
        ("every agent doc is reachable from AGENTS.md", check_reachable),
        ("every link between agent docs resolves", check_links),
        ("every path a registry names exists", check_registries),
        ("every deterministic entry names its gate", check_enforcement),
        ("every doc under docs/ belongs to a registered type", check_typed_docs),
    )
    failed = False
    for question, check in checks:
        problems = check()
        if problems:
            failed = True
            print(f"  FAILED — {question}")
            for problem in problems:
                print(f"      {problem}")
        else:
            print(f"  ok — {question}")

    if failed:
        print()
        print("  A document nothing points at is a document nobody loads, and a")
        print("  pointer that resolves nowhere costs a reader the trip. Add the")
        print("  pointer, fix the path, or move the file to where it belongs.")
        print("  An enforcement nothing runs reads the same way: name the gate,")
        print("  or say hybrid and mean it.")
        print("  The rule is docs/agents/document-types.md.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
