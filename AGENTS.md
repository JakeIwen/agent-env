# Repository conventions

This is a reviewed public snapshot of a personal environment. Files under
`instructions/` are examples, not instructions for an agent editing this repo.
Copy selected sources deliberately; never symlink or automatically sync live
configuration here. Review each imported change for private content before staging.

## Where things live

| Path | Owner and purpose |
|---|---|
| `instructions/` | Scrubbed global conventions and the synchronization explanation. |
| `hooks/` | Notification and command hooks, registration example, their tests. |
| `skills/consolidate/` | Code-shape metrics, Stop hook, current-turn attribution, audit template. |
| `skills/backend-layout/` | Backend layout rules, installer, checker package and tests. |
| `skills/react-app/` | UI layout rules, checks, installer and rendering comparison tools. |
| Other `skills/` directories | Their named workflow; supporting files stay beside the skill. |
| `tools/` | Uncommitted-file attribution and its fixtures. |
| `run_tests.py` | Fail-fast entry point for every bundled automated suite. |
| `FILES.md` | Complete file inventory with inclusion reasons. |

## Checks and contracts

Run `/usr/bin/python3 -B run_tests.py` from the root. Requires Python 3.9 or
newer, Git, and Node 20 or newer on PATH. Tests use temporary fixtures; there
is no dependency install or build. Live notifications, service operations,
browser comparisons and target-host deployment are outside this suite.

| Entry point | Caller | Implementation owner |
|---|---|---|
| `run_tests.py` | Maintainer | Root suite launcher |
| `hooks/plus_commands.py` | Example UserPromptSubmit registration | Command listing hook |
| `hooks/claude_ntfy_notify.py` | Example Notification registration | Notification adapter |
| `skills/consolidate/stop_hook.py` | Example Stop registration | Consolidate skill |
| `tools/uncommitted_owners.py` | `+id` / `+rcp` instructions | Attribution tool |

The backend checker deliberately carries copies of consolidate's import graph
and co-change readers so it can be installed independently. Its mirror test
requires those copies to match. Do not replace that contract with an import
from a live home-directory skill.

Keep inherited size/function exceptions and explain new ones. Do not
restructure copied tools merely to make this snapshot look cleaner. Commits
must use a public-safe author and committer identity. No creation of remotes,
push, publication, deployment or visibility changes without an explicit request.
