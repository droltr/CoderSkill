import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import identity_gate  # noqa: E402


class IdentityGateTests(unittest.TestCase):
    NOW = {"account": "droltr", "repository": "droltr/example", "origin": "https://github.com/droltr/example.git"}

    def test_missing_record(self):
        self.assertEqual(identity_gate.compare(None, self.NOW), ("missing", []))

    def test_matching_record(self):
        self.assertEqual(identity_gate.compare(dict(self.NOW, confirmed_at="x"), self.NOW), ("match", []))

    def test_changed_account_or_remote_is_a_mismatch(self):
        record = dict(self.NOW, account="someone-else")
        self.assertEqual(identity_gate.compare(record, self.NOW), ("mismatch", ["account"]))
        record = dict(self.NOW, origin="https://github.com/other/example.git", repository="other/example")
        self.assertEqual(identity_gate.compare(record, self.NOW)[0], "mismatch")

    def test_origin_parsing_strips_credentials_and_suffix(self):
        self.assertEqual(identity_gate.origin_repository("https://github.com/droltr/CoderSkill.git"), "droltr/CoderSkill")
        self.assertEqual(identity_gate.origin_repository("git@github.com:droltr/CoderSkill.git"), "droltr/CoderSkill")
        self.assertEqual(identity_gate.origin_repository("https://example.com/a/b"), "")


class ProfileVisibilityTests(unittest.TestCase):
    def validate(self, text):
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as handle:
            handle.write(text)
        result = subprocess.run([str(ROOT / "scripts" / "validate-project-profile"), handle.name], capture_output=True, text=True)
        Path(handle.name).unlink()
        return json.loads(result.stdout)

    def test_invalid_visibility_is_rejected(self):
        base = (ROOT / ".coderskill" / "project.yml.example").read_text()
        self.assertEqual(self.validate(base)["status"], "valid")  # negative control
        self.assertEqual(self.validate(base.replace("visibility: private", "visibility: internal"))["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
