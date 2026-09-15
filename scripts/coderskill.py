#!/usr/bin/env python3
"""Install CoderSkill globally and generate a safe project-start prompt."""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def install(update: bool) -> int:
    home = Path.home(); targets = {"codex": home / ".codex/skills", "claude": home / ".claude/skills", "gemini": home / ".gemini/skills"}
    for tool, target in targets.items():
        target.mkdir(parents=True, exist_ok=True)
        source = ROOT / (".agents" if tool == "codex" else f".{tool}") / "skills"
        for skill in source.iterdir():
            destination = target / skill.name
            if destination.exists() and not update:
                print(f"preserved existing {tool}/{skill.name}; use --update to replace")
                continue
            if destination.exists(): shutil.rmtree(destination)
            shutil.copytree(skill, destination)
            print(f"installed {tool}/{skill.name}")
    bindir = home / ".local/bin"; bindir.mkdir(parents=True, exist_ok=True)
    link = bindir / "coderskill"
    if link.exists() or link.is_symlink(): link.unlink()
    link.symlink_to(Path(__file__).resolve())
    print(f"installed command at {link}")
    return 0

def start(args) -> int:
    repo = args.github or "not yet assigned"
    prompt = f"Use the professional-coding skill. Read the current project instructions and profile. GitHub repository: {repo}. Classify this directory, preserve main, select only applicable skills, and execute the complete validated workflow. Do not copy CoderSkill into this project. Do not perform destructive actions, credential operations, or hardware writes. Communicate with the user in Turkish and write repository artifacts in English."
    print(prompt)
    if not args.run: return 0
    agent = args.agent
    if not agent:
        available = [name for name in ("codex", "claude", "gemini") if shutil.which(name)]
        if len(available) != 1:
            if not available: print("No supported AI CLI found. Install or specify --agent codex|claude|gemini.", file=sys.stderr)
            else: print("Multiple AI CLIs found; choose one with --agent: " + ", ".join(available), file=sys.stderr)
            return 2
        agent = available[0]
    command = {"codex": "codex", "claude": "claude", "gemini": "gemini"}[agent]
    return subprocess.call([command, prompt])

def main():
    parser = argparse.ArgumentParser(prog="coderskill"); sub = parser.add_subparsers(dest="command", required=True)
    i = sub.add_parser("install"); i.add_argument("--update", action="store_true")
    s = sub.add_parser("start"); s.add_argument("phrase", nargs="+"); s.add_argument("--github"); s.add_argument("--agent", choices=("codex", "claude", "gemini")); s.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.command == "install": return install(args.update)
    if "execute" not in args.phrase or "order" not in args.phrase or "66" not in args.phrase: print("Use: coderskill start execute order 66", file=sys.stderr); return 2
    return start(args)

if __name__ == "__main__": raise SystemExit(main())
