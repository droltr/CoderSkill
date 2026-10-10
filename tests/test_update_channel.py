import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_channel as uc  # noqa: E402

GITHUB = "968479A1AFF927E37D1A566BB5690EEEBB952194"


def git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True, env=env)


class TrustedOutputTests(unittest.TestCase):
    def test_pinned_github_key_is_trusted(self):
        line = f"[GNUPG:] VALIDSIG {GITHUB} 2026-10-10 1 0 4 0 1 8 00 {GITHUB}"
        self.assertTrue(uc.trusted_output(line))

    def test_other_gpg_key_and_unknown_ssh_key_are_not(self):
        # Negative controls: a valid signature from another key, and an SSH key with no principal.
        self.assertFalse(uc.trusted_output("[GNUPG:] VALIDSIG " + "A" * 40 + " 2026-10-10 1 0 4 0 1 8 00 " + "A" * 40))
        self.assertFalse(uc.trusted_output('Good "git" signature with ED25519 key SHA256:x\nNo principal matched.'))
        self.assertFalse(uc.trusted_output(""))

    def test_importance(self):
        self.assertTrue(uc.is_important(["hooks/coderskill_hook.py"]))
        self.assertTrue(uc.is_important(["skills/professional-coding/SKILL.md"]))
        self.assertTrue(uc.is_important(None))  # unknown installed version
        self.assertFalse(uc.is_important(["README.md", "tests/test_hooks.py", "skills/x/references/y.md"]))


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.home = base / "home"
        (self.home / ".claude" / "skills").mkdir(parents=True)
        state, config = base / "state", base / "config"
        saved = {name: getattr(uc, name) for name in
                 ("SOURCE_FILE", "TRUST_DIR", "LATEST_FILE", "FETCH_STAMP", "LOCK_FILE", "SESSIONS_DIR")}
        self.addCleanup(lambda: [setattr(uc, k, v) for k, v in saved.items()])
        uc.SOURCE_FILE, uc.TRUST_DIR = config / "source.json", config / "trust" / "gnupg"
        uc.LATEST_FILE, uc.FETCH_STAMP = state / "latest.json", state / "last-fetch"
        uc.LOCK_FILE, uc.SESSIONS_DIR = state / "install.lock", state / "sessions"
        # Signing key and allowed signers for this test only.
        key = base / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        other = base / "other"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other)], check=True)
        signers = base / "allowed_signers"
        signers.write_text("test@example.invalid " + (base / "key.pub").read_text())
        gitconfig = base / "gitconfig"
        gitconfig.write_text(f"[gpg \"ssh\"]\n\tallowedSignersFile = {signers}\n[user]\n\tname = Test\n\temail = test@example.invalid\n")
        previous = os.environ.get("GIT_CONFIG_GLOBAL")
        os.environ["GIT_CONFIG_GLOBAL"] = str(gitconfig)
        self.addCleanup(lambda: os.environ.__setitem__("GIT_CONFIG_GLOBAL", previous) if previous
                        else os.environ.pop("GIT_CONFIG_GLOBAL", None))
        self.key, self.other = key, other
        # Source clone with an origin, like a real CoderSkill checkout.
        self.origin = base / "origin.git"
        work = base / "work"
        work.mkdir()
        git(work, "init", "-q", "-b", "main")
        self.work = work
        self.commit("skills/demo/SKILL.md", "v1\n", sign=self.key)
        git(base, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(work, "remote", "add", "origin", str(self.origin))
        git(work, "push", "-q", "origin", "main")
        self.clone = base / "clone"
        git(base, "clone", "-q", str(self.origin), str(self.clone))
        uc.record_source(self.clone)

    def commit(self, path, text, sign=None):
        target = self.work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        git(self.work, "add", path)
        options = ["-c", "gpg.format=ssh", "-c", f"user.signingkey={sign}", "commit", "-q", "-S", "-m", path] if sign \
            else ["commit", "-q", "--no-gpg-sign", "-m", path]
        git(self.work, *options)
        return git(self.work, "rev-parse", "HEAD").stdout.strip()

    def publish(self, path, text, sign=None):
        commit = self.commit(path, text, sign)
        git(self.work, "push", "-q", "origin", "main")
        return commit

    def install_receipt(self, commit):
        receipt = self.home / ".claude" / "skills" / uc.RECEIPT
        receipt.write_text(json.dumps({"demo": "x", uc.SOURCE_COMMIT: commit}))

    def test_signature_checks(self):
        signed = git(self.clone, "rev-parse", "origin/main").stdout.strip()
        self.assertTrue(uc.signature_ok(self.clone, signed))
        unsigned = self.publish("README.md", "x\n")
        other = self.publish("README.md", "y\n", sign=self.other)
        git(self.clone, "fetch", "-q", "origin")
        # Negative controls: no signature, and a signature from a key that is not an allowed signer.
        self.assertFalse(uc.signature_ok(self.clone, unsigned))
        self.assertFalse(uc.signature_ok(self.clone, other))

    def test_status_reports_outdated_and_untrusted(self):
        first = git(self.clone, "rev-parse", "origin/main").stdout.strip()
        self.install_receipt(first)
        self.assertEqual(uc.status("claude", home=self.home)["state"], "current")
        self.publish("README.md", "docs\n", sign=self.key)
        uc.FETCH_STAMP.unlink()  # the fetch interval would otherwise skip this fetch
        result = uc.status("claude", home=self.home)
        self.assertEqual(result["state"], "outdated")
        self.assertFalse(result["important"])
        # An unsigned commit anywhere in the range blocks the update, even under a signed tip.
        self.publish("hooks/x.py", "1\n")
        self.publish("skills/demo/SKILL.md", "v2\n", sign=self.key)
        uc.FETCH_STAMP.unlink()
        result = uc.status("claude", home=self.home)
        self.assertEqual(result["state"], "untrusted")
        self.assertEqual(len(result["unsigned"]), 1)

    def test_fetch_is_rate_limited(self):
        self.assertTrue(uc.fetch(self.clone))
        self.assertIsNone(uc.fetch(self.clone))
        self.assertTrue(uc.fetch(self.clone, force=True))

    def test_session_notice_once_per_change(self):
        first = git(self.clone, "rev-parse", "origin/main").stdout.strip()
        self.install_receipt(first)
        uc.remember_session("s1", "claude", home=self.home)
        self.assertIsNone(uc.session_notice("s1", "claude", home=self.home))  # negative control
        newer = self.publish("skills/demo/SKILL.md", "v2\n", sign=self.key)
        uc.status("claude", home=self.home)  # a session start elsewhere fetched main
        notice = uc.session_notice("s1", "claude", home=self.home)
        self.assertIn("important CoderSkill update", notice)
        self.assertIsNone(uc.session_notice("s1", "claude", home=self.home))
        self.install_receipt(newer)  # another session installed it
        self.assertIn("were updated during this session", uc.session_notice("s1", "claude", home=self.home))
        self.assertIsNone(uc.session_notice("s1", "claude", home=self.home))

    def test_snapshot_has_only_committed_files(self):
        (self.clone / "skills" / "demo" / "SKILL.md").write_text("uncommitted edit\n")
        (self.clone / "untracked.txt").write_text("x")
        out = Path(self.tmp.name) / "snapshot"
        commit = git(self.clone, "rev-parse", "origin/main").stdout.strip()
        uc.export_snapshot(self.clone, commit, out)
        self.assertEqual((out / "skills" / "demo" / "SKILL.md").read_text(), "v1\n")
        self.assertFalse((out / "untracked.txt").exists())

    def test_change_request_goes_to_the_local_queue(self):
        import coderskill
        self.assertEqual(coderskill.request("Clarify: the stop rule!", "Why it is needed.", "codex"), 0)
        files = list((self.clone / ".private" / "change-requests").glob("*-clarify-the-stop-rule.md"))
        self.assertEqual(len(files), 1)
        self.assertIn("Agent: codex", files[0].read_text())
        self.assertNotIn("change-requests", git(self.clone, "ls-files").stdout)  # local only, not tracked


if __name__ == "__main__":
    unittest.main()
