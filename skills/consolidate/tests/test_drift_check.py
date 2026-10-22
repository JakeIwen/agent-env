"""drift_check.py behavior through its CLI and the advisory metric modules, on temp git repos.
Run from the skill directory: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import cochange
import css_metrics
import import_graph

CHECK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "drift_check.py")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null"]


class Repo:
    def __init__(self, root):
        self.root = root
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.run(GIT + ["-C", self.root, *args], capture_output=True, text=True, check=True).stdout

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def run(self, *args):
        r = subprocess.run([sys.executable, CHECK, *args, "--repo", self.root], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    @property
    def baseline_path(self):
        return os.path.join(self.root, ".codeshape", "baseline.json")

    def baseline(self):
        with open(self.baseline_path, encoding="utf-8") as fh:
            return json.load(fh)

    def downgrade_baseline(self):
        """Rewrite the baseline as an older checker wrote it: no coverage, no stylesheets, no new markers."""
        base = self.baseline()
        base.pop("coverage", None)
        base["files"] = {p: n for p, n in base["files"].items() if not p.endswith((".css", ".scss", ".sass", ".less"))}
        base["markers"].pop("important", None)
        with open(self.baseline_path, "w", encoding="utf-8") as fh:
            json.dump(base, fh)
        self.commit("old baseline")


def lines(n, line="a { margin: 0; }"):
    return "\n".join([line] * n) + "\n"


class RatchetCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(self.tmp.name)
        self.repo.write("app.py", "def f():\n    return 1\n")
        self.repo.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def old_baseline_then(self, rel, text):
        self.repo.run("rebaseline")
        self.repo.downgrade_baseline()
        self.repo.write(rel, text)
        self.repo.commit()

    def test_big_stylesheet_against_old_baseline_is_advisory(self):
        self.old_baseline_then("web/big.css", lines(900))
        code, out = self.repo.run("ratchet")
        self.assertEqual(code, 0, out)
        self.assertNotIn("WORSE", out)
        self.assertIn("not ratcheted until rebaseline", out)
        code, out = self.repo.run("check")
        self.assertIn("rebaseline would grandfather", out)
        self.assertIn("web/big.css", out)

    def test_after_rebaseline_stylesheet_is_ratcheted_and_growth_fails(self):
        self.old_baseline_then("web/big.css", lines(900))
        self.repo.run("rebaseline")
        self.repo.commit("new baseline")
        self.assertEqual(self.repo.run("ratchet")[0], 0)
        self.repo.write("web/big.css", lines(901))
        code, out = self.repo.run("ratchet")
        self.assertEqual(code, 1, out)
        self.assertIn("WORSE  web/big.css: already over 800 lines and grew (900 -> 901)", out)
        self.assertNotIn("not ratcheted until rebaseline", out)

    def test_new_marker_key_against_old_baseline_is_advisory_then_ratcheted(self):
        self.old_baseline_then("web/a.css", "a { color: var(--x) !important; }\n")
        code, out = self.repo.run("ratchet")
        self.assertEqual(code, 0, out)
        self.assertIn("marker important=1", out)
        self.repo.run("rebaseline")
        self.repo.commit("new baseline")
        self.repo.write("web/a.css", "a { color: var(--x) !important; }\nb { margin: 0 ! important; }\n")
        code, out = self.repo.run("ratchet")
        self.assertEqual(code, 1, out)
        self.assertIn("WORSE  marker important: 1 -> 2", out)

    def test_allow_marker_in_css_comment_excuses_important(self):
        self.repo.write("web/a.css", "a { margin: 0 !important; } /* codeshape: allow-marker print reset */\n"
                                     "b { margin: 0 !important; }\n")
        out_json = os.path.join(self.tmp.name, "metrics.json")
        self.repo.run("check", "--json-out", out_json)
        with open(out_json, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["markers"]["important"], 1)

    def test_every_marker_is_counted(self):
        self.repo.write("tool.py", "import sys\nsys.path.insert(0, 'x')\nif __package__:\n    pass\n"
                                   "x = 1  # type: ignore\ny = 2  # noqa\ntry:\n    pass\nexcept:\n    pass\n")
        self.repo.write("web/a.ts", "const a = b as any; // eslint-disable-line\n// @ts-expect-error\nlet c: any;\n")
        self.repo.write("web/a.css", "a { margin: 0 !IMPORTANT; }\n")
        out_json = os.path.join(self.tmp.name, "metrics.json")
        self.repo.run("check", "--json-out", out_json)
        with open(out_json, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["markers"], {"sys_path_hack": 1, "dual_import_guard": 1, "ts_any": 2,
                                                        "type_ignore": 2, "lint_disable": 2, "bare_except": 1,
                                                        "important": 1})

    def test_rebaseline_keeps_format_readable_by_older_checkers(self):
        self.repo.write("web/a.css", lines(3))
        self.repo.commit()
        self.repo.run("rebaseline")
        base = self.repo.baseline()
        self.assertEqual(base["version"], 2)
        self.assertEqual(set(base["limits"]), {"file_lines", "func_lines", "enforce_tests"})
        self.assertIn(".css", base["coverage"]["extensions"])
        self.assertIn("important", base["coverage"]["markers"])
        self.assertNotIn("organization", base["advisory"])

    def test_rebaseline_keeps_the_layout_key_backend_layout_writes(self):
        self.repo.run("rebaseline")
        base = self.repo.baseline()
        base["layout"] = {"date": "2026-10-21", "head": "", "findings": {"prefix-group": ["tools/radar_a.py"]}}
        with open(self.repo.baseline_path, "w", encoding="utf-8") as fh:
            json.dump(base, fh)
        self.repo.commit("layout baseline")
        self.repo.run("rebaseline")
        self.assertEqual(self.repo.baseline()["layout"], base["layout"])

    def test_no_baseline_counts_stylesheets(self):
        self.repo.write("web/big.css", lines(900))
        code, out = self.repo.run("ratchet")
        self.assertEqual(code, 1, out)
        self.assertIn("web/big.css: new file is 900 lines", out)

    def test_ratchet_output_has_no_advisory_section(self):
        self.repo.write("web/a.css", "a { color: #fff; }\n")
        self.repo.write("web/b.css", "a.x { color: red; }\n")
        self.repo.commit()
        code, out = self.repo.run("ratchet")
        self.assertEqual(code, 0, out)
        self.assertNotIn("advisory", out)
        code, out = self.repo.run("check")
        self.assertIn("advisory, color literals", out)
        self.assertIn("advisory, files in different top-level folders", out)


class StylesheetMetricTests(unittest.TestCase):
    def collect(self, files):
        with tempfile.TemporaryDirectory() as root:
            for rel, text in files.items():
                os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
                with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
                    fh.write(text)
            return css_metrics.collect(root, list(files))

    def test_color_literals_outside_palette(self):
        out = self.collect({
            "styles/palette.css": ":root { --accent: #ff0000; --bg: white; }\n",
            "app/card.css": (
                "#main .card:hover, .fade { color: #fff; background: rgb(1 2 3); border-color: red; }\n"
                ".a { color: var(--red); background: url('#fff.png'); box-shadow: 0 0 1px rgb(var(--x) / .5); }\n"
                "/* color: blue */ .b { content: 'tomato'; }\n"),
            "app/vars.scss": "$brand: #123456;\n.c { color: $brand; border: 1px solid #abc; }\n",
        })
        self.assertEqual(out["palette_files"], ["styles/palette.css"])
        self.assertEqual(out["color_literals"]["app/card.css"]["count"], 3)
        self.assertEqual(out["color_literals"]["app/vars.scss"]["count"], 1)

    def test_duplicate_selectors_same_context_only(self):
        out = self.collect({
            "a.css": ".card { margin: 0; }\n@media (max-width: 600px) { .row { margin: 0; } }\nbody { margin: 0; }\n",
            "b.css": ".card, .other { padding: 0; }\n.row { margin: 1px; }\nbody { margin: 0; }\n"
                     ".nest { .card { margin: 0; } }\n@keyframes k { from { opacity: 0; } }\n",
        })
        self.assertEqual(out["duplicate_selectors"], [{"context": "", "selector": ".card", "files": ["a.css", "b.css"]}])


class ImportGraphTests(unittest.TestCase):
    def collect(self, files, tests=()):
        with tempfile.TemporaryDirectory() as root:
            for rel, text in files.items():
                os.makedirs(os.path.dirname(os.path.join(root, rel)) or root, exist_ok=True)
                with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
                    fh.write(text)
            return import_graph.collect(root, list(files), set(tests))

    def test_python_cycle_module_level_only(self):
        out = self.collect({
            "pkg/__init__.py": "",
            "pkg/a.py": "from . import b\n",
            "pkg/b.py": "from pkg.a import thing\n",
            "pkg/c.py": "import pkg.a\n",
            "pkg/d.py": "def late():\n    from . import c\n",
            "pkg/e.py": "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from . import c\n",
        })
        self.assertEqual(out["python_cycles"], [["pkg/a.py", "pkg/b.py"]])

    def test_js_cycle_relative_value_imports_only(self):
        out = self.collect({
            "src/x.ts": "import { y } from './y.js'\nexport const x = 1\n",
            "src/y.ts": "import { x } from \"./x\";\nexport const y = 2;\n",
            "src/t.ts": "import type { x } from './x'\nexport const t = 1\n",
            "src/u.ts": "import { t } from './t'\nimport { type x } from './x'\n",
            "src/v.tsx": "import { z } from '@/alias'\nimport React from 'react'\n",
        })
        self.assertEqual(out["js_cycles"], [["src/x.ts", "src/y.ts"]])

    def test_grab_bag_disjoint_importer_groups(self):
        out = self.collect({
            "src/util.ts": "export const f1 = 1, f2 = 2, f3 = 3\n",
            "src/a.ts": "import { f1, f2 } from './util'\n",
            "src/b.ts": "import {\n  f3,\n} from './util'\n",
            "src/util.test.ts": "import { f1, f3 } from './util'\n",
            "src/ns.ts": "export const g1 = 1, g2 = 2, g3 = 3\n",
            "src/c.ts": "import { g1 } from './ns'\n",
            "src/d.ts": "import * as ns from './ns'\nimport { g2, g3 } from './ns'\n",
        }, tests={"src/util.test.ts"})
        self.assertEqual(out["grab_bags"], [{"module": "src/util.ts", "groups": [
            {"names": ["f1", "f2"], "importers": ["src/a.ts"]}, {"names": ["f3"], "importers": ["src/b.ts"]}]}])


class CochangeTests(unittest.TestCase):
    def test_pairs_across_folders_skip_large_commits_and_tests(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Repo(root)
            for i in range(3):
                repo.write("src/a.py", f"A = {i}\n")
                repo.write("lib/b.py", f"B = {i}\n")
                repo.write("tests/test_a.py", f"T = {i}\n")
                repo.write("src/c.py", f"C = {i}\n")
                repo.commit(f"pair {i}")
            for i in range(11):
                repo.write(f"lib/bulk{i}.py", "X = 1\n")
            repo.write("src/a.py", "A = 9\n")
            repo.write("lib/b.py", "B = 9\n")
            repo.commit("bulk")
            current = ["src/a.py", "lib/b.py", "src/c.py", "tests/test_a.py"]
            out = cochange.collect(root, current, {"tests/test_a.py"})
        self.assertEqual(out["skipped_large"], 1)
        self.assertEqual([(p["a"], p["b"], p["together"]) for p in out["pairs"]],
                         [("lib/b.py", "src/a.py", 3), ("lib/b.py", "src/c.py", 3)])


if __name__ == "__main__":
    unittest.main()
