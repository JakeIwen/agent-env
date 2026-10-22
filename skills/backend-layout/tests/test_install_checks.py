"""install-checks.py on fixture repos only: dry run, idempotence, edited-file refusal, config and
suite wiring for run_tests.py, npm and unittest repos, and the installed copy running without the skill.
Skill-only: the installer does not copy this file into repos."""
import json
import os
import subprocess
import sys
from pathlib import Path

from layout_fixture import LayoutCase

INSTALLER = Path(__file__).resolve().parent.parent / "install-checks.py"
RUN_TESTS = """#!/usr/bin/env python3
import subprocess
import sys


def main():
    commands = [
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
    ]
    for command in commands:
        if subprocess.run(command).returncode:
            return 1
    return 0
"""


class Installer(LayoutCase):
    def install(self, *args, expect: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run([sys.executable, str(INSTALLER), str(self.root), *args], capture_output=True,
                                text=True, check=False)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result

    def snapshot(self) -> dict:
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*")
                if p.is_file() and ".git/" not in str(p)}

    def test_dry_run_changes_nothing_and_lists_the_plan(self):
        self.write({"app/main.py": "", "tests/test_main.py": ""})
        before = self.snapshot()
        out = self.install("--dry-run").stdout
        self.assertEqual(self.snapshot(), before)
        self.assertIn("would write: scripts/check_layout.py", out)
        self.assertIn("would write: .codeshape/config.json", out)
        self.assertIn("would write: tests/test_backend_layout.py", out)

    def test_repeat_install_is_idempotent_and_never_writes_a_baseline(self):
        self.write({"app/main.py": "", "tests/test_main.py": ""})
        self.install()
        first = self.snapshot()
        out = self.install().stdout
        self.assertEqual(self.snapshot(), first)
        self.assertNotIn("wrote:", out)
        self.assertFalse((self.root / ".codeshape/baseline.json").exists())

    def test_edited_installed_file_is_refused_unless_forced(self):
        self.write({"app/main.py": "", "tests/test_main.py": ""})
        self.install()
        edited = self.root / "scripts/backend_layout/report.py"
        edited.write_text(edited.read_text() + "# local edit\n")
        result = self.install(expect=1)
        self.assertIn("scripts/backend_layout/report.py", result.stderr)
        self.assertIn("# local edit", edited.read_text())
        self.install("--force")
        self.assertNotIn("# local edit", edited.read_text())

    def test_config_block_is_added_beside_other_keys_and_kept_when_present(self):
        self.write({"app/main.py": "", "tests/test_main.py": "",
                    ".codeshape/config.json": '{"hook_mode": "block", "file_lines": 900}\n'})
        self.install()
        text = (self.root / ".codeshape/config.json").read_text()
        self.assertTrue(text.startswith('{"hook_mode": "block", "file_lines": 900,'))
        data = json.loads(text)
        self.assertEqual(data["layout"]["sourceRoots"], ["."])
        data["layout"]["entries"] = ["tools/x.py"]
        (self.root / ".codeshape/config.json").write_text(json.dumps(data))
        self.install()
        self.assertEqual(json.loads((self.root / ".codeshape/config.json").read_text())["layout"]["entries"],
                         ["tools/x.py"])

    def test_run_tests_suite_gains_one_step(self):
        self.write({"app/main.py": "", "run_tests.py": RUN_TESTS})
        self.install()
        text = (self.root / "run_tests.py").read_text()
        self.assertIn("        [sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts', '-p', "
                      "'test_layout*.py'],\n", text)
        self.assertIn("'discover', '-s', 'tests'],", text)
        self.install()
        self.assertEqual((self.root / "run_tests.py").read_text(), text)

    def test_npm_suite_keeps_its_test_command(self):
        self.write({"server/index.mjs": "export {}\n",
                    "package.json": json.dumps({"name": "x", "scripts": {"test": "node --test"}}, indent=2)})
        self.install()
        scripts = json.loads((self.root / "package.json").read_text())["scripts"]
        self.assertEqual(scripts["test"], "node --test && npm run test:layout")
        self.assertEqual(scripts["check:layout"], "python3 scripts/check_layout.py")
        self.assertIn("-p 'test_layout*.py'", scripts["test:layout"])

    def test_unittest_suite_gets_a_wiring_test_in_its_discovery_root(self):
        self.write({"pkg/__init__.py": "", "pkg/core.py": "", "checks/test_core.py": "",
                    "AGENTS.md": "Run `python3 -m unittest discover -s checks -v`.\n"})
        self.install("--scripts-dir", "tools/layout")
        wiring = (self.root / "checks/test_backend_layout.py").read_text()
        self.assertIn('parents[1] / "tools/layout"', wiring)

    def test_installed_copy_runs_without_the_skill(self):
        self.write({"pkg/__init__.py": "", "pkg/core.py": "", "tests/test_core.py": ""})
        self.install()
        home = self.root / "fake-home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home))
        tree = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p",
                               "test_layout_tree.py"], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(tree.returncode, 0, tree.stdout + tree.stderr)
        report = subprocess.run([sys.executable, "scripts/check_layout.py", "--json"], cwd=self.root, env=env,
                                capture_output=True, text=True)
        data = json.loads(report.stdout)
        installed_tests = len(list((self.root / "scripts").glob("test_layout*.py")))
        # pkg/ and tests/ (3), the generated tests/test_backend_layout.py and the installed tests; the
        # checker's own modules are excluded by the default layout block
        self.assertEqual(data["counts"]["filesScanned"], 4 + installed_tests)
        self.assertEqual(data["findings"], [])
