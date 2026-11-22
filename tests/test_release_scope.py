"""Release scope: every tracked file must be listed in docs/SHIPS_WITH.md with purpose, origin and rights."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def listed():
    rows = re.findall(r"^\| `([^`]+)` \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", (ROOT / "docs/SHIPS_WITH.md").read_text(encoding="utf-8"), re.M)
    return {path: (purpose.strip(), origin.strip(), rights.strip()) for path, purpose, origin, rights in rows}


def tracked():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None  # a ZIP download has no git: nothing to check
    return set(out.split())


class ReleaseScope(unittest.TestCase):
    def test_every_tracked_file_is_listed(self):
        files = tracked()
        if files is None:
            self.skipTest("not a git checkout")
        unlisted = sorted(files - set(listed()))
        self.assertEqual(unlisted, [], "add these to docs/SHIPS_WITH.md (purpose, origin, rights) or leave them out of the release")

    def test_every_listed_file_exists_and_has_origin_and_rights(self):
        for path, (purpose, origin, rights) in listed().items():
            self.assertTrue((ROOT / path).exists(), path)
            self.assertTrue(purpose and origin and rights, path)


if __name__ == "__main__":
    unittest.main()
