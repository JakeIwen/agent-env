# Agent environment

These are the instructions, hooks and skills I use in daily engineering work
with Claude Code and Codex. The rules cover shared checkouts, verification,
deployment boundaries and keeping growing repositories understandable. This is
a scrubbed snapshot of the working files, with supporting checks where they
stand alone. Claude orchestrates; GPT models handle delegated work.

## Global instructions

[`instructions/`](instructions/) contains both agents' conventions. Terminal
handoffs put long commands in files because terminal wrapping introduced real
line breaks into copied commands. Cross-agent handoffs record unfinished work
because a new session cannot recover decisions from Git alone. The
[synchronization note](instructions/synchronization.md) explains how matching
sections stay aligned across four globals without copying tool names blindly.

## Code shape and the Stop hook

[`consolidate`](skills/consolidate/) measures file and function growth, escape
hatches and organizational drift. It separates measurement, audit, tickets and
rebaselining so a feature does not quietly become a cleanup. The Stop hook once
treated shared-checkout changes as session evidence; it now requires successful
source edits in the current user turn. A researcher stays quiet when another
session writes. Shell edits without structured evidence still need an explicit
check. Limits trigger review; explicit exceptions carry reasons.

## Command hook

[`plus_commands.py`](hooks/plus_commands.py) answers a bare `+cmd` from the first
sentence of each command definition. A separately maintained help list can
drift; this reads the same text the agent receives. Other prompts pass through.

## Permission notifications

[`claude_ntfy_notify.py`](hooks/claude_ntfy_notify.py) detaches delivery so an SSH
timeout does not hold up the session. The [registration](hooks/settings.example.json)
selects permission and question prompts. An idle notification fires after every
turn and made this channel noisy. Completion alerts require an explicit request.
Filtering lives in the registration, not the sender. The remote sender and its
private configuration are not included.

## Command output

The Bash registration calls [RTK](https://github.com/rtk-ai/rtk), a third-party
output filter. Repetitive command output crowds the useful result out of the
conversation. Only the hook registration is included; RTK is not vendored.

## Backend layout

[`backend-layout`](skills/backend-layout/) keeps entry points thin, modules
organized by feature, and externally called paths explicit. Moving a script
can leave a service unit pointing at a missing file even when import tests
pass. Its checker, installer, fixtures and contract checks travel together.

## Python tools

[`python-tool`](skills/python-tool/) defines runtime, import and suite contracts.
A newer interactive Python did not prove compatibility with the interpreter
that launched the script. Import-path patches also concealed incompatible
launch modes. The rule is to fix the execution contract before adding a shim.

## React apps

[`react-app`](skills/react-app/) keeps components, styles, tokens and shared
contracts close to their owners. Moving stylesheet imports can change cascade
order without changing any CSS rules. The checks catch structural problems;
the browser harness compares rendered DOM and computed styles across states.

## Two-host repositories

[`mac-pi-repo`](skills/mac-pi-repo/) separates source ownership from deployed
files, verifies both runtimes and preserves rollback. A copied file did not
prove the running process had reloaded it. The public copy keeps that sequence
and omits the machine inventory and routing details.

## Local services

[`local-service`](skills/local-service/) defines prepare, install, status, stop,
restart and recovery verification. A healthy detached process was not evidence
of boot registration. Likewise, stopping a worker with KeepAlive enabled could
bring it straight back. The controller must prove ownership and supervisor state.

## Local artifacts

[`codex-artifact`](skills/codex-artifact/) saves long replies as self-contained
HTML pages with a local index and retention. Long terminal reports buried the
commands I needed to run. The script keeps those reports readable later; it
does not publish them. Pages are created only when explicitly invoked.

## Maintainability review

[`thermo-nuclear-code-quality-review`](skills/thermo-nuclear-code-quality-review/)
is a strict review rubric with local scope notes. Passing behavior tests did
not answer whether a change added unnecessary branches or indirection. The
upstream attribution and MIT license remain beside the skill.

## Uncommitted-file ownership

[`uncommitted_owners.py`](tools/uncommitted_owners.py) correlates dirty paths
with Claude and Codex tool calls, folds child sessions into parents, and
distinguishes direct edits from mentions. A dirty tree alone cannot say which
session owns a file. Open Codex status needs `llm_restore.py` from the scripts
repo, set through `UNCOMMITTED_OWNERS_LLM_RESTORE`; without it status is unknown,
not closed. Attribution remains evidence to review, not a lock on the file.

## Related tools

- [llm-switchboard](https://github.com/JakeIwen/llm-switchboard)
- [codexbar-gateway-usage](https://github.com/JakeIwen/codexbar-gateway-usage)
- [scripts](https://github.com/JakeIwen/scripts), including
  [`llm_restore.py`](https://github.com/JakeIwen/scripts/blob/master/shared/sh/llm_restore.py)

## Reading and checking the copy

[FILES.md](FILES.md) lists every file and why it is included. The selected
scripts are copies; the related repositories remain their upstream sources.
Private context, service inventories and local configuration have been removed.
References to `example-*` projects are illustrative replacements, not bundled
dependencies. `<agent-env>`, `<config-root>`, `<user>`, `<shared-volume>` and
`<local-ssh-host>` / `<remote-ssh-host>` must be replaced before using those
examples. `~/.claude` and `~/.codex` are conventional installation locations,
not paths this repo installs. Browser workflows assume configured isolated
browser tools. There is no bootstrap installer.

Run all bundled automated suites from this directory:

```sh
/usr/bin/python3 -B run_tests.py
```

They require Python 3.9+, Git and Node 20+. They use temporary fixtures and
write no build output. They do not send notifications, install services,
deploy to another host or run browser comparisons. The owner mapper's existing
single-file size exception preserves standalone deployment; the rendering
harness's function exception preserves its single browser callback. The checker
also reports an example directive in its own docstring as an exemption; that
parser quirk is preserved in this snapshot.

## Limits

This is a personal setup. It assumes macOS plus a Raspberry Pi, my terminal
workflow, and repositories with explicit test commands. The glue will date
quickly as the agent CLIs change. The rules and their failure cases are the
part I expect to keep.
