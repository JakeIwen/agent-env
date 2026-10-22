---
name: python-tool
description: Organize and check the owner's Python tool and library repos. Use when creating or reorganizing one, or adding modules, CLIs, tests or dependencies. Covers runtimes, packages, imports and suite gates. Not for third-party repositories or ad-hoc one-off scripts.
---

# python-tool

The Python layer over the global Code shape rules; those rules are not
repeated here. The repo's own AGENTS.md wins. One file serves both agents:
under Claude load `python-tool` with the Skill tool; under Codex read this
same SKILL.md through its skill listing.

Use `local-service` for always-on apps, supervision and service controllers;
use `mac-pi-repo` for host layout and deployment. This skill owns neither.

## Start with the execution contract

Read AGENTS.md's map, README's setup/test commands, dependency manifests,
entry points and representative tests before choosing a layout. Establish:

- Which interpreters actually launch the program, not just `python3` on the
  interactive PATH; which hosts and minimum Python version are supported.
- Whether it is a checkout-run tool, an installed library, a bundled script
  cohort, or an intentionally standalone executable.
- Which command covers every automated suite, and which imports/data paths
  callers depend on. Preserve these contracts when adding a module.

## Python version and dependencies

Use the interpreter named by the deployment contract.

- A stdlib tool intended to run with Mac `/usr/bin/python3` stays compatible
  with **3.9**. That is the portability default for such tools, not a mandate
  to downgrade other repos. For a new managed-runtime or Pi-only project,
  prefer **3.11+**, or a higher floor required by its dependencies; document
  that choice and its interpreter. Existing declared floors win.
- Write the floor in AGENTS.md and the setup instructions; for an installable
  project also declare `requires-python` in `pyproject.toml`. Test the oldest
  supported interpreter, not only the newest development one. Syntax parsing
  alone cannot detect unavailable stdlib APIs or dependency incompatibilities.
- On 3.9, use `Optional`/`Union` where annotations are evaluated and
  `class State(str, Enum)` rather than `StrEnum`; do not introduce `match`,
  `tomllib`, or other newer features accidentally. Postponed annotations do
  not backport runtime APIs.
- Prefer stdlib for CLI parsing, JSON, paths, SQLite and ordinary HTTP. Add a
  dependency for a real capability, not just a convenience wrapper. Keep
  heavy/optional features separate so basic CLI/help/imports remain usable.
- For dependencies, use a repo-owned, ignored `.venv` unless the repo already
  has a documented environment location. Use that interpreter's `-m pip`;
  never install into system Python or use `--break-system-packages` as setup.
  Recreate environments rather than moving them. Default to isolation, not
  `--system-site-packages`; preserve an existing deliberate exception.
- Checkout applications record runtime dependencies in `requirements.txt`,
  optional features in a named requirements file, and test-only dependencies
  separately. Pin application environments as the repo does. An installable
  library uses `[project.dependencies]` / optional dependencies in
  `pyproject.toml` with supported ranges, not the app's exact pins; keep any
  reproducible development lock separate. Do not maintain conflicting lists
  or add packaging machinery to a stdlib checkout tool just for uniformity.
- External executables are dependencies too. Name them in setup and fail
  clearly when required; a Python-only import check will not find missing
  FFmpeg, Node or platform tools. Keep installation out of runtime imports.

## Packages and entry points

Layout inside a package (module roles, feature folders, compatibility paths)
is `backend-layout`'s; this section covers packaging and launch.

- **Checkout-run tools:** default to one snake_case package at the repo root,
  with `__init__.py`, a small `__main__.py`, `cli.py` and feature-named modules;
  put tests in `tests/`. Run `python3 -m package_name` from the repo root.
  This matches the small repos without adding an installation step.
- **Installable libraries/tools:** prefer `src/package_name/`, a
  `pyproject.toml` and tests outside `src/`. Declare a console command with
  `[project.scripts]` pointing at `package_name.cli:main` if needed. Install
  into the venv for development and test a built wheel from outside the
  checkout too: the src layout exposes missing packaged files instead of
  silently importing the working tree. This is a recommendation for new
  distributable projects, not the surveyed repos' prevailing layout.
- **Existing script cohorts:** keep their deployment contract. Media's
  `scripts/` siblings travel in an app bundle; example-guides has top-level
  modules plus `local_service/`; example-toolkit has `lib/`, `tools/` and
  `projects/` packages. Do not migrate them during an unrelated feature.
  An independently deployed, stdlib-only executable may remain one file.
- Default CLI interface: argparse, `main(argv=None) -> int`, and
  `raise SystemExit(main())` at the entry boundary. Importing the library
  should not parse argv, start a server, install packages or perform work.
  Keep CLI parsing outside reusable operations. Preserve existing stdout,
  stderr, exit codes and machine-readable output when splitting a CLI.
- A stable script path used by a scheduler or bundle can remain a thin
  wrapper delegating to the package. Resolve its launch location once at
  that boundary, not separately inside every module. A shell wrapper should
  `exec` the Python command so exit status and signals remain intact.
- Within packages use explicit relative or package-qualified imports, not
  bare sibling imports dependent on cwd. Spawn package children with
  `sys.executable`, `-m` and an explicit cwd when using a checkout; do not
  execute an internal package file by path. Installed commands should not
  require the caller to be in the checkout.
- Keep `__init__.py` lightweight. Use regular packages for new test/support
  trees unless namespace packaging is deliberate. Put packaged resources
  with their feature and access installed resources with `importlib.resources`;
  existing checkout-relative paths may use `Path(__file__)`. Mutable state
  belongs in the repo's documented ignored/state location, not a package.

## Import isolation, not import repair

`python3 -I` ignores `PYTHON*` environment settings and excludes the script
or working directory and user site-packages from the normal import path.
Use it for intentionally standalone stdlib scripts processing untrusted
inputs, or for packages installed in the selected interpreter's environment.
A venv alone does not install the checkout package. Do not add `-I` blindly
to a checkout `-m package` command or a sibling-importing script cohort.

For an import failure, fix the launch/install contract. Avoid new per-file
`sys.path` edits, implicit `PYTHONPATH` dependencies, and
`try: from .x ... except ImportError: from x ...` branches: they support two
incompatible execution modes and can hide a real dependency failure.
Preserve an existing reviewed release bootstrap; do not spread it into the
library. Some flat `-I` helpers in `scripts/shared/sh/` deliberately use a
subprocess CLI boundary instead of importing siblings.

For an existing loose-script test suite, one explicit import-root registry
in its suite launcher is a transitional contract; use it rather than adding
another test-local patch. `~/dev/scripts/run_tests.py` has
`PYTHON_IMPORT_ROOTS`. New packages should need neither. An optional-feature
import guard may report the documented install command when that feature
is selected; it must not disguise a required missing dependency or retry
imports under another module name.

## Records, configuration and helper discovery

Python choices for the global shared-record rule:

- Use dataclasses for internal records/configuration, `frozen=True` for
  immutable values and `field(default_factory=...)` for mutable defaults.
  Use TypedDict for dictionary-shaped JSON contracts. Convert argparse
  namespaces into the configuration record at the boundary rather than
  passing untyped namespaces throughout the implementation.
- Use `str, Enum` (or `StrEnum` at a 3.11 floor) for string-valued states;
  serialize explicit values where necessary. Validators parse incoming
  dictionaries into the declared record and reject invalid fields/types;
  TypedDict and dataclass construction alone do not validate JSON. Be
  explicit about whether booleans are acceptable as integers.
- Keep executable defaults in a discoverable `paths.py`/`config.py` or the
  feature's schema module; keep user settings separate from code. Parse
  environment/config at a defined boundary so tests can supply values.

Search the current repo map and shared modules before adding a helper.
Cross-repo reuse requires an explicit dependency or a reviewed extraction,
not an absolute sibling-checkout import.

## Tests and repo-level gates

- Default new stdlib tools to **unittest** with `tests/test_*.py` and shared
  fixture builders beside the tests. This matches seven surveyed repos and
  keeps their setup dependency-free. Retain pytest where already used:
  example-toolkit mixes unittest classes with pytest functions/fixtures, so
  unittest discovery alone would silently omit real tests.
- A documented command is an entry point; a `run_tests.py` file is not
  mandatory. For one unittest tree, a command such as
  `python3 -m unittest discover -s tests -v` suffices if it really finds all
  tests. Ensure nested directories are discoverable at the supported Python
  floor; use regular test packages and a suitable top-level discovery root.
- When tests span roots or runners, use one repo-owned `run_tests.py` that
  invokes each required suite with explicit cwd/interpreter, propagates
  failure, rejects an empty inventory and reports unrun suites on fail-fast.
  Retain an existing umbrella such as example-guides' `npm test` instead of
  adding a competing launcher. Name the exact command and prerequisites in
  AGENTS.md. No test/build command may depend on this skill's directory.
- Include Python, Node/shell tests and required integration checks in that
  inventory. Source-dependent acceptance checks may be a declared gate with
  prerequisites; never silently count them as covered by unit discovery.
  Missing required tools/dependencies are setup failures, not skip reasons.
  Keep optional live/hardware checks explicit and separate from safe default
  tests; executing the suite must not implicitly authorize device actions.
- Test through imports and CLI subprocesses, using generated fixtures,
  temporary output roots and controlled external boundaries. For a CLI,
  cover help, success, invalid input and exit behavior. For an installed
  command/wrapper, test from an unrelated cwd. A packaging change also needs
  an installed-artifact test, not only editable-checkout imports.
- Before completion run the whole documented suite and the repo's existing
  lint/type/structure gates. For a reorganization compare baseline and new
  CLI stdout/stderr/exit codes, JSON or generated file bytes with identical
  inputs and interpreter; use semantic comparison only when volatile fields
  are intentionally excluded. Report the interpreter, command, outcomes
  and any unverified host/package checks. This skill introduces no blanket
  formatter, type checker or new dependency into an established repo.
