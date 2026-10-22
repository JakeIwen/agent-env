# CLAUDE.md — public snapshot

Private context and machine-specific sections omitted. Paths in angle brackets
are placeholders; see the repository README.

Claude orchestrates; GPT models handle delegated work.

## Working conventions (kept in sync with ~/.codex/AGENTS.md)

- `c/p` is shorthand for "commit and push": when a message is just `c/p` (or
  uses it as a standalone instruction, e.g. "looks good, c/p"), treat it
  exactly as if the owner had typed "commit and push".
- Never commit to or push to the default branch (`main`, `master`, or
  whatever the remote's HEAD names) of a repo that isn't the owner's: his repos
  are under `github.com/JakeIwen`, so check the remote URL first; a repo
  with no remote counts as his. This holds even for `c/p` or an explicit
  "commit and push": on someone else's default branch, stop and offer to
  put the work on a new branch instead.
- Commit and push by default in the owner's repos (as defined above): when a
  task that changed files in one is done and verified, commit and push
  this session's changes without waiting for `c/p` or `+cp` and without
  asking. This is standing authorization. Follow `+cp`'s rules (this
  session's files staged by path, tidyings in their own commits, whole
  suite green). Leave the work uncommitted, and say why, when the owner asked
  for that, when the work is unfinished, or when the suite is red. In a
  repo that isn't his, commit nothing unless he asks, and then follow the
  default-branch rule. With no remote, commit locally and never add one.
  This never authorizes a deploy (that is `+cpd`). Delegated workers
  commit only when their brief says to.
- In a repo that isn't the owner's, never edit its AGENTS.md (or CLAUDE.md)
  unless that file itself specifically says to, and never add a test
  runner or suite entry point; report the gap instead.
- Delegated workers stay quiet until they finish. Every brief tells them to
  report once, in their final result, and to message the parent mid-run only
  when blocked on a file or decision another worker owns. Each worker
  message starts a new parent turn with its own wrap-up, and those bury the
  real report. Don't schedule wake-ups or timers to watch workers:
  completion notices arrive on their own. If one is set anyway, cancel it
  (`ScheduleWakeup` with `stop: true`) as soon as the work it watches is
  done.
- Long replies: when a final message to the owner would run past one terminal
  screen (about 50 rows at his usual width, roughly 450 words; tables and
  blank lines count), put the reply in a local page instead: save it with
  the `+art` skill's script and `--agent claude`, but no `--hosted` and no
  Artifact publish, with the reply itself as the page body (that skill's
  "Long replies" section). The terminal message then leads with anything
  he must act on, written out in full per Terminal handoffs (that part
  doesn't count toward the length), then a summary of up to five lines
  and the links from the skill's step 4. Not for reports a delegated
  worker returns, output a script consumes, or when the owner asks for the
  answer in the terminal.
- Phone notifications (ntfy): the hooks alert only when a session is
  blocked on a permission prompt or question. When the owner asks to be
  notified (e.g. "ping me when it's done"), send one alert when the task
  finishes, or sooner if it stalls waiting on him:
  `/usr/bin/python3 <agent-env>/hooks/claude_ntfy_notify.py
  --send "<project>" "<one-line result>" default`. One alert per request,
  not per turn.
- After making changes, do not print diffs or patches unless explicitly asked.
  Summarize changed files and behavior instead.
- Whenever the owner must configure, authorize, restart, install, or open something
  himself, give exact copy-pasteable CLI commands. Prefer CLI routes over GUI
  instructions; if no CLI route exists, say so explicitly and still provide
  commands for every CLI-capable part.
- If a request is materially ambiguous, ask a concise clarifying question
  before acting. If a safe assumption would not materially affect the outcome,
  state the assumption and proceed.
## + commands (kept in sync with ~/.codex/AGENTS.md)

the owner sends these alone or appended to a message; text after one is its
focus (`+ir the dashboard 502s`), and combined ones run in the order
written (`+ir +cp`).

- `+cp`: commit and push, the same as `c/p`. Follow the default-branch
  rule and Code shape's commit rules (whole suite green, tidyings in their
  own commits). Stage this session's files by path; other sessions'
  uncommitted changes in the repo stay out.
- `+cpd`: commit, push and deploy. Deploy the way the repo's AGENTS.md or
  deploy docs say, in their order (some deploy first and commit what was
  deployed), then check the live result: health endpoint, service status,
  or the page in `browser_clean`. With no documented deploy, say so and
  stop after the push.
- `+rcp`: review the repo's uncommitted work, then `+cp` it. Run the `+id`
  script to see who owns what, read the whole diff including untracked
  files, check for bugs, leftovers (debug output, temp files, secrets) and
  code-shape problems, fix the small ones, and run the whole suite. Commit
  in logical groups and push. Leave out files an open session is still
  working on and local data that shouldn't be tracked. Stop for the owner only
  on a decision that is really his (work abandoned midway, conflicting
  edits from two sessions, someone else's default branch), and commit
  everything else before asking.
- `+ir`: investigate and remediate. Observe the problem live, find the root
  cause rather than the symptom, fix it, and verify the fix the way the
  problem was seen; check whether the same cause bites elsewhere. Carry it
  through without stopping to ask, except before an action that is
  destructive, outward-facing, or outside what the task authorizes. Report
  the cause, the fix, the evidence it works, and anything left unfixed.
- `+le`: itemize this session's loose ends, changing nothing. Cover work
  started but unfinished, steps skipped or unverified, uncommitted or
  undeployed changes, questions and decisions still waiting on the owner,
  promised follow-ups, temporary files or processes left behind, and
  handoffs he hasn't run. Number them; for each, say who acts (agent or
  the owner) and the exact next step. If there are none, say so in one line.
- `+id`: find which sessions own the repo's uncommitted work. Run
  `/usr/bin/python3 <agent-env>/tools/uncommitted_owners.py` in the
  repo: it maps each uncommitted file to the Claude and Codex sessions that
  edited it and says which sessions are open, in which iTerm tab. Read each
  session's tail to judge where it stands, then report:
  - Open sessions: the iTerm tab name, the files it owns, and its apparent
    state. Leave its files alone.
  - Closed sessions with loose ends: what's left, and a handoff script (per
    Terminal handoffs) that resumes it from its own folder.
  - Closed sessions whose work looks finished: from each session's folder,
    one at a time, resume it headless with a `c/p` scoped to its files
    (`claude -p --resume <id> --permission-mode bypassPermissions "c/p,
    only <files>"` or `codex exec resume <id> "c/p, only <files>"`), and
    report the commits.
  - Files no session explains: their apparent status (in progress,
    finished, local data) and what to do with them.
  `+id` commits nothing itself.
- `+prompt`: write a self-contained prompt for another agent to do the
  task that follows. Include the goal, the context and decisions from this
  conversation it can't rediscover, file paths, constraints, and how to
  check the result; save it per Terminal handoffs (text for another app)
  and give the `pbcopy` command. With no task, hand off this session:
  bring the workstream's handoff note up to date (Cross-agent handoffs),
  then write the prompt that has a new agent read it and continue.
- `+gl`: make this a global rule. In the config-maintenance session, apply it to the
  four globals as `<config-root>/CLAUDE.md` describes; anywhere else, write a
  `+prompt` for a config-maintenance session (start one in the config directory) that states
  the rule and why.
- `+ux`: audit the app's UI/UX and fix what you find. Run it locally and
  use it in `browser_clean` the way a person would, at phone and desktop
  widths, on every page and control. Fix errors, broken or confusing
  flows, clutter and layout problems; prefer hover tooltips or info icons
  to explanatory text scattered across the page. Report what changed,
  with before and after screenshots where they help.
- `+both`: make the same change on the other machine. Mirror it to the Pi
  (or the Mac) by the route the repo or `<config-root>/CLAUDE.md` gives (deploy
  script, `scp`, or edits over `ssh <remote-host>`), verify it there, and report
  anything that has to differ between the two.
- `+n`: send one ntfy when this task finishes, or sooner if it stalls on
  the owner. Use the command under Phone notifications.
- `+tests`: audit the repo's tests and cut the ones that check nothing
  real. Delete duplicates, tests of retired behavior, and tests that only
  exercise mocks or grep source text; rewrite weak ones to assert behavior
  through public entry points; keep the suite green, and report what went
  and why.
- `+sa`: use subagents where independent scopes reduce elapsed time. Give each
  worker a self-contained brief; the parent integrates and verifies the result.
- `+art`: summarize this conversation as an Artifact, narrowed to any focus
  written after it (`+art just the wiring findings`). Write the body by the
  content and markup rules in `~/.codex/skills/codex-artifact/SKILL.md` and
  save it with that skill's script, adding `--agent claude --hosted
  <scratchpad>/<name>.html`: the page lands in `~/.agent/artifacts/`
  (pruned after 90 days unless pinned) and the hosted copy is ready to
  publish. Publish the hosted copy with the Artifact tool, then give the
  hosted link and the local `file://` URL. Re-running `+art` in the same
  conversation passes `--out` and republishes the same file. Without the
  Artifact tool, the local page is the deliverable.
- `+cmd`: list these commands, one line each. A hook answers a bare `+cmd`
  without a model turn; when it comes with other text, run
  `/usr/bin/python3 <agent-env>/hooks/plus_commands.py` and show its
  output as is.

## Terminal handoffs (kept in sync with ~/.codex/AGENTS.md)

The terminal UI hard-wraps long lines, so anything the owner copies from the
screen picks up real line breaks once it wraps. A single command under about
80 characters can be shown inline. For anything longer or multiline, create
the file yourself and give him one short command; never present it for
copying from the screen, and never make him paste heredocs or long quoted
multiline commands.

The terminal also buries earlier messages: tool output, review hooks, and
later progress notes push anything said mid-turn off the screen, and the owner
reads only the final message of a turn. So whatever he must act on (a command
to run, a file to open, a question, a choice) goes in that final message,
written out in full even if it was already given earlier in the turn. For a
handoff script that means the script's contents again (they are rarely more
than a dozen lines) followed by the command that runs it; the owner prefers the
repeat over the token cost. Never point back at it ("the setup command
above", "the previously provided script"). When a hook or a follow-up step
extends a turn after a handoff was given, repeat the handoff at the new end.
Lead the final message with the action and its exact command, then the
status and what is still blocked on it.

One request often runs over several turns (worker messages, completion
notices, a follow-up change), and each turn's final message may be the one
the owner reads. So the report that closes the work covers the whole request,
not just the latest change: every item he asked for or asked about, and
every open question or decision, carried forward until he answers it. A
later turn never shrinks a finished report into a one-line status; if it
adds nothing, it says so in a line and repeats the full report, or the link
to the page that holds it when the report is long. When more than one thing
waits on him, lead with all of them, so a single action doesn't read as
the whole message.

Keep handoff files in `/tmp/clip` (create or tighten it with
`mkdir -p -m 700 /tmp/clip && chmod 700 /tmp/clip`). Name each file with a
short description plus the current time as HHMM (`example-project-restart-1432`)
so a later handoff never overwrites one already in his shell history.

Commands he runs himself (sudo, his login session, or anything an agent shell
can't do):

- Write a script that starts with `#!/bin/zsh` and `set -eux -o pipefail`,
  so it stops at the first failure and echoes each command as it runs. Use
  absolute paths, and `cd` inside the script as needed.
- Put `sudo` only on the lines that need it. Never tell him to run
  `sudo zsh <script>`. If any line needs sudo, take the password up front
  and keep the grant alive so a long step never stops on a prompt: right
  after the `set` line add `sudo -v`, then
  `( set +x; while kill -0 $$; do sudo -n true; sleep 50; done 2>/dev/null ) &`
  and `trap "kill $! 2>/dev/null" EXIT`.
- Run `zsh -n <file>` yourself to check syntax, show the script's contents
  in your reply so he can read what will run, then give
  `zsh /tmp/clip/<name>`. Running it through the interpreter means it needs
  no execute bit.
- A script can't change his shell's state: `cd`, `export`, and venv or nvm
  activation vanish when it exits. When that state is the point, write the
  file without any `set` options (they would persist in his shell, and `-e`
  would close it on the first error) and give `source /tmp/clip/<name>`.

Text for another app (JSON for a web form, config for a settings field, a
message to a person):

- Write the exact payload as UTF-8, preserving quotes, Unicode, and real
  newlines, and validate the format when you can, such as parsing JSON. Give
  `/usr/bin/pbcopy < /tmp/clip/<name>`.
- Never claim the clipboard was updated unless a clipboard tool reported
  success.

If he is already stuck at `heredoc>`, tell him to press Ctrl+C first.

## Web pages (kept in sync with ~/.codex/AGENTS.md)

- Pages the owner asks for are working tools or reference docs for him, not
  marketing. No hero section, slogan, tagline, eyebrow/kicker label,
  mission line, or copy that describes the site or announces what was built.
- Title the page with its plain name at normal heading size. The first
  screen is the content itself (the index list, the guide, the controls).
- This overrides plugin/skill design guidance, including the Sites
  skill's "visual thesis" and "memorable visual decision."

## Local services

- Always-on local apps (launchd on the Mac, systemd on the Pi): before
  creating, installing, restarting, debugging or publishing one, or picking
  a port, load the `local-service` skill. It holds the service contract,
  the controller verbs and the installed-services inventory.

## Code shape

Agent-built repos decay one reasonable feature at a time: helpers get copied
because the agent doesn't know one exists, and files grow because the last
feature went there. These rules are cheap per change. Safety, the task's
authorization, and leaving unrelated code untouched always outrank them;
the red-test rule below is the one carve-out.

- Before writing a helper (parser, time or number helper, file writer, CLI
  confirm gate, HTTP client, validator), read the repo AGENTS.md "where
  things live" map and grep the shared library. Reuse or extend what exists.
  If you copy anyway, say so in your report. Name shared code so it can be
  found: descriptive names, one concern per file, a file named for what it
  exports, and shared modules grouped by feature (`layout/`,
  `screenshots/`), never by kind: no grab-bag `utils`, `helpers`, or `hooks`
  folder.
- When you add a shared module, add it to the map in the same change.
- Entry points only wire things together: a shell holds layout and routing,
  `main` bootstraps. Code, styles, and hooks with one consumer live beside
  it; when a second consumer appears, move them to the nearest common
  folder. Content and configuration (copy, URLs, slug tables) live in
  content or config modules, not inside the functions that render or process
  them. Each constant (URL, path, magic number) is defined once. Where the
  repo sets no convention, follow the framework's common one; a framework
  skill, where one exists, holds the repo-level layout and gates: load it
  before creating or reorganizing a repo or adding modules to one
  (`react-app` for React/Preact web apps, `python-tool` for the owner's Python
  repos, `mac-pi-repo` for code that runs on both the Mac and the Pi,
  `backend-layout` for services, CLIs, workers and script folders in
  Python, Node, shell or Go).
- Styles: design values used in more than one place are CSS custom
  properties in one palette or tokens file, and themes and dark mode
  override the tokens there and nowhere else. Prefer plain custom properties
  to adding a preprocessor for variables.
- Size limits (default 800 lines per file, 80 per function; a repo's
  `.codeshape/config.json` can override) are review triggers, not design
  rules. If the file or function you'd add to is already over, put the new
  code in a sibling module or a new function and call it from there; a small
  extraction that makes room is fine. Never delete comments, compress code,
  or add shims only to satisfy a count, and don't restructure existing code
  during a feature to make the number move.
- Exceptions are explicit, never silent. A file that should stay large (a
  generated table, a schema, a state machine read top to bottom) gets a
  comment `codeshape: allow-size <reason>` in the file, or an entry in
  `.codeshape/config.json`; `allow-functions`, `allow-all`, and
  `allow-marker` (on the same line as an escape hatch) work the same way.
  Write the reason for a reviewer, mention it in your report, and never add
  one just to pass the check; every new exception is shown to the user. The
  prose rules take the same route: do what the task needs and disclose the
  departure.
- Shared vocabulary is declared once: a status, state, or kind set used in
  more than one file is one named enum, union, or constant set, and
  comparisons go through it. Dispatch on a kind, slug, or status through one
  keyed map over that set, not through conditionals repeated in several
  places, so a misspelled key fails the type check. A record that crosses a
  module or process boundary has one canonical definition (dataclass,
  TypedDict, TS type, schema). Keep runtime validation at trust boundaries;
  a static type is not input checking.
- About to repeat a workaround (`sys.path` edits, import guards, per-file
  shims, copy-pasted error handling)? Stop and report the structural cause
  instead of adding another instance.
- Prefer tests that call public entry points and assert on behavior over
  tests that set private attributes or grep source text. Structural tests
  that assert architecture (import contracts, "this unit references a file
  that exists") are fine. Filenames and paths that a deploy or service unit
  depends on are contracts; keep them, with a shim if the code moves.
- A test is passing, skipped with a stated reason, or deleted; "known
  failing" is not a state, and a commit never lands with a red test, even
  one the task didn't touch. This is the one exception to leaving unrelated
  code untouched; the scope rules hold otherwise. On meeting a red test the
  task didn't cause: if it drifted from a deliberate code change, update it;
  if it fails only for the environment (tool, OS, interpreter version,
  hardware), gate it with a skip that names the reason; if the code it
  covered is gone, delete it and say so in the commit message; if it exposes
  a real bug, fix it when the fix is small and in scope, otherwise stop:
  leave the work uncommitted and report the bug to the user as a bug, not
  as pre-existing. A skip that names the bug as its reason is not an exit.
  A missing dependency, secret, service, or build step is a broken setup,
  not an environment: fix the setup rather than gating the test.
- Before committing or reporting done, run the whole suite, not just the
  tests near the change. A repo with no single entry point that runs
  everything and exits nonzero on any failure gets one, named in its
  AGENTS.md, unless the repo is someone else's: then report the gap. Run a
  fail-fast suite until it is green; one red case hides every case behind
  it. Briefs to delegated workers carry this rule; "leave pre-existing
  failures alone" is not an allowed instruction.
- Comments explain why. Incident stories, trip notes, and changelogs go in
  `docs/` or the commit message, not in code comments or growing READMEs.
- When committing, keep tidyings (rename, move, extract,
  dedupe) in their own commits, separate from behavior changes. Verify a
  pure reorganization by comparing output before and after (rendered DOM,
  computed styles, CLI output, API responses), not by reading the diff.
- Where a repo has `.codeshape/baseline.json`, an agent-side check reports
  regressions against it at the end of a turn (a file over the limit grew, a
  function went over, an escape hatch was added). Fix what is inside the
  task's scope; report what isn't. Never restructure live-service code to
  satisfy it. The baseline changes only through `rebaseline`, run by the
  user or as the final, separate commit of a reviewed refactor branch. A
  repo with no baseline and nothing over the limits is enforced as if it
  had an empty one, so new repos need no setup.
- When delegating, the brief carries these rules, names who updates the map,
  and lets the worker report conflicts instead of forcing them. The
  orchestrator runs the check after workers finish.
- Batch cleanup is separate work (the `consolidate` skill). Don't start one
  during a feature; list candidates in your report. A refactor ticket's own
  brief governs that ticket; these rules govern feature work.

## Cross-agent handoffs

Claude Code and Codex both work on this machine's repos. For substantive
multi-session work, keep a handoff note at `.agent/handoffs/<workstream>.md`
(kebab-case, one file per workstream) in the root of the repo the work is in
(`git rev-parse --show-toplevel`), wherever the session started. Outside any
repo, use the project's top-level folder (where its AGENTS.md or README
lives), or `~/.agent/handoffs/` for machine-wide work such as global config.
When starting or resuming substantive work, list the handoffs in that
location and read any plausible matches; reuse a match before creating a new
one. Record only what another agent needs to continue: objective, key
decisions, discoveries, work done/remaining, verification status,
recommended next step. Replace stale information rather than appending.
Durable project facts belong in the project's AGENTS.md instead. When a
workstream is finished, promote anything durable to the project's AGENTS.md
(or the global instructions, for machine-wide work) and delete the handoff
file. Code, git state, and test results outrank handoff notes.
