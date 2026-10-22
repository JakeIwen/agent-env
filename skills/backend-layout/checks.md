# backend-layout checks

A stdlib-only Python checker (3.9+), installed into a repo and owned by it
from then on. It reads source text and never imports or executes project
code. Size and heuristics are review triggers; declared structure is
enforced, and only forward.

| File | Role |
|---|---|
| `checks/check_layout.py` | entry point and CLI |
| `checks/backend_layout/cli.py` | runs the rules, applies exceptions and the baseline, picks the exit code |
| `checks/backend_layout/config.py` | the `layout` block: defaults, validation, path patterns |
| `checks/backend_layout/files.py` | discovery (git or a walk), default exclusions, source kinds |
| `checks/backend_layout/edges.py` | import edges through consolidate's resolver, coverage counts |
| `checks/backend_layout/structure_rules.py` | contract, prefix-group, entry-heavy, kind-folder, cycle |
| `checks/backend_layout/advisory_rules.py` | fan-in-size, shim-stale, effects-in-rules, shell-size |
| `checks/backend_layout/contracts_table.py` | reads the AGENTS.md Contracts table |
| `checks/backend_layout/references.py` | turns commands, paths and `-m` modules into repo paths |
| `checks/backend_layout/targets.py` | reads units, plists, package.json and manifests; declared-target |
| `checks/backend_layout/baseline.py`, `json_splice.py` | the `layout` baseline key and rebaseline |
| `checks/backend_layout/git_adapter.py` | every git call |
| `checks/backend_layout/report.py`, `findings.py` | result record, text and JSON output, rule vocabulary |
| `checks/backend_layout/import_graph.py`, `cochange.py` | copies of consolidate's files, hash-checked by the skill's tests |
| `tests/test_layout_*.py`, `tests/layout_fixture.py` | fixture tests, installed with the checker |
| `templates/test_layout_tree.py` | installed test: the repo's own tree passes |
| `install-checks.py`, `install_plan.py` | the installer's command line and its plan (files, config, suite wiring); skill-only |

Skill-only tests (`test_install_checks.py`, `test_import_graph_copy.py`) stay
in the skill. Run the skill's suite from its folder:
`python3 -m unittest discover -s tests`.

## Rules

| Rule | Treatment | Reports |
|---|---|---|
| `contract` | ratchet, once the repo declares `contracts` | an import that crosses a declared boundary; unresolved imports are coverage gaps, not findings |
| `declared-target` | block | a Contracts row whose path doesn't exist or names no caller/owner; a unit, plist, package-script or manifest target the table doesn't list or that doesn't exist. Dynamic targets are listed for a manual check |
| `prefix-group` | ratchet | a file in a group of 3+ siblings sharing a name prefix (`radar_`, `autofill-`) with no folder of that name, with cohesion evidence: imports within the group, shared import targets, outside callers, commits changing 2+ members |
| `entry-heavy` | ratchet | a module with a main guard over `entryLines` (Python `__main__` guard, a Node `process.argv[1]`/`require.main` guard or shebang, Go `package main`); `entries` pass |
| `kind-folder` | ratchet | a folder named utils, helpers, common or misc, or an `sh/` folder holding Python |
| `cycle` | ratchet for Python, advisory for JS/TS | a static module-level import cycle; function-level and `TYPE_CHECKING` imports don't count |
| `fan-in-size` | advisory | a file over consolidate's `file_lines` (default 800) imported by `fanIn`+ non-test modules |
| `shim-stale` | advisory | a re-export-only module (or `raise SystemExit(main())` wrapper) that nothing in the repo imports and no Contracts row or unit lists |
| `effects-in-rules` | advisory | socket, subprocess, clock, HTTP, storage or file writes in a module named like a model or rules module (`models.py`, `*_state.py`, `*_view.py`, `*.helpers.js`, ...) |
| `shell-size` | advisory | a shell script over `shellLines` |

Test files (`tests/`, `test_*.py`, `*.test.ts`, ...) are scanned for imports
but are never subjects of the structure rules. `.tsx`/`.jsx` files resolve
imports but belong to react-app. Where react-app's `check-structure` is
installed (a `structure` block or `check-structure.mjs` in the repo), a
`layout.contracts` entry equal to one of its contracts is skipped with a
warning, and JS cycles inside its source root are left to it.

## Settings

The `layout` block of `<repo>/.codeshape/config.json`, paths relative to
the repo. Unknown keys fail. consolidate's keys and react-app's `css` and
`structure` blocks share the file; `file_lines` is read for `fan-in-size`.

```json
{
  "layout": {
    "sourceRoots": ["."],
    "entries": [],
    "contracts": [{ "from": "lib", "to": ["projects", "tools"], "allowDynamic": false }],
    "contractsTable": { "file": "AGENTS.md", "heading": "Contracts" },
    "targets": ["**/*.service", "**/*.plist", "**/package.json"],
    "exclude": [],
    "aliases": {},
    "thresholds": { "entryLines": 200, "shellLines": 200, "prefixGroup": 3, "fanIn": 3 },
    "exceptions": []
  }
}
```

These are the defaults except `contracts` (default none); list only what
differs.

- Paths and globs: a pattern without `*?[` is a path prefix (a file, or a
  folder and everything under it); otherwise `fnmatch`, where `*` crosses
  folders and `**/x` also matches `x` at the root.
- `sourceRoots`: what the rules look at. Imports resolve across the whole
  repo either way. Nested roots are fine; each file counts once.
- `entries`: standalone tools and wrappers allowed a long entry module.
- `contracts`: `from` is a folder or file (`*` is everything outside `to`);
  `to` lists folders it must not import. `allowDynamic` permits imports
  inside functions (Python) for lazy loaders.
- `targets`: globs for the files `declared-target` reads. `.service` and
  other unit files by `Exec*` lines and `WorkingDirectory`; `.plist` by
  `Program`/`ProgramArguments`; `package.json` by `scripts` and `bin`; any
  other file as a manifest (JSON string values or text lines, including
  example-compute `{source:path}` placeholders).
- `aliases`: JS/TS specifier prefixes mapped to repo folders
  (`{"~/": "app/"}`). Python resolves against the importer's folder, its
  parents and `src/`, as consolidate does.
- `exclude`: on top of the built-in exclusions (`node_modules`, `dist`,
  `build`, `vendor`, `__pycache__`, `.venv`, `venv`, `site-packages`,
  `generated`, `*.min.*`, `.agent`, `.claude/worktrees`). In a git work
  tree only tracked and unignored files are read.

## The Contracts table

The first Markdown table under the heading named by `contractsTable`, one
row per path something outside the repo calls:

```markdown
## Contracts

| Path | Caller | Owner |
|---|---|---|
| `python3 -m projects.device_app.broker` | van-telemetry.service | projects/device_app/broker.py |
| `pi/scripts/backup/` | Pi deploy allowlist, cron | pi/scripts/backup/run.py |
```

The path cell may be a repo path, a folder (covers everything under it), a
dotted module, or a command. Deployed absolute paths in units and plists
are matched to repo files by their longest common suffix of two or more
components (`/home/<user>/scripts/x.sh` to `pi/scripts/x.sh`); a match by file
name alone is listed as dynamic. Without a table, `declared-target` lists
every target it found as advisory: the rows the table would need.

## Exceptions

```json
"exceptions": [
  { "rule": "kind-folder", "path": "shared/sh", "reason": "documented compatibility layout; extend through its owners" }
]
```

`path` matches any of a finding's paths (the importer or target of a
contract, any member of a cycle). A reason is required. Every exception is
reported with the number of findings it covers; one that covers nothing is
a warning. A folder or an external caller can't carry a same-line marker,
so there are no inline exemptions.

## Baseline

Existing findings live under a top-level `layout` key of
`.codeshape/baseline.json`, outside consolidate's `limits`; the file stays
`version: 2`, so older checkers read it unchanged, and consolidate's
`drift_check.py rebaseline` keeps the key.

- Until the key exists every rule is advisory and the run exits 0.
- With it: a ratcheted finding whose rule and key are not recorded is new
  and fails; recorded ones are reported as baselined. Keys are paths
  (`contract`: `importer -> target`; `cycle`: its members). Renames since
  the recorded `head` are followed with `git diff -M`.
- `declared-target` findings fail whenever there is a baseline; they are
  never recorded. Advisory rules never fail.
- `check_layout.py rebaseline` writes the key (date, HEAD, ratcheted
  non-exempt findings) and nothing else: every other byte of the file is
  kept, and the file is left unstaged. It refuses when the file doesn't
  exist (run `drift_check.py rebaseline` first; consolidate owns the file)
  and on uncommitted changes outside `.codeshape/` unless `--allow-dirty`.
  Rebaseline after a reviewed cleanup, never to make a failing run pass.

## Running

```sh
python3 scripts/check_layout.py [--json]           # in a repo with the checks installed
python3 scripts/check_layout.py rebaseline         # after drift_check.py rebaseline
python3 ~/.claude/skills/backend-layout/checks/check_layout.py --root <repo> --config <file> [--json]
```

The last form is a read-only audit: write a config shaped like
`.codeshape/config.json` anywhere and point at any repo. Use plain
`python3`; `-I` on 3.11+ drops the checker's folder from the import path.

Output always shows, separately: files scanned (by kind), findings (new,
blocking, baselined, advisory, exempt), exceptions applied, parse and target
file errors, and resolved, unresolved and unsupported imports (shell
`source` lines and Go files are counted, not analyzed). Exit codes: 0
clean; 1 new ratchet findings, `declared-target` failures, or zero files
scanned; 2 a config error.

## Installing

```sh
python3 ~/.claude/skills/backend-layout/install-checks.py <repo> [--scripts-dir scripts] [--suite run_tests|npm|unittest|none] [--dry-run] [--force]
```

- Copies `check_layout.py`, the `backend_layout/` package (with consolidate's
  `import_graph.py` and `cochange.py`) and the tests into
  `<repo>/<scripts-dir>/`. Nothing in the repo depends on `~/.claude`
  afterwards. Refuses when the skill's copies of consolidate's files have
  drifted from consolidate.
- Adds a default `layout` block to `.codeshape/config.json` when there is
  none (excluding the installed checker files), touching no other key.
  Never writes a baseline.
- Wires the tests (`<scripts-dir>/test_layout*.py`, including
  `test_layout_tree.py`, which runs the checker on the repo) into the suite
  the repo already uses: a step in `run_tests.py`'s `commands = [` list
  (or nothing, when it collects `test_*.py` files itself); `check:layout`
  and `test:layout` scripts with `test:layout` appended to `npm test`; or a
  generated `test_backend_layout.py` in the unittest discovery root named
  in AGENTS.md or README (default `tests/`). Existing commands are kept.
- `--dry-run` prints what would change. A repeat run changes nothing. An
  installed file that differs from the skill's copy is refused, by name,
  unless `--force`; compare first, and review the diff like any change.
- After installing: run the checker, fix findings or record them as
  exceptions with reasons, then `drift_check.py rebaseline` and
  `check_layout.py rebaseline`, and commit the wiring with the baseline.
  When the skill's checker improves, rerun with `--force`.

## Known gaps

- JS/TS: relative static imports, `export ... from` and `require` only;
  dynamic `import()` is not seen; unconfigured aliases (`~/`, `@/`, `#`)
  are counted as unsupported. JS cycles stay advisory until a repo's alias
  config is validated.
- Python: absolute imports that resolve outside the importer's ancestors
  (a launcher's `PYTHONPATH`) are unresolved, and counted only when the
  name matches a first-party folder or module.
- Roles are detected by module name only, so `effects-in-rules` sees only
  conventionally named model and rules modules.
- Go imports and shell `source` graphs are not analyzed.
