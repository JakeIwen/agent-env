---
name: consolidate
description: Code-shape checks and consolidation planning for the current git repo. `check` (default) reports size, function-length, escape-hatch and duplication metrics against the repo's tracked baseline and says whether a cleanup round is due; `rebaseline` writes `.codeshape/baseline.json` after a reviewed cleanup lands; `audit` writes a full read-only refactor audit to .agent/handoffs/refactor-audit.md; `tickets` turns ranked audit items into delegation-ready prompts. Use only when the user asks to check code drift, rebaseline, audit for refactors, or write refactor tickets.
---

# consolidate

Planning and measurement only; it never refactors. The mode is the first word of the invocation
arguments: `check` (default), `rebaseline`, `audit`, or `tickets`. Anything after the mode is
extra guidance (e.g. `tickets 1-3`, `audit focus on lib/`).

## Hard rules (all modes)

- Run from inside a git repo; the scripts resolve the root themselves. If the cwd isn't in a repo, stop.
- Never ssh anywhere, never run services or deploys, never open device sockets.
- `check`, `audit`, `tickets` are read-only on tracked files. They write only under `.agent/`
  (ignored globally via `~/.config/git/ignore`; confirm with `git check-ignore -q .agent/x`).
- `rebaseline` writes exactly one tracked file, `.codeshape/baseline.json`, and leaves it unstaged
  for the user to commit (a refactor ticket's orchestrator commits it as the branch's final commit).
  Nothing else writes it except backend-layout's `check_layout.py rebaseline`, which replaces only
  its top-level `layout` key (drift_check keeps that key when it rebaselines); hooks are read-only.

## Files

Scripts live in `~/.claude/skills/consolidate/` (canonical; `~/.codex/skills/consolidate/` holds only this SKILL.md):
- `drift_check.py`: stdlib-only measurement with three modes, `check` / `ratchet` / `rebaseline`;
  the only script these instructions run. Enforced metrics: per-file line counts (scripts and
  stylesheets: `.css`, `.scss`, `.sass`, `.less`), Python function lengths (exact, `ast`),
  escape-hatch markers (`sys.path` hacks, dual import guards, `as any`, `type: ignore`, lint-disable,
  bare `except`, and `!important` in stylesheets). Advisory only: JS/TS and shell function lengths
  (heuristic), helper names defined in several non-test files (a name match, not clone detection),
  and the organization metrics below. Paths are relative to the git root whatever the cwd; renames
  are followed via `git diff -M` so an unchanged file keeps its allowance.
- Sibling modules, loaded by `check` only (the ratchet path never imports them): `org_metrics.py`
  collects and prints the organization metrics from `css_metrics.py` (color literals in stylesheets
  outside a file named like palette/tokens/theme/variables, SCSS `$x:` lines skipped; a class, id or
  attribute selector defined in two stylesheets under the same @media/@supports/@container/@layer/
  @scope context), `import_graph.py` (Python import cycles via `ast`, module-level imports only;
  JS/TS cycles over relative static imports, type-only imports skipped; grab-bag modules: JS/TS
  named imports that split into disjoint importer groups, tests not counted as importers) and
  `cochange.py` (source files in different top-level folders changed together 3+ times in the
  last 200 non-merge commits, commits over 10 files and test files skipped). A metric that errors is
  printed as skipped; none of them ever fails a run.
- `tests/`: `python3 -m unittest discover -s tests`, run from this directory.
- `stop_hook.py`: agent-side Stop adapter. Automatic checks require successful source-edit
  evidence in this session's **current user turn**, matched by exact Claude `prompt_id` / Codex
  `turn_id` in its transcript by `turn_activity.py`.
  A read-only researcher gets no ratchet, exception, missing-baseline, review or rebaseline messages,
  even if another agent edits or commits in the same checkout. Git history, a clean tree and a
  previous turn's writes are not evidence that the current turn owns the work.
- `turn_activity.py`: bounded, read-only transcript parser. Recognizes successful Claude Write/Edit/MultiEdit results and Codex structured
  `patch_apply_end` / `item_completed: FileChange` events, not unstructured tool output.
  Ignores failed edits, reads/searches, ordinary shell output, docs/notes, policy files, configured generated/vendor
  output exclusions and edits outside this checkout. Missing transcript/turn IDs or unknown evidence fail quiet; arbitrary
  scripts and delegated changes without file evidence still need the orchestrator's explicit check.
- Repeat protection: an atomic per-session, per-checkout, per-user-turn claim is recorded before
  work is requested. Repeated Stop events are silent even if stop_hook_active is missing. Without
  a session ID, the transcript's absolute path is the stable fallback (never a process ID).
- Automatic WORSE/EXCEPTION notices concern only files this turn edited; aggregate marker counts
  cannot be attributed and remain available through manual `check`/`ratchet`. Two writers changing
  the same file still require human/agent judgment about which lines belong to whom.
- Thermonuclear's default remains 400. It now counts successful attributable edit/patch payload
  lines, accumulated across source-writing turns, rather than subtracting repo-wide Git diff totals.
  Full-file writes count the supplied content, so this is a review trigger estimate, not a LOC metric.
  A request credits those lines; it does not prove that review ran. Research-only turns never trigger
  pending reviews. Follow the current global model-delegation policy, not hard-coded family fallbacks.
- Automatic rebaseline requires zero reported repo-wide regressions, a clean working tree and at
  least three measured improvements in source files this turn actually edited. At most one such
  request is issued per session/check-out. It preserves existing commit/push authorization and must
  be skipped if ownership is uncertain or the task is research-only. No task acquires commit/push
  permission merely because the branch was already pushed. The hooks themselves never commit.
- Existing `UserPromptSubmit --record` registrations remain compatible but are now no-ops; no new
  hook registration or trust prompt is needed for this fix. State stays outside the repository under
  `~/.cache/codeshape/`. Explicit skill invocations still inspect the repo normally.
- `ticket-template.md`: the ticket prompt skeleton for `tickets` mode.

Per repo:
- `.codeshape/baseline.json` (tracked): what the ratchet compares against. Created and updated
  only by `rebaseline`. Worktrees, the other clones of the same remote, and the Pi all see it
  through git.
- `.codeshape/config.json` (tracked, optional): `{"file_lines": 800, "func_lines": 80,
  "exclude": ["glob", ...], "enforce_tests": true, "hook_mode": "advisory", "review_lines": 400}`
  (`review_lines: 0` turns the review trigger off for that repo). Changing limits makes the baseline
  incomparable until the next `rebaseline`; the check says so instead of guessing. Other blocks
  (the `react-app` skill's `css` and `structure`) belong to other tools; drift_check ignores them.
- `.agent/consolidation/metrics-latest.json`: the most recent `check` output.
- `.agent/handoffs/refactor-audit.md` and `.agent/consolidation/tickets/`: audit and tickets.

Exceptions: a file that should stay large carries a comment `codeshape: allow-size <reason>`
(or `allow-functions`, `allow-all`; `allow-marker` on the same line as an escape hatch), or the repo's
`config.json` lists `{"path": "glob", "file_lines": null, "func_lines": 200, "exempt": false,
"reason": "..."}` under `exceptions`. Both are tracked and reviewable. The ratchet never blocks on an
exception, but every new one since the baseline is printed as an `EXCEPTION` line and the hook shows
it to the user once per session, so an agent cannot quietly exempt itself. `check` lists all
exceptions in force. Removing an exception later does not fail by itself; only growth after that does.

No baseline: if no committed file is over the limits, the ratchet enforces size rules against an
implicit empty baseline, so a new repo is covered from its first commit with no setup. If committed
files are already over, automatic notices are limited to source-writing turns, once per session;
research-only turns stay silent.

Coverage and rollout: each baseline records what it measured in a `coverage` field (source
extensions and marker keys). The format stays `version: 2` and `limits` keeps exactly
`file_lines`, `func_lines` and `enforce_tests`, so an older checker reads a newer baseline unchanged
(it ignores `coverage`, the stylesheet entries and the `important` count). A baseline without
`coverage` (written before stylesheets were measured) is taken to cover the original script
extensions and six markers; stylesheets and any marker key it lacks are advisory there: `ratchet`
prints one "not ratcheted until rebaseline" line and never fails on them, and `check` prints a
"rebaseline would grandfather" section listing the uncovered files over the limit and the uncovered
marker counts. After the next `rebaseline` they are ratcheted at their current size, like any other
file. A future extension or marker key rolls out the same way with no special case. No baseline:
stylesheets count toward the implicit empty baseline (there is nothing to grandfather), so a clean
repo that commits a stylesheet over the limit is reported as already over and not enforced.

Known gaps, stylesheets: inline `<style>` in HTML is not scanned (`.html` is not a source extension),
and colors in JS (inline styles, canvas) are not counted. Duplicate selectors compare only rules not
nested in other rules, and indented `.sass` gets the color count only. JS/TS import cycles miss
paths through aliases (tsconfig `paths`, package `imports`), which are not resolved.

The ratchet's rules: a file over the limit may not grow; a file may not cross the limit; a Python
function over the limit may not grow and no function may newly exceed it; marker totals may not
rise. Each is checked independently (shrinking one thing never buys room for another). Known gaps,
by design: a new file under the limit made of short functions passes regardless of cohesion;
duplication that isn't a name match is only reported, never enforced. Those are review matters.

## check (default)

1. Run `python3 ~/.claude/skills/consolidate/drift_check.py check --json-out .agent/consolidation/metrics-latest.json`.
2. Report in a few lines: whether there is a baseline, the regression and improvement counts since
   it, and the 3–5 most notable items (files over the limit, longest functions, marker changes,
   advisory duplicate names, and the organization metrics when they point at something concrete).
   If a "rebaseline would grandfather" section is present, repeat it: those stylesheets and marker
   counts are not ratcheted until the user rebaselines. Don't read source files in this mode; the
   script output is the evidence. Mention unparsable files if any were skipped. If the output has an "exceptions in
   force" section, repeat it: those files are deliberately exempt, with the reason given, and are
   not cleanup candidates. Any `EXCEPTION` line (new since the baseline) is for the user to judge;
   quote its reason verbatim.
3. No baseline: say so and recommend `rebaseline` (after confirming the tree is in a state the
   user wants to grandfather) or `audit` if there is no `.agent/handoffs/refactor-audit.md`.
4. If there are regressions a cleanup is likely due; end with the next step, `audit`.

## rebaseline

1. Confirm with the user that the current tree is the state to grandfather (typically right after
   a reviewed cleanup merged). Do not run this to make a failing ratchet pass during feature work.
   The script refuses on a dirty tree (uncommitted work may still change); commit first, or pass
   `--allow-dirty` only when the user explicitly wants the uncommitted state recorded.
2. Run `python3 ~/.claude/skills/consolidate/drift_check.py rebaseline`. Report the HEAD it recorded and remind the
   user to commit `.codeshape/baseline.json` with their next commit. Don't stage it. The new baseline
   records its coverage, so anything `check` listed under "rebaseline would grandfather" is ratcheted
   at its current size from then on; say so. Where backend-layout's `check_layout.py` is installed,
   run `python3 <scripts-dir>/check_layout.py rebaseline` in the same step, after this one: it writes
   the `layout` key.

## audit

1. Run `check` first so the metrics are fresh.
2. Read the repo's AGENTS.md (and README / docs it points to), the previous
   `.agent/handoffs/refactor-audit.md` if any (note its open Follow-ups and Do-not-touch list),
   and `git log --since=<baseline date or 4 months>` to find hot vs dormant areas.
3. Audit read-only. Use the metrics to aim: files over the limit, the longest functions, duplicate
   helper names, marker hotspots. Weight recently active areas higher. Files listed under
   "exceptions in force" are not candidates for splitting or trimming: the owner or a previous
   agent decided they stay as they are, for the reason recorded. List them in a short "Exempt"
   note instead, and only question an exception if the audit finds its reason no longer holds. If you can spawn subagents,
   fan out one per area (at most five), each returning the sections below with file:line evidence;
   otherwise do it directly. Verify every finding you keep against the code. If `jscpd` (or its
   Rust port `cpd`) is installed, run it with `--min-tokens 50` for real copy-paste pairs.
4. Write `.agent/handoffs/refactor-audit.md`, replacing the old one. Header: repo, audit date,
   HEAD sha, and "Use this as the spec for refactor tickets. Every ticket: zero behaviour change,
   tests green before reporting." Sections:
   1. **Overall shape**: layers as documented vs as built; conventions and where they break down.
   2. **Ranked candidates**: what's wrong (concrete examples, file:line), the target shape,
      refactor vs rewrite, size in agent-hours, risk (live service? hardware? data? test coverage?),
      and the machine-checkable gate that would prove no behavior change.
   3. **Cross-cutting**: duplication, shared vocabularies, contracts, config, logging, CLI
      conventions, dead code.
   4. **Do not touch**: carry forward the previous list, re-verified.
   5. **Test situation**: how to run the suites, real counts, which tests protect a refactor and
      which are brittle.
   6. **Proposed "where things live" map** for the repo's AGENTS.md: the shared module for each
      recurring concern, one line of description each, so an agent that reads only the map knows
      what exists. This is the audit's most valuable output; the duplication problem is a context
      gap, not a capability gap. If AGENTS.md has a map, list only corrections. Don't edit it.
   7. **Proposed import contracts**: 2–4 rules the code should obey, as `import-linter` contracts
      (Python) or `dependency-cruiser` rules (JS/TS), each from a real inversion the audit found,
      with a planted-violation meta-test. Where they run (agent-side, or the test suite, which
      would also bind human changes) is the owner's decision; say so.
   8. **Follow-ups**: open items carried forward plus new ones.
5. Reply with the ranked list (one line each: title, size, risk) and offer `tickets`. Recommend
   "nothing warrants a rewrite" unless the evidence says otherwise.

## tickets

1. Read `.agent/handoffs/refactor-audit.md`. If it's missing or clearly older than the code it
   describes, say so and suggest `audit` first.
2. Confirm the available delegation tools before writing executable briefs.
3. For each requested item (default: all ranked items), fill `ticket-template.md` and write
   `.agent/consolidation/tickets/rank_<N>_<topic>.md`. Rules:
   - Every placeholder replaced; no `{{` left (grep to confirm).
   - Steps split decide/apply and tagged [T1]/[T2]/[T3]; protected, contract-bearing, or untested
     code stays [T3]; byte-verifiable work first; shim-first for file splits.
   - Each ticket names at least one gate beyond the test suite and how to produce its before file.
   - Preconditions name earlier tickets that must merge first.
   - Never write a ticket that splits, trims, or de-marks a file that has an exception in force;
     if a ticket must touch such a file, it keeps the file's directive and says so.
   - Prefer several small tickets to one large one; after a catch-up round, a ticket should be a
     few hours of agent work, and the ratchet should make most of them unnecessary.
   - The template's review section has the orchestrator run the `thermo-nuclear-code-quality-review`
     skill on the branch diff; keep that step.
   - Each brief carries the Code shape rules, names who updates the "where things live" map, and
     tells workers to report conflicts rather than force them; the orchestrator runs the ratchet
     after workers finish and before reporting.
4. Reply with the list of files and a one-line copy command for the first:
   `/usr/bin/pbcopy < <absolute path>` (macOS; on a headless host give the path instead).
