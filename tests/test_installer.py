import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_adapters import digest_tree  # noqa: E402
CLI = ROOT / "scripts" / "coderskill"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.env = {**os.environ, "HOME": str(self.home)}
        self.skill = self.home / ".claude" / "skills" / "professional-coding" / "SKILL.md"

    def install(self, *args):
        # The working-tree path tests the copy rules offline; tests/test_update_channel.py covers signed main.
        return subprocess.run([str(CLI), "install", "--worktree", "--agents", "claude", *args], env=self.env,
                              capture_output=True, text=True)

    def edit(self, text):
        self.skill.chmod(0o644)  # installed files are read-only; a user edit makes them writable first
        self.skill.write_text(text)

    def test_installs_only_the_selected_agent(self):
        self.assertEqual(self.install().returncode, 0)
        self.assertTrue(self.skill.is_file())
        self.assertFalse((self.home / ".codex").exists())
        receipt = json.loads((self.home / ".claude" / "skills" / ".coderskill-installed.json").read_text())
        self.assertIn("professional-coding", receipt)

    def test_update_replaces_unchanged_copies(self):
        self.install()
        self.edit("old version from an earlier install\n")
        receipt_path = self.home / ".claude" / "skills" / ".coderskill-installed.json"
        receipt = json.loads(receipt_path.read_text())
        # Simulate an earlier installation of that old content.
        receipt["professional-coding"] = digest_tree(self.skill.parent)
        receipt_path.write_text(json.dumps(receipt))
        self.assertEqual(self.install("--update").returncode, 0)
        self.assertNotIn("old version", self.skill.read_text())

    def test_update_stops_on_local_changes_and_force_keeps_a_backup(self):
        self.install()
        self.edit(self.skill.read_text() + "\nmy local note\n")
        result = self.install("--update")
        self.assertEqual(result.returncode, 3)
        self.assertIn("my local note", self.skill.read_text())  # nothing lost
        self.assertEqual(self.install("--update", "--force").returncode, 0)
        self.assertNotIn("my local note", self.skill.read_text())
        # Backups go outside the skills folder, so the agent never loads them as skills.
        self.assertEqual(list(self.skill.parent.parent.glob("*.backup-*")), [])
        backups = list((self.home / ".local/share/coderskill/backups/claude").glob("professional-coding.backup-*"))
        self.assertTrue(backups and "my local note" in (backups[0] / "SKILL.md").read_text())

    def test_installed_files_are_read_only(self):
        self.install()
        self.assertFalse(self.skill.stat().st_mode & 0o222)

    def test_removed_skill_is_uninstalled_unless_changed(self):
        self.install()
        receipt_path = self.home / ".claude" / "skills" / ".coderskill-installed.json"
        old = self.home / ".claude" / "skills" / "retired-skill"
        old.mkdir()
        (old / "SKILL.md").write_text("old\n")
        receipt = json.loads(receipt_path.read_text())
        receipt["retired-skill"] = digest_tree(old)
        receipt_path.write_text(json.dumps(receipt))
        self.install("--update")
        self.assertFalse(old.exists())
        # Negative control: a skill that was never installed by CoderSkill stays.
        own = self.home / ".claude" / "skills" / "my-own-skill"
        own.mkdir()
        (own / "SKILL.md").write_text("mine\n")
        self.install("--update")
        self.assertTrue(own.exists())

    def test_command_runs_from_a_copy(self):
        self.install()
        link = self.home / ".local" / "bin" / "coderskill"
        self.assertTrue(link.is_symlink())
        self.assertNotIn(str(ROOT), str(link.resolve()))


if __name__ == "__main__":
    unittest.main()
