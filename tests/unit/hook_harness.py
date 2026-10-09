"""The scratch checkouts and stub environments the hook tests are built on.

Separate from the modules that assert against it, because the two change for
different reasons. The harness moves when the shape of a checkout changes —
worktrees, virtual environments, pushed refs. The tests move when the hooks do.

Nothing here asserts anything. `python_files = test_*.py` in `pytest.ini` keeps
this module out of collection, so it is a library the test modules import.

**It runs on Windows under Git Bash as well as on Linux and macOS.** Paths handed
to bash are POSIX-style (`Path.as_posix()`), bash is the one the machine's git
ships rather than whatever `bash` the PATH happens to find first (on Windows
that can be the WSL launcher), and symlinks are made with `git update-index`
rather than the file system, because the file system may refuse them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# The checkout these tests are running from, derived from this file's own path
# rather than asked of git, so a constant this file needs before it can collect
# does not depend on how the repository happens to be configured.
REPO = Path(__file__).resolve().parents[2]

# The kit stores its hooks in `hooks/`; an installed project has `.git-hooks/`.
# The tests copy the kit's into a scratch checkout under the installed name, so
# they exercise the layout a project really has.
HOOKS = REPO / ".git-hooks"

IS_WINDOWS = sys.platform.startswith("win")


def _find_bash():
    """The bash that ships with git on this machine, or the PATH's own."""
    override = os.environ.get("KIT_TEST_BASH")
    if override:
        return override
    candidates = []
    if IS_WINDOWS:
        git = shutil.which("git")
        if git:
            root = Path(git).resolve().parent.parent
            candidates += [root / "bin" / "bash.exe", root.parent / "bin" / "bash.exe"]
        candidates += [
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
        ]
        for one in candidates:
            if one.is_file():
                return str(one)
    return shutil.which("bash") or "bash"


BASH = _find_bash()


def posix(path) -> str:
    """A path in the form bash wants.

    On Windows that is the MSYS form, `/c/Users/...`, not `C:/Users/...`: the
    drive letter's colon would be read as a separator wherever the path lands in
    a `PATH` list, and every use of it here may.
    """
    text = Path(path).as_posix()
    if IS_WINDOWS and len(text) > 2 and text[1] == ":" and text[2] == "/":
        return "/" + text[0].lower() + text[2:]
    return text


# A PATH with nothing project-specific on it: bash, git and the coreutils a hook
# needs, and no pytest, black, python or gitleaks — which is the condition the
# missing-tool tests assert on, and one that cannot be faked by unsetting a
# variable. On Windows git lives in /mingw64/bin, which is added.
BARE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin" + (":/mingw64/bin" if IS_WINDOWS else "")

# **The caller's own setup, scrubbed.** These tests assert what a hook found on
# a machine they built; anything inherited from the machine they are running on
# can only make that answer a lie.
#
# `GIT_*`: when these tests run inside `pre-commit`, git has exported `GIT_DIR`,
# `GIT_INDEX_FILE` and friends. A `git init` in a scratch directory then quietly
# operates on the real repository instead.
#
# `VIRTUAL_ENV`: the suite is normally run from inside an activated environment,
# so a test asking "did `activate_venv` find nothing?" would read that variable
# and be told about this checkout's venv.
#
# `KIT_HOOK_REEXEC`: the hand-off exports it, so a suite run by a hook that
# handed off inherits "a hand-off already happened".
#
# `PYTHONPATH`: `activate_venv` sets it, so a test asking what the hook put there
# would be reading the caller's own answer back.
_SCRUBBED = ("VIRTUAL_ENV", "KIT_HOOK_REEXEC", "PYTHONPATH")


def _clean_env(**extra):
    """The environment, less `GIT_*`, `VIRTUAL_ENV`, `KIT_HOOK_REEXEC`
    and `PYTHONPATH`."""
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("GIT_") and k not in _SCRUBBED
    }
    environment.update(extra)
    return environment


def _git(*arguments, cwd, check=True):
    """Run git in a scratch checkout, free of the caller's git variables."""
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        env=_clean_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def _commit(repo, message, *, allow_empty=False):
    """Commit what is staged in a scratch checkout.

    **The identity is passed rather than configured**, so nothing here depends
    on the git config of the machine running the suite. `--no-verify` because a
    scratch repository exists to have a hook run at it deliberately, in the body
    of a test, and not on the way in.
    """
    _git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        *(["--allow-empty"] if allow_empty else []),
        "--quiet",
        "--no-verify",
        "-m",
        message,
        cwd=repo,
    )


def _run_gate(command, cwd):
    """Run a gate script against a tree and hand back the completed process."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=_clean_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _run(
    script: str,
    cwd: Path,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
):
    """Run a bash snippet and hand back the completed process.

    `bash` rather than `sh`: the hooks have a bash shebang and use bash-only
    forms — `[[`, arrays, process substitution — so running them under sh would
    test a shell the project does not use.
    """
    environment = _clean_env(
        PATH=os.environ["PATH"],
        # **The scratch directory is the home, not the real one.** Git Bash's
        # profile prepends `~/bin` to PATH, so a developer's own gitleaks (or
        # black, or python) there would win over the stub a test put first and
        # make the test describe the machine instead of the hook.
        HOME=posix(cwd),
    )
    if env:
        environment.update(env)
    # **Bytes in, bytes out.** Text mode turns every `\n` written to stdin into
    # `\r\n` on Windows, and the hook then reads a sha with a carriage return on
    # it — a bug in the harness, not in git, which writes LF everywhere.
    finished = subprocess.run(
        [BASH, "-c", script],
        cwd=cwd,
        env=environment,
        capture_output=True,
        check=False,
        # `pre-push` reads the refs being pushed from stdin, one line per ref.
        # `stdin_text` is how a test plays git's side of it; the empty default
        # is the honest stand-in for "run by hand, no refs given".
        input=(stdin_text or "").encode("utf-8"),
    )
    return subprocess.CompletedProcess(
        finished.args,
        finished.returncode,
        finished.stdout.decode("utf-8", errors="replace"),
        finished.stderr.decode("utf-8", errors="replace"),
    )


def write_lf(path: Path, text: str, mode: int | None = None) -> None:
    """Write `text` with LF line endings, whatever the platform.

    `Path.write_text` turns `\n` into CRLF on Windows, and a bash script or a
    `.kit/config.env` with a carriage return on every line is a different file
    than the one meant.
    """
    path.write_bytes(text.encode("utf-8"))
    if mode is not None:
        path.chmod(mode)


def write_config(root: Path, **settings):
    """Write `.kit/config.env` in a scratch checkout from KIT_* keyword names.

    `write_config(root, STACK="python")` writes `KIT_STACK="python"`.
    """
    (root / ".kit").mkdir(exist_ok=True)
    lines = [f'KIT_{key}="{value}"' for key, value in settings.items()]
    write_lf(root / ".kit" / "config.env", "\n".join(lines) + "\n")


def _scratch_repo(tmp_path, name, **config):
    """A one-commit git checkout with the kit's real hooks and tools.

    Every test here needs the same thing: somewhere git-shaped that holds the
    hook files under test and nothing else. The stale-hook self-check compares
    the running file against `<toplevel>/.git-hooks/<name>`, so the whole
    directory is copied rather than the one hook — without that a hook would
    refuse for the wrong reason and its test would pass while proving nothing.

    `tools/` is copied too, because the hooks call `tools/doc_structure.py` and
    friends by relative path. `config` keywords are `.kit/config.env` keys
    without the `KIT_` prefix.

    `--no-verify` on the commit, because the hooks being copied in are the ones
    that would otherwise run against this scratch checkout.
    """
    scratch = tmp_path / name
    scratch.mkdir()
    shutil.copytree(HOOKS, scratch / ".git-hooks")
    shutil.copytree(
        REPO / "tools", scratch / "tools", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copyfile(REPO / ".gitignore", scratch / ".gitignore")
    if config:
        write_config(scratch, **config)

    _git("init", "--quiet", cwd=scratch)
    _git("config", "core.autocrlf", "false", cwd=scratch)
    _git("add", "-A", cwd=scratch)
    _commit(scratch, "checkout")
    return scratch


def _push_line(repo, path, contents):
    """Commit one file and hand back the ref line git would give `pre-push`.

    Git writes `<local ref> <local sha> <remote ref> <remote sha>` on stdin, one
    line per ref. The remote sha here is the commit before this one, which is
    the ordinary case: a branch the remote already has, moving forward by one.
    """
    before = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    write_lf(repo / path, contents)
    _git("add", path, cwd=repo)
    _commit(repo, f"add {path}")
    after = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()
    return f"refs/heads/main {after} refs/heads/main {before}\n"


def _run_pre_push(hooks_in, refs, *, cwd=None, path=None, env=None):
    """Run a checkout's `pre-push` the way git does, and hand back what it said.

    Git writes the ref lines on stdin, and passing them is the one thing a test
    of this hook cannot get wrong quietly — a hook that cannot see its refs
    falls back to running everything and still exits zero. So the call shape
    lives here rather than being written out per test.

    Hands back `(result, stdout + stderr)`, which is what every caller wants.
    """
    environment = {"PATH": path or BARE_PATH}
    if env:
        environment.update(env)
    result = _run(
        f'exec "{posix(hooks_in)}/.git-hooks/pre-push"',
        cwd=cwd or hooks_in,
        env=environment,
        stdin_text=refs,
    )
    return result, result.stdout + result.stderr


def _run_pre_commit(repo, *, path=None, env=None):
    """Run a checkout's `pre-commit` against whatever is staged in it."""
    environment = {"PATH": path or os.environ["PATH"]}
    if env:
        environment.update(env)
    result = _run(
        f'exec "{posix(repo)}/.git-hooks/pre-commit"', cwd=repo, env=environment
    )
    return result, result.stdout + result.stderr


def _stub_venv(root, name=".venv", layout="bin"):
    """A virtual environment that is only the part `activate_venv` reads.

    An `activate` that sets `VIRTUAL_ENV` and puts its executables directory on
    `PATH`, which is all the function looks for and all the assertions read.
    `layout` is `bin` (Linux, macOS) or `Scripts` (Windows): the hook must find
    both. Building a real one would cost seconds and prove less.

    Built after the checkout is committed, the way a real one is: an environment
    is a cache on disk, not something the repository tracks.
    """
    venv = root / name
    stub = venv / layout
    stub.mkdir(parents=True)
    write_lf(
        stub / "activate",
        f'export VIRTUAL_ENV="{posix(venv)}"\nexport PATH="{posix(stub)}:$PATH"\n',
    )
    return venv


def _stub_tools(venv, ledger, *names, layout="bin", code=0):
    """Stand-in tools inside a stub environment, each logging its name and args.

    They are the only copies on the `PATH` a test hands a hook, so a name in
    `ledger` proves the hook used this environment, and the arguments say what it
    was asked. They exit `code`, zero by default.
    """
    for name in names:
        write_lf(
            venv / layout / name,
            f'#!/bin/bash\necho "{name} $*" >> "{posix(ledger)}"\nexit {code}\n',
            0o755,
        )


def _stub_pylint(venv, ledger, *, layout="bin", reporting=(), broken_with=None):
    """A `pylint` that records the arguments it was given, and can report R0801.

    `reporting` holds `(first, second)` module-name pairs to report as
    `duplicate-code`, in the shape real pylint prints: the `R0801` line, then one
    `==module:[start:end]` line per side. A non-empty `reporting` also exits 8,
    pylint's code for a refactor message, so the hook sees a real refusal rather
    than a tool that printed something and passed.

    `broken_with` is an exit code for a pylint that did not run at all — 32 is a
    usage error, 1 a fatal. Such a run prints no `R0801` and reports nothing,
    which is the shape a gate reading only its own filter mistakes for a clean
    tree.
    """
    tool = venv / layout / "pylint"
    log = posix(ledger)
    if broken_with is not None:
        write_lf(
            tool,
            "#!/bin/bash\n"
            f'echo "pylint $*" >> "{log}"\n'
            'echo "pylint: error: this run never happened" >&2\n'
            f"exit {broken_with}\n",
            0o755,
        )
        return tool

    findings = ""
    for first, second in reporting:
        findings += (
            f'echo "{first}.py:1:0: R0801: Similar lines in 2 files"\n'
            f'echo "=={first}:[1:5]"\n'
            f'echo "=={second}:[1:5]"\n'
            'echo " (duplicate-code)"\n'
        )
    write_lf(
        tool,
        "#!/bin/bash\n"
        f'echo "pylint $*" >> "{log}"\n' + findings + f"exit {8 if reporting else 0}\n",
        0o755,
    )
    return tool


def _stub_on_path(directory, name, body="exit 0"):
    """An executable stub named `name` in `directory`, for a PATH entry."""
    directory.mkdir(parents=True, exist_ok=True)
    stub = directory / name
    write_lf(stub, f"#!/bin/bash\n{body}\n", 0o755)
    return stub


def _python_dir():
    """The directory holding the interpreter running this suite, POSIX-style."""
    return posix(Path(sys.executable).parent)


def _ask_activate_venv(cwd, *, config_dir=None):
    """Source `common.sh`, call `activate_venv`, and report what it activated.

    `VENV=` and then the path, or `VENV=none`. Asserted on rather than
    `command -v pytest`, because the machine running this suite has a pytest on
    PATH already — asking about pytest would pass whether the lookup worked or
    not.
    """
    where = posix(config_dir or cwd)
    return _run(
        f'source "{where}/.git-hooks/common.sh"; activate_venv; rc=$?; '
        'echo "VENV=${VIRTUAL_ENV:-none}"; echo "PP=${PYTHONPATH:-none}"; exit $rc',
        cwd=cwd,
        env={"PATH": BARE_PATH},
    )


def _ask_skip_sentence(function="tests_not_needed_note", subject="staged"):
    """Source `common.sh` and return the sentence a skipped gate reads."""
    return subprocess.run(
        [BASH, "-c", f'source "{posix(HOOKS)}/common.sh"; {function} "{subject}"'],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env=_clean_env(),
    ).stdout


def _stage_link(repo, path, target):
    """Stage a symlink at `path` pointing at `target`, without the file system.

    `git update-index --cacheinfo 120000` records exactly what a real symlink
    would, on a machine whose file system may refuse to make one (Windows
    without developer mode, or `core.symlinks=false`).
    """
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo,
        env=_clean_env(),
        input=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout.strip()
    _git("update-index", "--add", "--cacheinfo", f"120000,{blob},{path}", cwd=repo)
