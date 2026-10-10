#!/usr/bin/env python3
"""Find out whether the installed CoderSkill skills match the signed `main` of the source clone.

Agents install only reviewed code: the commits on `origin/main` of the CoderSkill clone that
installed them. A commit is trusted when it carries a valid signature from

- GitHub's web-flow key (squash merges made on github.com), pinned by fingerprint and kept in a
  dedicated keyring, or
- an SSH key listed in the git `gpg.ssh.allowedSignersFile` (the owner's machines).

Sources: https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification
(GitHub signs web commits; rebase merges are not signed), https://github.com/web-flow.gpg (the key),
https://git-scm.com/docs/git-verify-commit.

Standard library only. The hooks import this module; `coderskill install` uses it to install.
"""

from __future__ import annotations

import argparse
import fcntl
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "coderskill"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state") / "coderskill"
SOURCE_FILE = CONFIG_DIR / "source.json"
TRUST_DIR = CONFIG_DIR / "trust" / "gnupg"
LATEST_FILE = STATE_DIR / "latest.json"
FETCH_STAMP = STATE_DIR / "last-fetch"
LOCK_FILE = STATE_DIR / "install.lock"
SESSIONS_DIR = STATE_DIR / "sessions"

REMOTE = "origin"
BRANCH = "main"
REMOTE_REF = f"{REMOTE}/{BRANCH}"
FETCH_INTERVAL = 600  # seconds; shared by every session on this machine
FETCH_TIMEOUT = 6     # the session-start hook itself has 10 seconds

GITHUB_KEY_URL = "https://github.com/web-flow.gpg"
# "GitHub <noreply@github.com>", created 2024-01-16; replaced 4AEE18F83AFDEB23, which expired that day.
GITHUB_KEY_FINGERPRINTS = frozenset({"968479A1AFF927E37D1A566BB5690EEEBB952194"})

RECEIPT = ".coderskill-installed.json"
SOURCE_COMMIT = "_source_commit"  # receipt key; skill names never start with "_"
AGENT_SOURCES = {"claude": ".claude", "codex": ".agents", "gemini": ".gemini"}
# Codex reads user skills from ~/.codex/skills and ~/.agents/skills (openai/codex, codex-rs/ext/skills/src/host_roots.rs).
AGENT_TARGETS = {"claude": ".claude/skills", "codex": ".codex/skills", "gemini": ".gemini/skills"}
# Changes to these paths alter rules or hook behaviour: agents are told during a session.
IMPORTANT = re.compile(r"^(hooks/|scripts/install|scripts/coderskill\.py$|scripts/update_channel\.py$|skills/[^/]+/SKILL\.md$)")
SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


# ---------------------------------------------------------------- small helpers


def git(repo: Path, *args: str, timeout: float = 10, env: dict | None = None) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              timeout=timeout, check=False, env=env)
    except (OSError, subprocess.SubprocessError):
        return None


def git_value(repo: Path, *args: str) -> str:
    result = git(repo, *args)
    return result.stdout.strip() if result and result.returncode == 0 else ""


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temporary, path)


@contextmanager
def install_lock():
    """One install at a time on this machine, across sessions and agents."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


# ---------------------------------------------------------------- source and receipts


def source_repo() -> Path | None:
    value = read_json(SOURCE_FILE).get("repo")
    if not value:
        return None
    path = Path(value)
    return path if (path / "skills").is_dir() and git_value(path, "rev-parse", "--git-dir") else None


def record_source(repo: Path) -> None:
    write_json(SOURCE_FILE, {"repo": str(repo.resolve())})


def receipt_path(agent: str, home: Path = HOME) -> Path:
    return home / AGENT_TARGETS[agent] / RECEIPT


def installed_commit(agent: str, home: Path = HOME) -> str | None:
    return read_json(receipt_path(agent, home)).get(SOURCE_COMMIT)


def installed_skill_dirs(home: Path = HOME) -> list[Path]:
    """Folders written by `coderskill install`, from the receipts."""
    folders = []
    for agent in AGENT_TARGETS:
        receipt = read_json(receipt_path(agent, home))
        folders.extend(home / AGENT_TARGETS[agent] / name for name in receipt if not name.startswith("_"))
    return folders


# ---------------------------------------------------------------- trust


def ensure_trust(download=urllib.request.urlopen) -> str | None:
    """Import GitHub's web-flow key into the dedicated keyring. Returns an error or None."""
    if TRUST_DIR.is_dir() and trusted_fingerprints() & GITHUB_KEY_FINGERPRINTS:
        return None
    try:
        with download(GITHUB_KEY_URL, timeout=15) as response:
            key = response.read()
    except OSError as error:
        return f"could not download {GITHUB_KEY_URL}: {error}"
    TRUST_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    TRUST_DIR.chmod(0o700)
    result = subprocess.run(["gpg", "--homedir", str(TRUST_DIR), "--batch", "--quiet", "--import"],
                            input=key, capture_output=True, check=False)
    if result.returncode != 0 or not trusted_fingerprints() & GITHUB_KEY_FINGERPRINTS:
        shutil.rmtree(TRUST_DIR, ignore_errors=True)
        return "the downloaded key does not have the pinned GitHub fingerprint; check it at " + GITHUB_KEY_URL
    return None


def trusted_fingerprints() -> set[str]:
    try:
        output = subprocess.run(["gpg", "--homedir", str(TRUST_DIR), "--batch", "--with-colons", "--fingerprint"],
                                capture_output=True, text=True, check=False).stdout
    except OSError:
        return set()
    return {line.split(":")[9] for line in output.splitlines() if line.startswith("fpr:")}


def signature_ok(repo: Path, commit: str, fingerprints: frozenset = GITHUB_KEY_FINGERPRINTS) -> bool:
    """True when `commit` has a valid signature from the pinned GitHub key or an allowed SSH signer."""
    env = {**os.environ, "GNUPGHOME": str(TRUST_DIR)}
    result = git(repo, "verify-commit", "--raw", commit, env=env)
    if result is None or result.returncode != 0:
        return False
    return trusted_output(result.stderr, fingerprints)


def trusted_output(output: str, fingerprints: frozenset = GITHUB_KEY_FINGERPRINTS) -> bool:
    """Parse `git verify-commit --raw` output (GnuPG status lines or the ssh-keygen message)."""
    for line in output.splitlines():
        fields = line.split()
        # VALIDSIG <signing-key fpr> ... <primary-key fpr> (GnuPG doc/DETAILS)
        if fields[:2] == ["[GNUPG:]", "VALIDSIG"] and len(fields) > 2 and {fields[2], fields[-1]} & fingerprints:
            return True
    # SSH: git prints 'Good "git" signature for <principal>' only when allowedSignersFile lists the key.
    return 'Good "git" signature for ' in output


def unsigned_commits(repo: Path, old: str | None, new: str) -> list[str]:
    """Commits after `old` up to `new` without a trusted signature (only `new` when `old` is unknown)."""
    ancestor = git(repo, "merge-base", "--is-ancestor", old, new) if old else None
    if ancestor is not None and ancestor.returncode == 0:
        commits = git_value(repo, "rev-list", f"{old}..{new}").split()
    else:
        commits = [new]
    return [commit for commit in commits if not signature_ok(repo, commit)]


# ---------------------------------------------------------------- update state


def fetch(repo: Path, force: bool = False) -> bool | None:
    """Fetch `main` at most every FETCH_INTERVAL seconds. None = skipped, True/False = result."""
    try:
        age = time.time() - FETCH_STAMP.stat().st_mtime
    except OSError:
        age = None
    if not force and age is not None and age < FETCH_INTERVAL:
        return None
    FETCH_STAMP.parent.mkdir(parents=True, exist_ok=True)
    FETCH_STAMP.touch()
    result = git(repo, "fetch", "--quiet", REMOTE, BRANCH, timeout=FETCH_TIMEOUT)
    return bool(result and result.returncode == 0)


def changed_paths(repo: Path, old: str | None, new: str) -> list[str] | None:
    if not old:
        return None
    result = git(repo, "diff", "--name-only", old, new)
    return result.stdout.split() if result and result.returncode == 0 else None


def is_important(paths: list[str] | None) -> bool:
    return paths is None or any(IMPORTANT.match(path) for path in paths)


def status(agent: str, do_fetch: bool = True, home: Path = HOME) -> dict:
    """State of this agent's installed skills against `origin/main`.

    state: current | outdated | untrusted | unavailable
    """
    repo = source_repo()
    installed = installed_commit(agent, home)
    if repo is None:
        return {"state": "unavailable", "reason": "no CoderSkill source clone recorded; run scripts/coderskill install from the clone",
                "installed": installed}
    fetched = fetch(repo) if do_fetch else None
    latest = git_value(repo, "rev-parse", "--verify", "--quiet", f"{REMOTE_REF}^{{commit}}")
    if not latest:
        return {"state": "unavailable", "reason": f"{REMOTE_REF} not found in the source clone", "installed": installed}
    result = {"installed": installed, "latest": latest, "fetched": fetched}
    if installed == latest:
        result["state"] = "current"
    else:
        unsigned = unsigned_commits(repo, installed, latest)
        result["state"] = "untrusted" if unsigned else "outdated"
        if unsigned:
            result["unsigned"] = [commit[:12] for commit in unsigned]
        result["important"] = is_important(changed_paths(repo, installed, latest))
        result["summary"] = git_value(repo, "log", "-1", "--format=%s", latest)
    write_json(LATEST_FILE, {"commit": latest, "checked_at": int(time.time()), "state": result["state"]})
    return result


def refresh_if_due(agent: str, home: Path = HOME) -> None:
    """Fetch and refresh the cached state when the shared fetch interval has passed."""
    try:
        if time.time() - FETCH_STAMP.stat().st_mtime < FETCH_INTERVAL:
            return
    except OSError:
        pass
    status(agent, home=home)


def cached_latest() -> str | None:
    return read_json(LATEST_FILE).get("commit")


# ---------------------------------------------------------------- per-session notes


def session_file(session_id: str | None) -> Path | None:
    return SESSIONS_DIR / f"{session_id}.json" if session_id and SESSION_ID.match(session_id) else None


def remember_session(session_id: str | None, agent: str, home: Path = HOME) -> None:
    path = session_file(session_id)
    if path:
        write_json(path, {"installed_at_start": installed_commit(agent, home), "notified": []})


def session_notice(session_id: str | None, agent: str, home: Path = HOME) -> str | None:
    """Text to show once per event: skills changed during the session, or an important update waits."""
    path = session_file(session_id)
    if path is None:
        return None
    state = read_json(path)
    notified = set(state.get("notified", []))
    installed = installed_commit(agent, home)
    notes = []
    start = state.get("installed_at_start")
    if path.is_file() and installed and installed != start and f"installed:{installed}" not in notified:
        notified.add(f"installed:{installed}")
        notes.append(
            f"CoderSkill skills for {agent} were updated during this session ({(start or 'unknown')[:12]} -> "
            f"{installed[:12]}). Tell the user. The agent may still hold rules from the old version; "
            "restarting the session is the user's decision.")
    repo = source_repo()
    latest = cached_latest()
    if repo and latest and latest != installed and f"latest:{latest}" not in notified:
        if is_important(changed_paths(repo, installed, latest)):
            notified.add(f"latest:{latest}")
            notes.append(
                f"An important CoderSkill update is on main ({latest[:12]}). Tell the user. With their agreement, "
                f"run `coderskill install --update --agents {agent}`; restarting is the user's decision.")
    if not notes:
        return None
    write_json(path, {**state, "notified": sorted(notified)})
    return "\n".join(notes)


def start_notice(agent: str, home: Path = HOME) -> str | None:
    """Session-start text for the update state, or None when the skills are current."""
    result = status(agent, home=home)
    state = result["state"]
    if state == "current":
        return None
    if state == "unavailable":
        return f"CoderSkill update check: {result['reason']}."
    if state == "untrusted":
        return (f"CoderSkill update check: main has commits without a trusted signature "
                f"({', '.join(result['unsigned'])}). Do not install. Tell the user; the installed version stays in use.")
    note = (f"CoderSkill update available on main: {result['latest'][:12]} \"{result['summary']}\" "
            f"(installed: {(result['installed'] or 'unknown')[:12]}). Before other work, run "
            f"`coderskill install --update --agents {agent}` and tell the user what changed.")
    if result.get("fetched") is False:
        note += " (The fetch failed; this is the last known state.)"
    return note


# ---------------------------------------------------------------- snapshot


def export_snapshot(repo: Path, commit: str, destination: Path) -> None:
    """Write the tree of `commit` to `destination` (no working tree, no untracked files)."""
    archive = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit],
                             capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(destination, filter="data")


# ---------------------------------------------------------------- command line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("status", "post-merge"))
    parser.add_argument("--agent", default="claude", choices=sorted(AGENT_TARGETS))
    args = parser.parse_args()
    if args.command == "post-merge":
        # Called by the global post-merge git hook in every repository; act only in the source clone on main.
        repo = source_repo()
        here = git_value(Path.cwd(), "rev-parse", "--show-toplevel")
        if repo and here and Path(here).resolve() == repo.resolve() and git_value(repo, "branch", "--show-current") == BRANCH:
            for agent in AGENT_TARGETS:
                status(agent, do_fetch=False)
        return 0
    print(json.dumps(status(args.agent), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
