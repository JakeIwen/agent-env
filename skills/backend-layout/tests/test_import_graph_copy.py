"""The skill's copies of consolidate's import_graph.py and cochange.py match consolidate's files,
so the installer ships the resolver consolidate owns. Skill-only: not copied into repos."""
import hashlib
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CONSOLIDATE = SKILL.parent / "consolidate"


class MirroredFromConsolidate(unittest.TestCase):
    def test_copies_match_consolidate(self):
        for name in ("import_graph.py", "cochange.py"):
            ours = SKILL / "checks" / "backend_layout" / name
            theirs = CONSOLIDATE / name
            self.assertTrue(theirs.is_file(), f"consolidate is not installed beside this skill: {theirs}")
            self.assertEqual(hashlib.sha256(ours.read_bytes()).hexdigest(),
                             hashlib.sha256(theirs.read_bytes()).hexdigest(),
                             f"{name} differs from consolidate's; copy {theirs} over {ours}")
