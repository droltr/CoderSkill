import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
AUDIT = ROOT / "scripts" / "security-audit"


def audit(root, *args):
    result = subprocess.run([str(AUDIT), "--root", str(root), *args], capture_output=True, text=True)
    return {(f["category"], f["path"]) for f in json.loads(result.stdout)["findings"]}


class SecurityAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".gitignore").write_text(".private/\n")

    def test_ignored_files_are_skipped_unless_requested(self):
        (self.root / ".private").mkdir()
        (self.root / ".private" / "notes.md").write_text("host " + ".".join(["10", "0", "0", "5"]) + "\n")
        self.assertEqual(audit(self.root), set())
        self.assertIn(("ipv4-address", ".private/notes.md"), audit(self.root, "--all-files"))

    def test_personal_email_and_home_path_are_found(self):
        # Built at run time so that the repository audit does not flag this test file.
        (self.root / "README.md").write_text("contact jane.doe" + "@" + "gmail.com\nlog at /" + "home/jane/project\n")
        found = audit(self.root)
        self.assertIn(("email-address", "README.md"), found)
        self.assertIn(("home-path", "README.md"), found)

    def test_placeholders_are_not_findings(self):
        # Negative control: documentation addresses, SSH remotes and generic paths.
        (self.root / "README.md").write_text(
            "dev@example.com 1+droltr@users.noreply.github.com git@github.com:owner/repo.git\n"
            "/home/user/project /home/<user>/x icon@2x.png\n"
        )
        self.assertEqual(audit(self.root), set())

    def test_secret_is_found_in_untracked_publishable_file(self):
        (self.root / "config.txt").write_text("token=" + "ghp_" + "C" * 36 + "\n")
        self.assertIn(("secret", "config.txt"), audit(self.root))


if __name__ == "__main__":
    unittest.main()
