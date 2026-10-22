# Verifying a reorganization

A layout change (a split, a move into a feature folder, a compatibility
path) must not change behavior. Three complementary checks, each using what
the repo already has; there is no shared oracle runner.

## 1. Expected behavior

Tests through public operations, CLI entry points and request handlers, not
private attributes. The pure halves get record-in, record-out tests;
adapters are exercised against a temporary real thing (a SQLite file, a
loopback service, a protocol fixture). The whole documented suite stays
green, not only the tests near the change.

## 2. Preservation

Run the repo's reviewed capture harness against the baseline tree (a
detached worktree at the commit before the change) and the candidate tree
with identical fixtures, and compare the contracts the change could affect:
stdout, stderr, exit codes, JSON and generated files, socket payloads,
storage contents and failure behavior.

- example-toolkit: `tests/*_oracle.py` block sockets and subprocesses and control
  time (`tests/broker_pure_oracle.py` captures generated helper and state
  output).
- Python tools: python-tool's output comparison (same inputs, same
  interpreter, both trees).
- Bytes where bytes are contractual; a narrow, named normalization (a
  timestamp field, a temp path) only when justified, and said so in the
  report.

Equality on captured cases is evidence, not proof. Say which cases were
captured and which launch modes and hosts were not exercised.

## 3. Execution and deployment

The supported launch commands still start: every Contracts-table path, unit
`ExecStart` and package script touched by the change (`check_layout.py`
reports a table row whose path no longer exists). Packaged files and install
paths still match the deployer's mapping (the Pi deploy allowlist, a
bundle's file list). A controller's `status` and `verify` run only when a
deployment is separately authorized; never start services or touch hardware
to verify a layout change.

## If a shared runner is built later

It must:

- list its commands explicitly, never discover them;
- record the provenance of both trees (commit, dirty state, interpreter);
- isolate state and clocks: temporary homes, data folders and sockets,
  fixed time;
- enforce timeouts and clean up processes and files it started;
- require each case's expected exit status and outputs, so two identical
  crashes never count as equivalence;
- compare storage contents and failure behavior as well as schema.
