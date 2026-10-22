#!/usr/bin/env python3
"""Run every bundled suite without leaving build or bytecode output."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PYTHON_SUITES = (
    "skills/consolidate", "skills/backend-layout", "hooks", "tools",
)


def main():
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for path in ROOT.rglob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    for path in ROOT.rglob("*.json"):
        json.loads(path.read_text())
    for folder in PYTHON_SUITES:
        tests = ROOT / folder / "tests"
        if not list(tests.glob("test_*.py")):
            raise RuntimeError("empty test inventory: " + folder)
        print("Suite: " + folder, flush=True)
        subprocess.run([sys.executable, "-B", "-m", "unittest", "discover",
                        "-s", "tests", "-f"], cwd=ROOT / folder,
                       env=environment, check=True)
    checks = ROOT / "skills/react-app/checks"
    node_tests = sorted(checks.glob("*.test.mjs"))
    if not node_tests:
        raise RuntimeError("empty React test inventory")
    subprocess.run(["node", "--test", *map(str, node_tests)],
                   cwd=ROOT, env=environment, check=True)
    print("All bundled suites passed.")


if __name__ == "__main__":
    main()
