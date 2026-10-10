import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
LINK = re.compile(r"\]\(([^)\s]+)\)")


def documents():
    return [ROOT / "README.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").rglob("*.md"))]


def broken_links(path: Path) -> list[str]:
    broken = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue  # external URL or same-page anchor
        if not (path.parent / target.split("#", 1)[0]).exists():
            broken.append(target)
    return broken


class DocumentationTests(unittest.TestCase):
    def test_every_skill_has_a_page_and_a_row_in_the_map(self):
        index = (ROOT / "docs" / "skills" / "README.md").read_text(encoding="utf-8")
        for skill in sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()):
            self.assertTrue((ROOT / "docs" / "skills" / f"{skill}.md").is_file(), skill)
            self.assertIn(f"]({skill}.md)", index, skill)

    def test_relative_links_resolve(self):
        for path in documents():
            self.assertEqual(broken_links(path), [], path.relative_to(ROOT))

    def test_link_check_detects_a_broken_link(self):
        # Negative control: the checker must report a missing target.
        probe = ROOT / "docs" / "missing-link-probe.md"
        probe.write_text("[x](does-not-exist.md) [ok](README.md) [web](https://example.com)\n")
        try:
            self.assertEqual(broken_links(probe), ["does-not-exist.md"])
        finally:
            probe.unlink()


if __name__ == "__main__":
    unittest.main()
