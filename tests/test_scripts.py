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


if __name__ == "__main__":
    unittest.main()
