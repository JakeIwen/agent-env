<!--
Template for one consolidation ticket prompt. The `consolidate` skill fills every {{PLACEHOLDER}}
and writes the result to .agent/consolidation/tickets/rank_<N>_<topic>.md. The finished prompt is
pasted into a fresh Claude Code session started in the repo; that session orchestrates and reviews.
-->
You orchestrate and review the refactor ticket in {{REPO_NAME}}. Use isolated
worktrees for implementation, inspect the actual diff, and run the tests yourself.
Claude orchestrates; GPT models handle delegated work.

{{ONE_PARAGRAPH_RISK_FRAMING — what this code does in production, what a regression would cost, and what nobody in this session may touch (live devices, services, data dirs).}}

## Context you must read first

- `.agent/handoffs/refactor-audit.md` — the audit dated {{AUDIT_DATE}} (HEAD `{{AUDIT_HEAD}}`). This ticket is §2 item(s) {{ITEM_NUMBERS}}. §4 lists what must not be touched. §5 has the test recipe. Read its Follow-ups section too.
- {{REPO_DOCS — AGENTS.md and any design docs the ticket depends on}}

## Ground rules

- {{PRECONDITIONS — clean tree, not behind origin, earlier tickets merged; each with "if not, stop and report"}}
- Audit line numbers are from `{{AUDIT_HEAD}}`; locate code by name and treat line numbers as hints.
- {{NO-TOUCH RULES specific to this repo: services, deploy scripts, data dirs, live hardware}}
- On protected modules (audit §4): *consuming* a new shared helper or type is allowed when the substitution is mechanical and provably identical; *restructuring* them is not. If a substitution would change behavior, leave it and report the diff.
- Files with a code-shape exception in force (a `codeshape: allow-*` comment, or an `exceptions` entry in `.codeshape/config.json`; `python3 ~/.claude/skills/consolidate/drift_check.py check` lists them) stay as they are. Don't split, trim, or remove their directives; if the ticket must edit one, keep the directive and say so in the report.

## Baseline

{{EXACT COMMANDS to run the relevant test suites, plus how to record counts. Expected counts from the audit. "If anything fails at baseline, stop and report."}}

{{GATES — any machine-checkable equivalence check beyond tests, set up before the first change: payload/JSON snapshot diff, route list diff, --help diff, schema dump diff, replay diff, function-body diff. Say exactly how to produce the before file.}}

## Verification tiers

Tag mechanical, byte-verifiable steps [T1], tested implementation [T2], and
judgment or protected code [T3]. Keep decisions separate from application.

## {{TICKET A TITLE}} (audit §2 #{{N}}), one implementation job, one commit per numbered step

{{NUMBERED STEPS. Rules for writing them:
- Byte-verifiable mechanical work first.
- Split every "dedupe/replace/extract" into: [T1] inventory (paste originals verbatim) → [T3] decide/design → [T2] implement → [T1] verify by diff.
- Shim-first for any file split: package with the old file re-exporting, tests green, then move one module per commit.
- Name the one intentional behavior change, if any, and require a fails-before/passes-after test.
- Parallel jobs only across disjoint files.}}

Acceptance: {{suite green with counts ≥ baseline; every gate diff empty; named size targets; zero behavior change except the named one}}.

{{Optional: ## TICKET B ..., one implementation job, after A lands — same structure.}}

## How to brief the implementer

The implementer starts with zero context. Each brief must be self-contained: paste the relevant audit section verbatim, the tagged step list, the exact files, the exact test and gate commands, the acceptance criteria, and these standing rules:
- Zero behavior change except the change(s) named above.
- {{NO-TOUCH rules repeated: never ssh to devices, never run services/deploys, never touch data dirs, nothing in audit §4 beyond consuming new helpers.}}
- Commit in small steps on the worktree branch, plain-English messages. Do not merge, rebase onto main, or push.
- Finish with: files changed, test and gate output verbatim, {{ticket-specific inventories/tables}}, the delegation split table, and anything unsure.

Then paste this block verbatim:

> **Delegation.** You are the planner, reviewer and final verifier for this ticket, not the sole implementer. Spend your own turns on reading code, making decisions, resolving conflicts and verifying results. Delegate execution to cheaper models through the `Agent` tool, and review what comes back the same way the orchestrator will review you.
>
> **How to delegate.** Each delegated job gets a self-contained brief: the absolute path of your worktree (the sub-agent must `cd` there and edit only under it), the exact files, the exact change, the exact command to verify it, the acceptance criterion, and the standing rules copied from this brief (no behavior change, nothing in the no-touch list). State what the sub-agent must report back, including verbatim command output. Sub-agents do not commit; you commit after you have verified. One job per `Agent` call. Run independent jobs in parallel in one message, but only when their file sets are disjoint; parallel jobs run only the narrow test for their own files, and you run the full suite after they finish.
>
> **Verify before you accept.** Treat a sub-agent's report as a claim, not evidence. For every delegated job, run the verification yourself: the test suite, the build, and the equivalence check for anything that was supposed to be verbatim, type-only or formatting-only. Read the diff. If a result fails or does something the brief did not ask for, send a follow-up with the exact finding rather than fixing it yourself, unless the fix is smaller than the explanation.
>
> **Escalate, don't retry.** If a tier-1 or tier-2 job fails verification twice, do it yourself and say so. Never retry the same brief a third time on the same model.
>
> **Report the split.** In your final report, list each delegated job with its model, what it did, how many attempts it took, and what you had to correct.

## Your review, after each ticket

1. Run the suites and every gate yourself and read the output.
2. Read the full diff of every non-formatting commit. Check specifically: {{THE 4–6 THINGS most likely to go silently wrong in this ticket — lock/transaction boundaries, key order, flag names, error mapping, deleted code that docs/systemd still reference.}}
3. Run the thermo-nuclear-code-quality-review skill yourself on the branch diff (`git diff <default branch>...HEAD` in the worktree). You are a different model family from the implementer, which is the point. Its presumptive blockers are findings for the next step; anything outside this ticket's scope goes under Follow-ups. Give the report path in your final report.
4. If something is wrong, send the implementer the exact finding; do not fix it yourself.
5. Review the delegation split. If your miss count (findings the implementer's report didn't mention) climbs sharply versus earlier tickets, say so: the next ticket should move tier-2 work back to the implementer first.
6. Last commit on the branch, after your review passes: run `python3 ~/.claude/skills/consolidate/drift_check.py rebaseline` in the worktree and commit `.codeshape/baseline.json` on its own ("code-shape: rebaseline after <ticket>"). The baseline update then merges with the refactor it reflects and the owner never has to remember it. Skip this only if the repo has no `.codeshape/` directory yet.
7. Do not merge. Report: branch name, commit list, test and gate output, findings your review caught that the implementer missed, the delegation split, and append "Follow-ups" to `.agent/handoffs/refactor-audit.md`. {{If production runs a different interpreter/runtime than this machine, end with copy-pasteable commands for the owner to verify the branch there in a throwaway worktree, at low priority.}}
