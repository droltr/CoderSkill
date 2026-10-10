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
        return subprocess.run([str(CLI), "install", "--agents", "claude", *args], env=self.env, capture_output=True, text=True)

    def test_installs_only_the_selected_agent(self):
        self.assertEqual(self.install().returncode, 0)
        self.assertTrue(self.skill.is_file())
        self.assertFalse((self.home / ".codex").exists())
        receipt = json.loads((self.home / ".claude" / "skills" / ".coderskill-installed.json").read_text())
        self.assertIn("professional-coding", receipt)

    def test_update_replaces_unchanged_copies(self):
        self.install()
        self.skill.write_text("old version from an earlier install\n")
        receipt_path = self.home / ".claude" / "skills" / ".coderskill-installed.json"
        receipt = json.loads(receipt_path.read_text())
        # Simulate an earlier installation of that old content.
        receipt["professional-coding"] = digest_tree(self.skill.parent)
        receipt_path.write_text(json.dumps(receipt))
        self.assertEqual(self.install("--update").returncode, 0)
        self.assertNotIn("old version", self.skill.read_text())

    def test_update_stops_on_local_changes_and_force_keeps_a_backup(self):
        self.install()
        self.skill.write_text(self.skill.read_text() + "\nmy local note\n")
        result = self.install("--update")
        self.assertEqual(result.returncode, 3)
        self.assertIn("my local note", self.skill.read_text())  # nothing lost
        self.assertEqual(self.install("--update", "--force").returncode, 0)
        self.assertNotIn("my local note", self.skill.read_text())
        backups = list(self.skill.parent.parent.glob("professional-coding.backup-*"))
        self.assertTrue(backups and "my local note" in (backups[0] / "SKILL.md").read_text())

    def test_command_runs_from_a_copy(self):
        self.install()
        link = self.home / ".local" / "bin" / "coderskill"
        self.assertTrue(link.is_symlink())
        self.assertNotIn(str(ROOT), str(link.resolve()))


if __name__ == "__main__":
    unittest.main()
