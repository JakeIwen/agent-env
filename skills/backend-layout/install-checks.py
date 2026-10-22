#!/usr/bin/env python3
"""Install the backend-layout checks into a repo: copy check_layout.py, its backend_layout/ package
(with consolidate's import_graph.py and cochange.py) and its tests into <repo>/<scripts-dir>/, add a
default `layout` block to .codeshape/config.json when there is none, and wire the tests into the suite
the repo already uses. Never writes a baseline; the repo owns its copy from then on.

    python3 install-checks.py <repo> [--scripts-dir scripts] [--suite run_tests|npm|unittest|none]
                              [--dry-run] [--force]

Suites, detected in this order unless --suite says otherwise: a root run_tests.py (a step added to its
`commands = [` list, or nothing when it already collects test_*.py files), a package.json with a test
script (`check:layout` and `test:layout` scripts, the latter appended to `test`), or a unittest tree
(a generated test_backend_layout.py in its discovery root). Existing commands are kept.
"""
import argparse
import subprocess
import sys
from pathlib import Path

from install_plan import (SUITES, Plan, apply, mirrored_drift, plan_config, plan_copies, plan_suite)


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("--scripts-dir", default="scripts")
    ap.add_argument("--suite", choices=SUITES)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite installed files that differ from the skill's")
    return ap.parse_args(argv)


def first_run(repo: Path, scripts: str):
    result = subprocess.run([sys.executable, str(repo / scripts / "check_layout.py"), "--root", str(repo)],
                            capture_output=True, text=True, check=False)
    lines = result.stdout.splitlines()
    print("\nFirst run of the installed checker:")
    print("\n".join("  " + ln for ln in lines[:8] + ["..."] + [ln for ln in lines if ln.startswith("verdict")]))
    print("Fix or record each finding (exceptions with reasons), then rebaseline: drift_check.py rebaseline, "
          f"then python3 {scripts}/check_layout.py rebaseline.")


def main(argv=None) -> int:
    args = parse_args(argv)
    repo, scripts = Path(args.repo).resolve(), args.scripts_dir.strip("/")
    if not repo.is_dir():
        print(f"not a folder: {repo}", file=sys.stderr)
        return 2
    drift = mirrored_drift()
    if drift:
        print(f"refused: the skill's copy of {', '.join(drift)} differs from consolidate's; refresh "
              f"checks/backend_layout/ from ~/.claude/skills/consolidate/ first.", file=sys.stderr)
        return 1
    plan = Plan()
    plan_copies(repo, scripts, plan)
    plan_config(repo, scripts, plan)
    plan_suite(repo, scripts, args.suite, plan)
    if plan.conflicts and not args.force:
        print("refused: these files differ from what the installer would write: " + ", ".join(plan.conflicts)
              + ". Compare them, then rerun with --force.", file=sys.stderr)
        return 1
    plan.files.update(plan.conflicts)
    verb = "would write" if args.dry_run else "wrote"
    for rel in plan.files:
        print(f"{verb}: {rel}")
    kept = [x for x in plan.unchanged if "(" in x]
    print(f"unchanged: {len(plan.unchanged)} file(s)" + (f" ({', '.join(kept)})" if kept else ""))
    for note in plan.notes:
        print(f"NOTE: {note}")
    if not args.dry_run and plan.files:
        apply(repo, plan)
        first_run(repo, scripts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
