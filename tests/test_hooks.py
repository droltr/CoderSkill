import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
HOOK = ROOT / "hooks" / "coderskill_hook.py"
_ISOLATION = tempfile.TemporaryDirectory()
# Keep the user's global git configuration and hooks out of the tests.
os.environ.update({"HOME": _ISOLATION.name, "XDG_CONFIG_HOME": f"{_ISOLATION.name}/.config", "GIT_CONFIG_NOSYSTEM": "1"})
os.environ.pop("GIT_CONFIG_GLOBAL", None)


def run_hook(event, data, agent="claude"):
    result = subprocess.run(
        ["python3", "-I", str(HOOK), event, "--agent", agent],
        input=json.dumps(data), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else None


def git(cwd, *args, check=True):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=check)


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "README.md").write_text("x\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-q", "-m", "init")

    def bash(self, command):
        output = run_hook("pre-tool", {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(self.repo)})
        return output["hookSpecificOutput"]["permissionDecision"] if output else None


class SessionStartTests(RepoTestCase):
    def test_injects_rules_and_open_requests(self):
        docs = self.repo / "docs"
        docs.mkdir()
        (docs / "REQUESTS.md").write_text("| 1 | Done thing | ✅ | x |\n| 2 | Open thing | ⏳ | — |\n")
        output = run_hook("session-start", {"cwd": str(self.repo)})
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("professional-coding", context)
        self.assertIn("Open thing", context)
        self.assertNotIn("Done thing", context)

    def test_private_requests_research_and_sync_state(self):
        private = self.repo / ".private"
        (private / "research").mkdir(parents=True)
        (private / "requests.md").write_text("| 3 | Private open item | 🔄 | — |\n")
        (private / "research" / "2026-10-10-topic.md").write_text("x")
        context = run_hook("session-start", {"cwd": str(self.repo)})["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Private open item", context)
        self.assertIn(".private/requests.md", context)
        self.assertIn("2026-10-10-topic.md", context)
        self.assertIn("No remote configured", context)

    def test_unpushed_commits_are_reported(self):
        remote = Path(self.tmp.name) / "remote.git"
        git(self.tmp.name, "init", "-q", "--bare", str(remote))
        git(self.repo, "remote", "add", "origin", str(remote))
        git(self.repo, "push", "-q", "-u", "origin", "main")
        context = run_hook("session-start", {"cwd": str(self.repo)})["hookSpecificOutput"]["additionalContext"]
        # Negative control: in sync, so no branch or commit lines.
        for text in ("Unpushed commits", "without a remote copy", "uncommitted", "No remote configured"):
            self.assertNotIn(text, context)
        (self.repo / "README.md").write_text("changed\n")
        git(self.repo, "commit", "-q", "-am", "local only")
        git(self.repo, "switch", "-q", "-c", "feat/local")
        context = run_hook("session-start", {"cwd": str(self.repo)})["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Unpushed commits on: main", context)
        self.assertIn("Branches without a remote copy: feat/local", context)

    def test_missing_signing_is_reported(self):
        context = run_hook("session-start", {"cwd": str(self.repo)})["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Commit signing is not configured", context)

    def test_signing_with_yes_and_inline_key_is_recognised(self):
        git(self.repo, "config", "commit.gpgsign", "yes")
        git(self.repo, "config", "gpg.format", "ssh")
        git(self.repo, "config", "user.signingkey", "key::ssh-ed25519 AAAA test")
        context = run_hook("session-start", {"cwd": str(self.repo)})["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("Commit signing is not configured", context)

    def test_configured_signing_is_not_reported(self):
        # Negative control: an existing SSH signing key and commit.gpgsign=true.
        key = Path(self.tmp.name) / "signing.pub"
        key.write_text("ssh-ed25519 AAAA test\n")
        for name, value in (("commit.gpgsign", "true"), ("gpg.format", "ssh"), ("user.signingkey", str(key))):
            git(self.repo, "config", name, value)
        context = run_hook("session-start", {"cwd": str(self.repo)})["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("Commit signing is not configured", context)

    def test_outside_repository_has_rules_only(self):
        output = run_hook("session-start", {"cwd": self.tmp.name})
        self.assertNotIn("Project root", output["hookSpecificOutput"]["additionalContext"])

    def test_subagent_event_name(self):
        output = run_hook("subagent-start", {"cwd": str(self.repo)})
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SubagentStart")

    def test_context_fits_the_documented_limit(self):
        output = run_hook("session-start", {"cwd": str(self.repo)})
        self.assertLess(len(output["hookSpecificOutput"]["additionalContext"]), 10_000)


class PromptTests(RepoTestCase):
    def test_request_is_logged_in_ignored_folder(self):
        run_hook("prompt", {"cwd": str(self.repo), "session_id": "s1", "prompt": "add a feature"})
        log = self.repo / ".agent-sessions" / "requests.jsonl"
        self.assertEqual(json.loads(log.read_text())["prompt"], "add a feature")
        status = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(status, "")

    def test_stop_word_adds_context(self):
        output = run_hook("prompt", {"cwd": str(self.repo), "prompt": "dur"})
        self.assertIn("STOP", output["hookSpecificOutput"]["additionalContext"])

    def test_ordinary_prompt_adds_nothing(self):
        # Negative control: a sentence containing "dur" is not a stop request.
        self.assertIsNone(run_hook("prompt", {"cwd": str(self.repo), "prompt": "durumu anlat"}))

    def test_outside_repository_logs_nothing(self):
        run_hook("prompt", {"cwd": self.tmp.name, "prompt": "hello"})
        self.assertFalse((Path(self.tmp.name) / ".agent-sessions").exists())


class GitRuleTests(RepoTestCase):
    def test_merge_pull_request_is_denied(self):
        self.assertEqual(self.bash("gh pr merge 12 --squash"), "deny")
        self.assertEqual(self.bash("gh api -X PUT repos/o/r/pulls/12/merge"), "deny")

    def test_push_to_main_is_denied(self):
        git(self.repo, "switch", "-q", "-c", "feat/x")
        self.assertEqual(self.bash("git push origin main"), "deny")
        self.assertEqual(self.bash("git push origin HEAD:refs/heads/main"), "deny")
        self.assertEqual(self.bash("git push --all"), "deny")

    def test_wildcard_push_covering_main_is_denied(self):
        git(self.repo, "switch", "-q", "-c", "feat/x")
        self.assertEqual(self.bash("git push origin 'refs/heads/*:refs/heads/*'"), "deny")
        self.assertEqual(self.bash("git push origin '+refs/heads/m*:refs/heads/m*'"), "deny")

    def test_wildcard_push_outside_main_is_allowed(self):
        # Negative control: a pattern that cannot match main or master.
        git(self.repo, "switch", "-q", "-c", "feat/x")
        self.assertIsNone(self.bash("git push origin 'refs/heads/feat/*:refs/heads/feat/*'"))

    def test_push_without_refspec_on_main_is_denied(self):
        self.assertEqual(self.bash("git push"), "deny")

    def test_push_topic_branch_is_allowed(self):
        # Negative control.
        git(self.repo, "switch", "-q", "-c", "feat/x")
        self.assertIsNone(self.bash("git push -u origin feat/x"))
        self.assertIsNone(self.bash("git push"))

    def test_merge_on_main_is_denied_but_on_topic_allowed(self):
        self.assertEqual(self.bash("git merge feat/x"), "deny")
        git(self.repo, "switch", "-q", "-c", "feat/x")
        self.assertIsNone(self.bash("git merge main"))

    def test_staged_secret_blocks_commit(self):
        token = "ghp_" + "A" * 36
        (self.repo / "config.txt").write_text(f"token={token}\n")
        git(self.repo, "add", "config.txt")
        output = run_hook("pre-tool", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": str(self.repo)})
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn(token, reason)

    def test_clean_commit_is_allowed(self):
        # Negative control.
        (self.repo / "notes.txt").write_text("nothing secret\n")
        git(self.repo, "add", "notes.txt")
        self.assertIsNone(self.bash("git add -A && git commit -m notes"))


    def test_head_and_at_on_main_are_denied(self):
        self.assertEqual(self.bash("git push origin HEAD"), "deny")
        self.assertEqual(self.bash("git push origin @"), "deny")
        self.assertEqual(self.bash("git push origin main&"), "deny")

    def test_head_on_topic_branch_is_allowed(self):
        # Negative control.
        git(self.repo, "switch", "-q", "-c", "feat/x")
        self.assertIsNone(self.bash("git push -u origin HEAD"))

    def test_other_repository_on_main_is_checked(self):
        other = Path(self.tmp.name) / "other"
        git(self.tmp.name, "clone", "-q", str(self.repo), str(other))
        git(self.repo, "switch", "-q", "-c", "feat/x")  # the session repository is on a topic branch
        self.assertEqual(self.bash(f"git -C {other} push"), "deny")
        self.assertEqual(self.bash(f"cd {other} && git push"), "deny")
        self.assertIsNone(self.bash("git push"))  # negative control: session repository

    def test_no_verify_and_override_variable_are_denied(self):
        git(self.repo, "switch", "-q", "-c", "feat/x")
        self.assertEqual(self.bash("git push --no-verify origin feat/x"), "deny")
        self.assertEqual(self.bash("git commit --no-verify -m x"), "deny")
        self.assertEqual(self.bash("CODERSKILL_ALLOW_PROTECTED_PUSH=1 git push origin main"), "deny")

    def test_switching_off_git_hooks_is_denied(self):
        for command in (
            "git -c core.hooksPath=/dev/null commit -m x",
            "git -ccore.hooksPath=/tmp push origin feat/x",
            "git --config-env=core.hooksPath=HOOKS commit -m x",
            "GIT_CONFIG_PARAMETERS=\"'core.hooksPath'='/dev/null'\" git commit -m x",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), "deny")
        # Negative control: other one-off settings stay allowed.
        self.assertIsNone(self.bash("git -c user.name=x -c commit.gpgsign=true log -1"))

    def test_commit_all_scans_unstaged_changes(self):
        (self.repo / "README.md").write_text("token=" + "ghp_" + "B" * 36 + "\n")
        self.assertEqual(self.bash("git commit -am update"), "deny")
        self.assertEqual(self.bash("git commit -m update README.md"), "deny")
        # Negative control: a plain commit takes only the (clean) index.
        self.assertIsNone(self.bash("git commit -m 'update docs'"))

    def test_merge_text_inside_a_heredoc_is_allowed(self):
        command = "cat > notes.md <<'EOF'\nRun gh pr merge 73 --squash when ready.\nEOF"
        self.assertIsNone(self.bash(command))
        self.assertEqual(self.bash("echo ok && gh pr merge 73 --squash"), "deny")


class HardwareRuleTests(RepoTestCase):
    def test_hardware_writes_ask(self):
        for command in (
            "sudo i2cset -y 1 0x50 0x00 0x01",
            "nvidia-smi -pl 200",
            "liquidctl set fan speed 50",
            "dd if=fw.bin of=/dev/sdb",
            "setpci -s 00:02.0 0x10.w=1",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), "ask")

    def test_wrapped_hardware_writes_ask(self):
        for command in (
            "sudo -u root i2cset -y 1 0x50 0 1",
            "sudo -E nvidia-smi -pl 100",
            "env -i PATH=/usr/bin i2cset -y 1 0x50 0 1",
            "bash -c 'i2cset -y 1 0x50 0 1'",
            "timeout 5 liquidctl set fan speed 40",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), "ask")
        self.assertIsNone(self.bash("bash -c 'echo hello'"))  # negative control

    def test_read_only_hardware_commands_pass(self):
        # Negative control: reads must not prompt.
        for command in ("i2cdetect -y 1", "nvidia-smi -q", "liquidctl status", "setpci -s 00:02.0 0x10.w", "dd if=/dev/sdb of=img.bin"):
            with self.subTest(command=command):
                self.assertIsNone(self.bash(command))


class NameRuleTests(RepoTestCase):
    def write(self, path):
        output = run_hook("pre-tool", {"tool_name": "Write", "tool_input": {"file_path": str(path)}, "cwd": str(self.repo)})
        return output["hookSpecificOutput"]["permissionDecision"] if output else None

    def test_bad_new_names_are_denied(self):
        self.assertEqual(self.write(self.repo / "my notes.md"), "deny")
        self.assertEqual(self.write(self.repo / "türkçe.md"), "deny")
        self.assertEqual(self.write(self.repo / "bad (copy)" / "file.md"), "deny")
        for name in ("notes+old.md", "release.", "CON.md", "nul", "com1.txt"):
            with self.subTest(name=name):
                self.assertEqual(self.write(self.repo / name), "deny")

    def test_good_and_framework_names_pass(self):
        # Negative control.
        for name in ("install-desktop-entry.sh", "js_browser.py", "README.md", "[id].tsx", "icon@2x.png"):
            with self.subTest(name=name):
                self.assertIsNone(self.write(self.repo / name))

    def test_existing_and_third_party_files_pass(self):
        (self.repo / "Old Name.md").write_text("x")
        self.assertIsNone(self.write(self.repo / "Old Name.md"))
        self.assertIsNone(self.write(self.repo / "node_modules" / "pkg" / "Weird Name.js"))


class StopTests(RepoTestCase):
    def stop(self, message, active=False):
        return run_hook("stop", {"cwd": str(self.repo), "session_id": "s", "last_assistant_message": message, "stop_hook_active": active})

    def test_unlabelled_hedge_blocks(self):
        self.assertEqual(self.stop("The fan is probably broken.")["decision"], "block")
        self.assertEqual(self.stop("Sorun muhtemelen sürücüde.")["decision"], "block")

    def test_labelled_or_quoted_hedges_pass(self):
        # Negative controls.
        self.assertIsNone(self.stop("⚠️ VARSAYIM: sorun muhtemelen sürücüde. Dayanak: log."))
        self.assertIsNone(self.stop("Do not write `probably` in reports."))
        self.assertIsNone(self.stop("The test passed (source: command output)."))

    def test_loop_guard(self):
        self.assertIsNone(self.stop("This is probably fine.", active=True))

    def test_record_reminder(self):
        run_hook("session-start", {"cwd": str(self.repo), "session_id": "s"})
        run_hook("prompt", {"cwd": str(self.repo), "session_id": "s", "prompt": "change it"})
        (self.repo / "README.md").write_text("changed\n")
        output = self.stop("Done (source: tests).")
        self.assertIn("requests.md", output["systemMessage"])
        private = self.repo / ".private"
        private.mkdir()
        (private / "requests.md").write_text("| 1 | change it | ✅ | README.md |\n")
        self.assertIsNone(self.stop("Done (source: tests)."))


    def test_changes_before_the_session_do_not_trigger_the_reminder(self):
        # Negative control for the reminder: the file was already modified before the session.
        (self.repo / "README.md").write_text("changed before\n")
        run_hook("session-start", {"cwd": str(self.repo), "session_id": "s2"})
        self.assertIsNone(self.stop("Answered a question (source: README.md)."))


class UntrustedRepositoryTests(RepoTestCase):
    """A cloned repository must not be able to redirect prompts or transcripts."""

    def setUp(self):
        super().setUp()
        self.transcript = Path(self.tmp.name) / "t1.jsonl"
        self.transcript.write_text('{"secret": "transcript"}\n')

    def run_session(self):
        run_hook("prompt", {"cwd": str(self.repo), "session_id": "s", "prompt": "my private prompt"})
        run_hook("session-end", {"cwd": str(self.repo), "transcript_path": str(self.transcript)})

    def tracked_text(self):
        return "".join(p.read_text(errors="replace") for p in self.repo.rglob("*")
                       if p.is_file() and ".git" not in p.parts and ".agent-sessions" not in p.parts)

    def commit_symlinks(self, links):
        folder = self.repo / ".agent-sessions"
        folder.mkdir(exist_ok=True)
        for name, target in links.items():
            (folder / name).symlink_to(target)
        git(self.repo, "add", "-f", ".agent-sessions")
        git(self.repo, "commit", "-q", "--no-verify", "-m", "attack")

    def test_symlinked_log_and_transcripts_are_not_followed(self):
        (self.repo / "docs").mkdir()
        self.commit_symlinks({"requests.jsonl": "../README.md", "transcripts": "../docs"})
        self.run_session()
        self.assertNotIn("my private prompt", self.tracked_text())
        self.assertEqual(list((self.repo / "docs").iterdir()), [])

    def test_symlinked_folder_is_not_used(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (self.repo / ".agent-sessions").symlink_to(outside)
        self.run_session()
        self.assertEqual(list(outside.iterdir()), [])

    def test_repository_that_unignores_the_folder_is_not_used(self):
        (self.repo / ".gitignore").write_text("!.agent-sessions/\n!.agent-sessions/**\n")
        (self.repo / ".agent-sessions").mkdir()
        (self.repo / ".agent-sessions" / ".gitignore").write_text("!*\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-q", "--no-verify", "-m", "unignore")
        self.run_session()
        status = git(self.repo, "status", "--porcelain", "--untracked-files=all").stdout
        self.assertNotIn("requests.jsonl", status)
        self.assertNotIn("t1.jsonl", status)

    def test_clean_repository_still_records(self):
        # Negative control: the safe path must keep working.
        self.run_session()
        folder = self.repo / ".agent-sessions"
        self.assertIn("my private prompt", (folder / "requests.jsonl").read_text())
        self.assertTrue((folder / "transcripts" / "claude-t1.jsonl").is_file())
        self.assertEqual(git(self.repo, "status", "--porcelain").stdout, "")


class SessionEndTests(RepoTestCase):
    def test_transcript_is_copied(self):
        transcript = Path(self.tmp.name) / "abc.jsonl"
        transcript.write_text('{"type":"user"}\n')
        run_hook("session-end", {"cwd": str(self.repo), "transcript_path": str(transcript)}, agent="codex")
        self.assertTrue((self.repo / ".agent-sessions" / "transcripts" / "codex-abc.jsonl").is_file())

    def test_malformed_input_never_fails(self):
        result = subprocess.run(["python3", "-I", str(HOOK), "stop"], input="not json", capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout), (0, ""))


class InstallerTests(unittest.TestCase):
    def test_install_is_idempotent_and_keeps_other_hooks(self):
        with tempfile.TemporaryDirectory() as home:
            settings = Path(home) / ".claude" / "settings.json"
            settings.parent.mkdir()
            other = {"matcher": "rate_limit", "hooks": [{"type": "command", "command": "other-hook"}]}
            settings.write_text(json.dumps({"model": "opus", "hooks": {"StopFailure": [other]}}))
            env = {"HOME": home, "PATH": "/usr/bin:/bin"}
            for _ in range(2):
                subprocess.run([str(ROOT / "scripts" / "install-hooks"), "claude"], env=env, check=True, capture_output=True)
            data = json.loads(settings.read_text())
            self.assertEqual(data["model"], "opus")
            self.assertEqual(data["hooks"]["StopFailure"], [other])
            self.assertEqual(len(data["hooks"]["PreToolUse"]), 1)
            self.assertEqual(data["hooks"]["PreToolUse"][0]["matcher"], "Bash|Write")
            backups = list(settings.parent.glob("settings.json.bak-*"))
            self.assertTrue(backups)
            self.assertNotIn("coderskill_hook", min(backups, key=lambda p: p.stat().st_mtime_ns).read_text())

    def test_installed_command_runs_from_copy_and_fails_safe(self):
        with tempfile.TemporaryDirectory() as home:
            env = {"HOME": home, "XDG_CONFIG_HOME": f"{home}/.config", "PATH": "/usr/bin:/bin"}
            subprocess.run([str(ROOT / "scripts" / "install-hooks"), "claude"], env=env, check=True, capture_output=True)
            settings = json.loads((Path(home) / ".claude" / "settings.json").read_text())
            command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            self.assertNotIn(str(ROOT), command)
            result = subprocess.run(["sh", "-c", command], input=json.dumps({"cwd": home}), env=env, capture_output=True, text=True)
            self.assertIn("CoderSkill rules", result.stdout)
            # Without the installed script the hook must exit 0, never 2 (which blocks tools).
            (Path(home) / ".config" / "coderskill" / "hooks" / "coderskill_hook.py").unlink()
            pre_tool = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
            result = subprocess.run(["sh", "-c", pre_tool], input="{}", env=env, capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as home:
            subprocess.run([str(ROOT / "scripts" / "install-hooks"), "codex", "--dry-run"], env={"HOME": home, "PATH": "/usr/bin:/bin"}, check=True, capture_output=True)
            self.assertFalse((Path(home) / ".codex").exists())


class GitHookTests(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config")}
        subprocess.run([str(ROOT / "scripts" / "install-hooks"), "git"], env=self.env, check=True, capture_output=True)

    def commit(self, *paths, message="x"):
        for path in paths:
            subprocess.run(["git", "-C", str(self.repo), "add", "-f", path], env=self.env, check=True)
        return subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", message], env=self.env, capture_output=True, text=True)

    def test_private_files_are_rejected(self):
        (self.repo / ".private").mkdir()
        (self.repo / ".private" / "plan.md").write_text("secret plan\n")
        result = self.commit(".private/plan.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".private/plan.md", result.stderr)

    def test_local_note_names_are_rejected(self):
        (self.repo / "PROJECT_TASKS.md").write_text("x\n")
        self.assertNotEqual(self.commit("PROJECT_TASKS.md").returncode, 0)

    def test_secret_is_rejected(self):
        (self.repo / "app.cfg").write_text("key=" + "sk-" + "a" * 30 + "\n")
        self.assertNotEqual(self.commit("app.cfg").returncode, 0)

    def test_ordinary_commit_passes(self):
        # Negative control.
        (self.repo / "app.py").write_text("print('hi')\n")
        result = self.commit("app.py")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_repository_hooks_still_run(self):
        hooks = self.repo / ".git" / "hooks"
        (hooks / "pre-commit").write_text("#!/bin/sh\necho repo-hook-ran >&2\nexit 1\n")
        (hooks / "pre-commit").chmod(0o755)
        (hooks / "commit-msg").write_text("#!/bin/sh\ntouch \"$(git rev-parse --git-dir)/commit-msg-ran\"\n")
        (hooks / "commit-msg").chmod(0o755)
        (self.repo / "a.txt").write_text("a\n")
        result = self.commit("a.txt")
        self.assertIn("repo-hook-ran", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        (hooks / "pre-commit").unlink()
        self.assertEqual(self.commit("a.txt").returncode, 0)
        self.assertTrue((self.repo / ".git" / "commit-msg-ran").exists())

    def test_global_ignore_covers_private_folders(self):
        (self.repo / ".private").mkdir()
        (self.repo / ".private" / "n.md").write_text("x")
        result = subprocess.run(["git", "-C", str(self.repo), "check-ignore", ".private/n.md"], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0)
        ignore = (self.home / ".config" / "git" / "ignore").read_text()
        subprocess.run([str(ROOT / "scripts" / "install-hooks"), "git"], env=self.env, check=True, capture_output=True)
        self.assertEqual((self.home / ".config" / "git" / "ignore").read_text(), ignore)  # idempotent

    def push(self, refspec, **env):
        remote = Path(self.tmp.name) / "remote.git"
        if not remote.exists():
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        return subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", refspec],
                              env={**self.env, **env}, capture_output=True, text=True)

    def test_push_to_main_is_refused_by_git(self):
        for refspec in ("main", "HEAD", "HEAD:refs/heads/main", "refs/heads/*:refs/heads/*"):
            with self.subTest(refspec=refspec):
                result = self.push(refspec)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("refusing to update refs/heads/main", result.stderr)

    def test_topic_branch_push_and_owner_override_pass(self):
        # Negative controls: a topic branch, and an explicit owner override.
        git(self.repo, "branch", "feat/x")
        self.assertEqual(self.push("feat/x").returncode, 0)
        self.assertEqual(self.push("main", CODERSKILL_ALLOW_PROTECTED_PUSH="1").returncode, 0)

    def test_repository_pre_push_hook_still_runs(self):
        hook = self.repo / ".git" / "hooks" / "pre-push"
        hook.write_text("#!/bin/sh\necho repo-pre-push-ran >&2\nexit 1\n")
        hook.chmod(0o755)
        git(self.repo, "branch", "feat/y")
        result = self.push("feat/y")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repo-pre-push-ran", result.stderr)

    def test_other_hooks_path_is_not_replaced_without_force(self):
        subprocess.run(["git", "config", "--global", "core.hooksPath", "/elsewhere"], env=self.env, check=True)
        result = subprocess.run([str(ROOT / "scripts" / "install-hooks"), "git"], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
