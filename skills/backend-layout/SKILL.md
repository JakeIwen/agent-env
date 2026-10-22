---
name: backend-layout
description: Organize and check the layout of code with no UI - service processes, CLIs, workers and folders of scripts in Python, Node, shell or Go, including the backend parts of mixed apps. Use when creating or reorganizing such a repo or folder, adding modules, entry points or scripts to one, splitting a large module, moving a path something outside the repo calls, or installing or running its layout checks. Not for React/Preact UI code (react-app) or third-party repos.
---

# backend-layout

The layout layer over the global Code shape rules for code with no UI; those
rules are not repeated here. The repo's own AGENTS.md wins. One file serves
both agents: under Claude load `backend-layout` with the Skill tool; under
Codex read this same SKILL.md through its skill listing.

## Scope

Service processes, CLIs, workers and folders of scripts in Python, Node,
shell and Go, including the backend portions of mixed apps.
`python-tool` owns Python runtimes, packaging, imports and suites;
`local-service` owns supervision and service controllers; `mac-pi-repo` owns
the host split and deployment; `react-app` owns UI code. In a repo that isn't
the owner's, the global rule stands: no cleanup, no edits to its agent
instructions, no new test runner; report the gap.

Stack specifics: `stacks.md`. The checker, its rules and settings:
`checks.md`. Verifying a reorganization changed nothing: `verify.md`.

## Dependency direction

The default; repo-specific boundaries go in the checker's `contracts`.

- An entry point builds the configuration record and the collaborators,
  then calls the application once. It is thin.
- Models and rules describe records and decisions. They depend on nothing
  that starts a service, opens a transport or touches storage.
- Runtime code coordinates through explicit collaborators. Adapters depend
  only on the records and contracts they exchange.
- Cross-feature dependencies go through a documented public module or
  function. A shared contract lives at the nearest common ownership boundary.

Interfaces, factories or a composition module appear when construction or
substitution needs them, not before. A small cohesive module may hold a
record and its rules. An independently deployed script may stay one file.

## Roles as vocabulary

Five words for what a module does. They are not required filenames, and a
feature needn't have all five. Domain names stay (`radar/alignment.py`, not
`radar/rules.py`).

| Role | May do | Typical places |
|---|---|---|
| entry | Parse argv and env, build the config record, call one run | `__main__.py`, `cli.py`, `entrypoints/`, `bin/`, `cmd/<name>/main.go` |
| model | Records, enums, vocabularies, validators; no I/O | `models.py`, `types.ts`, a sidecar `.json`, a Go struct file |
| rules | Pure decisions over records: no clock, socket, file or subprocess | `*_state.py`, `*_view.py`, `*.helpers.js`, functions in `lib/<concern>.sh` |
| adapter | One external thing: a socket, store, subprocess, systemd, HTTP | `*_adapter.py`, `store.py`, `transport.py`, `lib/<thing>.sh` |
| runtime | The loop or handler that calls rules and adapters in order | `runtime.py`, `server/http.ts`, the script body |

- A module that both decides and acts is split at the decision when it is
  touched for a feature. The pure half gets record-in, record-out tests; the
  adapter half is tested against the real thing where a temporary one exists
  (a SQLite file, a loopback service, a protocol fixture). A test that swaps
  the adapter for a fake covers the orchestration, not the adapter.
- A module with a main guard is thin. Library code imports without side
  effects and without reading argv.
- An adapter is named for what it touches (`device_runtime`, `history/store`,
  `ntfy_adapter`), never `utils`, `helpers`, `common`, `io` or `misc`.
- Named phases make a long loop readable; a generic phase registry is
  optional. Lock scope, ordering, cancellation and cleanup are preserved
  before `run()` is made short.

## Features by cohesion

- Three or more siblings sharing a name prefix are a candidate feature, not
  an automatic move. Before grouping, check shared data, imports, callers and
  co-change (the checker's `prefix-group` prints that evidence). A prefix can
  mean one feature, several independent commands, or a family of adapters.
  Two files can already be a feature.
- Once grouped, the folder takes the prefix and the files drop it
  (`radar_alignment.py` becomes `radar/alignment.py`, `export-records.ts`
  becomes `export/records.ts`).
- A repo-level shared folder (`lib/`, `shared/`) is feature-named inside. A
  documented kind-named compatibility layout (`scripts/shared/sh/`) is
  extended through its owners, never duplicated.
- Framework conventions are boundaries too: route folders and `.server.ts`
  suffixes stay. A new server never starts in `scripts/`; moving an existing
  one out is its own migration.

## Public interfaces

- A feature has documented public modules or functions. A public module such
  as `radar.alignment` is a valid boundary; inside the feature, direct
  imports between internals are fine.
- `__init__.py` and `index.ts` stay light. No mandatory re-export hub: an
  imported initializer runs code, and one that loads adapters makes every
  consumer pay for them.
- A published Node package keeps its existing `exports`; adding a
  restrictive map during a layout cleanup can break consumers.
  Application-internal folders need no export map.

## Contracts and compatibility paths

- Every path something outside the repo calls is a contract: systemd
  `ExecStart`, launchd `ProgramArguments`, cron, BetterTouchTool, npm run
  scripts, `.example-compute.json` tasks, the Pi deploy allowlist, saved jobs,
  rollback releases.
- The repo AGENTS.md carries a Contracts table: one row per path, naming the
  caller and the implementation owner, never copied unit text. The checker's
  `declared-target` rule verifies it against the units, plists, package
  scripts and manifests it can read.
- Moving a listed path leaves a compatibility file at the old path. It is a
  supported interface: a header comment names the owner, its callers and its
  retirement condition, or says it is permanent. Migration dates go in docs,
  not the comment. An executable wrapper carries only the mechanics the
  contract needs (`raise SystemExit(main())`; a shell wrapper that `exec`s
  and keeps arguments, signals and exit status). Fixes go in the owner.
- A compatibility path is removed only when its callers on every supported
  host and every supported rollback state are gone. No importers in the repo
  is not evidence of that. A stable service entry point may stay forever.

## Splitting a god module

Default order when a module over the size limit is touched; each step a
tidying commit, each verified per `verify.md`. The goal is coherent state and
lifecycle ownership with behavior preserved, not a short file.

1. Pure decisions out into model and rules modules, keeping public names
   (device_app did this for `status_view`, `vehicle_state`, `wake_state`).
2. Adapters out, one per external thing (for a broker: CAN runtime, history
   store, notifications, helper processes), keeping lock scope and ordering.
3. The loop into named phases. If a class's `__init__` builds its
   collaborators and construction now needs substitution, a
   `build_<thing>(config)` factory in a composition module takes it over.

Never split by position ("part 2"), by size alone, or into a `_helpers`
sibling.

## Docs

- The repo AGENTS.md carries the folder and ownership map plus the Contracts
  table, both small and updated in the same change as the code. Longer
  migration records and incidents go to `docs/` with dated filenames.
- A README past about 400 lines is a review trigger to move topics to
  `docs/<topic>.md`, keeping links and operational entry points.

## Boundaries

- Moves land as tidying commits, separate from behavior changes.
- Exceptions are `layout.exceptions` entries with a reason (`checks.md`);
  every one is reported.
- Never restructure live-service code or hardware paths to satisfy a check;
  report it. Applying these rules to an existing repo is its own reviewed
  migration with captured baseline behavior and stable entry points.
