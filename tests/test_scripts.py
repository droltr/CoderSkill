import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class ScriptValidationTests(unittest.TestCase):
    def run_script(self, name, argument):
        result = subprocess.run(
            [str(ROOT / "scripts" / name), str(ROOT / argument)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, json.loads(result.stdout)

    def test_project_profile_example(self):
        code, output = self.run_script("validate-project-profile", ".coderskill/project.yml.example")
        self.assertEqual(code, 0)
        self.assertEqual(output["status"], "valid")

    def test_lesson_example(self):
        code, output = self.run_script("validate-lesson", "knowledge/lesson.example.yml")
        self.assertEqual(code, 0)
        self.assertEqual(output["status"], "valid")


class LessonValidatorTests(unittest.TestCase):
    def validate(self, text):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as handle:
            handle.write(text)
        result = subprocess.run([str(ROOT / "scripts" / "validate-lesson"), handle.name], capture_output=True, text=True)
        Path(handle.name).unlink()
        return json.loads(result.stdout)["status"]

    def test_rule_about_tokens_is_allowed_but_a_token_value_is_not(self):
        base = (ROOT / "knowledge" / "lesson.example.yml").read_text()
        self.assertEqual(self.validate(base.replace("State the durable rule in clear English.", "Never commit tokens or secrets.")), "valid")
        self.assertEqual(self.validate(base.replace("State the durable rule in clear English.", "token: abcdef123456")), "invalid")
        self.assertEqual(self.validate(base.replace("State the durable rule in clear English.", "See /" + "home/alice/x")), "invalid")


class ProfileValidatorTests(unittest.TestCase):
    def validate(self, text):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as handle:
            handle.write(text)
        result = subprocess.run([str(ROOT / "scripts" / "validate-project-profile"), handle.name], capture_output=True, text=True)
        Path(handle.name).unlink()
        return json.loads(result.stdout)["status"]

    def test_old_language_fields_are_ignored(self):
        base = (ROOT / ".coderskill" / "project.yml.example").read_text()
        self.assertEqual(self.validate(base + "user_communication_language: en\nsystem_language_suggestion: auto\n"), "valid")
        # Negative control: the validator still rejects a broken profile.
        self.assertEqual(self.validate(base.replace("artifact_language: english", "artifact_language: turkish")), "invalid")


class AdapterBuilderTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\n---\n")

    def build(self, *args):
        return subprocess.run([str(ROOT / "scripts" / "build-adapters"), "--root", str(self.root), *args], capture_output=True, text=True)

    def test_stale_adapter_file_is_detected_and_removed(self):
        self.build()
        self.assertEqual(self.build("--check").returncode, 0)  # negative control
        stale = self.root / ".claude" / "skills" / "demo" / "old.md"
        stale.write_text("old")
        result = self.build("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("(stale)", result.stdout)
        self.build()
        self.assertFalse(stale.exists())

    def test_manifest_drift_is_detected(self):
        self.build()
        manifest = self.root / "adapters" / "manifest.json"
        data = json.loads(manifest.read_text())
        data["skills"]["demo"] = "0" * 64
        manifest.write_text(json.dumps(data))
        self.assertEqual(self.build("--check").returncode, 1)


if __name__ == "__main__":
    unittest.main()
