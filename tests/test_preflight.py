import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preflight  # noqa: E402


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                    "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args], check=True, capture_output=True)


class PreflightScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "a.txt").write_text("clean\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "init")
        self.cwd = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, self.cwd)

    def test_history_finds_a_secret_removed_from_the_tree(self):
        (self.repo / "b.txt").write_text("token=" + "ghp_" + "D" * 36 + "\n")
        git(self.repo, "add", "b.txt")
        git(self.repo, "commit", "-q", "-m", "add")
        git(self.repo, "rm", "-q", "b.txt")
        git(self.repo, "commit", "-q", "-m", "remove")
        self.assertEqual(preflight.audit_check("history", "main")["returncode"], 1)
        self.assertEqual(preflight.audit_check("branch", "main")["returncode"], 0)

    def test_clean_history_passes(self):
        # Negative control.
        self.assertEqual(preflight.audit_check("history", "main")["returncode"], 0)

    def test_scopes_select_different_files(self):
        git(self.repo, "switch", "-q", "-c", "topic")
        (self.repo / "c.txt").write_text("x\n")
        git(self.repo, "add", "c.txt")
        git(self.repo, "commit", "-q", "-m", "c")
        (self.repo / "d.txt").write_text("y\n")
        git(self.repo, "add", "d.txt")
        self.assertEqual(preflight.scope_files("branch", "main"), ["c.txt"])
        self.assertEqual(preflight.scope_files("staged", "main"), ["d.txt"])


if __name__ == "__main__":
    unittest.main()
