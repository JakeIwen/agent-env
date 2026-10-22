---
name: mac-pi-repo
description: Organize, deploy and verify repositories with code for both the owner's MacBook  and Raspberry Pi . Use when adding cross-host code, deploying or checking either side, or moving files between the machines. Covers layout, routing, runtimes and deploy order. Not for Mac-only or Pi-only repos.
---

# mac-pi-repo

The cross-host layer over the global Code shape, network-safety and Terminal
handoff rules. The repo's own AGENTS.md wins over this skill; current deployment
code and live inspection establish facts, not an old directory name or note.
This skill does not authorize a deployment, commit, service restart or transfer.

Load `local-service` for the launchd/systemd service and controller contract;
load `python-tool` for Python packaging, entry points, dependencies and tests.
Under Claude, invoke those skills with the Skill tool; under Codex, load their
SKILL.md through its skill mechanism. Do not duplicate their rules here.

## Start with ownership

1. Read the repo's AGENTS.md, relevant handoff and deploy runbook. Identify the
   authoritative checkout, deployed paths and owner of each service or payload.
2. Inspect Git state on each checkout involved. A Pi checkout may hold active
   work; a deployed directory may not be a checkout at all. Preserve both.
3. Compare the files you intend to replace before changing anything. A mismatch
   is an investigation, not permission to overwrite the Pi with the Mac copy.
4. Choose the documented deployer and its complete source cohort. Include its
   shared modules, assets and units, not just the file named in the request.
   Record how to verify and roll back before starting a live change.

## Layout

For a new mixed-host toolkit, prefer:

```text
macbook/                 Mac adapters, installers, launchd templates
pi/                      Pi adapters, installers, systemd templates
shared/<feature>/        one source for code used on both hosts
```

- Put code by where it runs, not by the machine on which it was edited. A Mac
  launcher and Pi receiver should not each grow their own protocol definition.
- Keep shared code feature-named and platform-neutral; put OS calls in the host
  adapters. Tests belong beside their feature or in the repo's existing test
  layout, with explicit platform requirements.
- For a cohesive application, one canonical language package at the root is
  preferable to an extra `shared/` import layer. `example-compute/example_compute/` and
  `llm-switchboard/llm_switchboard/` already do this. Reuse the package; do not
  copy it into both host directories or move it just to fit the tree above.
- `scripts/shared/python` and `shared/sh` are existing compatibility layouts,
  not a reason to create more language-based grab bags. Extend their documented
  owners when appropriate; use feature folders for new independent concerns.
- Preserve installed path contracts. A deployed directory is not automatically
  the source checkout; identify its owner before editing it.

## Deployment sequence

The default for ordinary cross-host updates is **test, deploy Pi, verify Pi,
update/verify Mac, then commit and push the deployed cohort** when those Git
operations are authorized. Pi-first catches the slower/older target before
promoting the Mac side and keeps the commit aligned with installed work.
A coupled deployer owns its internal sequence; a documented reviewed/merged
first-cutover workflow wins over this default. Do not split a transaction or
skip an owner-run cutover merely to force Pi-first.

1. Run the whole repo suite per its AGENTS.md, including build/static checks.
   Review the selected deployer's dry-run/plan if it has one. A dry-run may be
   local-only; inspect its implementation before assuming it checks the Pi.
2. Preflight the LAN route, destination ownership, deployed hashes, runtime
   versions and service state. Resolve unexplained drift before replacement.
   Use the global backup and authorization rules for configuration changes.
3. Run the narrow owning deployer. Prefer allowlisted, hashed, staged releases
   with atomic promotion and retained rollback over broad directory mirroring:
   this preserves private state and prevents partial shared-module updates.
4. Verify installed bytes and the running instance before advancing the other
   host. Installed files alone do not prove that a long-lived process reloaded.
5. Finish the Mac side through its controller/installer and check compatibility
   across the boundary. For compute, require the new compatible heartbeat.
6. Stage only the reviewed deployed cohort when committing; include its tests
   and docs, not unrelated sessions' changes. Follow global Git and suite rules.
   Report an incomplete/failed deployment before committing it as a success.

## Verify both sides

Use launchd on the Mac and systemd on the Pi. Load `local-service` for the
contract itself. Select the existing scope: switchboard is a Pi **user** unit
with linger for boot startup; many other Pi apps use system units. Mac GUI/login
agents are not interchangeable with boot daemons. Do not migrate scopes during
an unrelated deployment.

For every deployed cohort, collect:

- **Bytes:** compare exact nonsecret files with `cmp`, or local
  `shasum -a 256` against Pi `sha256sum`. Compare a generated payload against its
  build manifest, not its original TypeScript. Preserve installer-managed
  immutable trees; even validation imports must not add bytecode to them.
- **Process:** the repo controller's status/verify, or read-only
  `systemctl status <unit> --no-pager` / `systemctl --user status <unit>` as
  appropriate; also check PID, loaded unit/drop-ins and restart state. Review
  bounded relevant journal output without exposing secrets.
- **Behavior:** the documented health endpoint and one safe affected public
  entry point, plus protocol/heartbeat compatibility for two-host features.
  Probe Pi loopback endpoints over SSH rather than exposing a new listener.
- **Rollback:** report whether the prior release remains recoverable and
  whether activation/restart is complete. Do not equate a successful copy,
  green unit or local mock with end-to-end health.

### Test placement

Run portable logic and protocol tests locally first. Run target-specific service,
shell and filesystem checks on the target when authorized. Verify with the
interpreter that actually runs the service; a newer local Python pass does not
prove compatibility with the target's Python. Never copy a virtual environment
or native dependency tree between operating systems.

Use bounded SSH checks and the configured host alias. Keep large transfers on
the intended local route; do not silently fall back to a metered route. Record
unverified target steps if the host is unavailable.
