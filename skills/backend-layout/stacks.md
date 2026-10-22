# backend-layout stacks

Per-stack details for the shared rules in `SKILL.md`.

## Python

`python-tool` owns interpreters, packaging, imports, records and suites;
this section only places modules.

- A checkout-run tool is one package with a small `__main__.py`, a
  `cli.py` that parses argv into a config record, and feature-named
  modules or feature subpackages (`history/`, `warning_engine/` in
  `~/dev/example-device-app`).
- Units and wrappers run modules by name (`python3 -m
  projects.device_app.broker`), so a module name in a unit is a contract:
  list it in the Contracts table, and keep a compatibility module when it
  moves.
- Records crossing a process boundary are dataclasses or TypedDicts in the
  feature's model module; vocabularies shared with a dashboard live in a
  sidecar `.json` the Python side validates at load (device_app's
  `lighting.json`, `compass.json`, `availability.json`).
- Reference: `~/dev/example-guides/local_service` (a role per module, 40 to
  170 lines each); `~/dev/example-python-app/explorer` (server, extract,
  ingest, ocr, search, schema).

## Node

- `server/` holds the process: `http.ts` or `server.mjs` wires routes to
  handler modules; `routes/` has one file per resource; features in
  `<feature>/`; records crossing the client boundary in `shared/`.
- Framework suffixes such as `.server.ts` are role markers and stay.
- `scripts/` is for operator commands: the service controller, deploy,
  data maintenance. A server living in `scripts/`
  (`~/dev/example-inventory/scripts/inventory-server.mjs`) moves out
  only as its own migration, with its launch path kept.
- Hyphen-prefixed siblings (`export-records.ts`, `export-*.ts` in
  `~/dev/example-web-app/app/server`) group the same way as
  Python prefixes: `export/records.ts`.
- Reference: `~/dev/example-ssr-app/server` (`http.ts` 230 lines wires
  routes; `agent/` is a feature folder; `app/db/*.server.ts` holds storage).

## Script folders

- A folder of scripts is a set of deployment contracts, not automatically
  one package. Tell standalone utilities, sourced libraries and files
  installed together apart before anything moves.
- Shared shell functions live in `lib/<concern>.sh`, sourced relative to
  the script's own directory (`. "$(dirname "$0")/lib/net.sh"`;
  `~/dev/example-edge/scripts/lib/`). No absolute `. /home/<user>/scripts/x.sh`
  sources; no copying a function between scripts. Router and antenna
  scripts run BusyBox ash with their own constraints and keep their own
  libraries.
- A shell script over 200 lines is a review trigger with the same standing
  as 800 lines elsewhere: consider splitting it or moving the hard part to
  Python under `python-tool`. Nothing converts automatically, and jq, dates
  or tables are not triggers; a jq pipeline is often the simplest correct
  implementation. Shell stays for straightforward process orchestration.
- A feature with three or more cohesive files gets its folder, as
  `pi/scripts/backup/` and `pi/scripts/network_recorder/` already have.
- The deployer defines an explicit, tested source-to-install mapping; the
  Pi runbook's allowlisted releases, current/previous pointers and flat
  rollback tree are that mapping (`~/dev/scripts/pi/docs/deployment.md`).
  A new folder means checking the allowlist, packaged resources, wrappers
  and rollback, not only imports. Fix the source tree, never the installed
  copy.

## Go

For new self-contained services and CLIs; existing Python is not converted.
Go's standard layout is the entry/library split by convention.

- `cmd/<name>/main.go` is the only `package main`: flags and env, then one
  call into the application. Features in `internal/<feature>/`.
- Records are structs; vocabularies are typed constants. Interfaces appear
  where a second implementation or a test double exists.
- Suite: `gofmt -l .` (must print nothing), `go vet ./...`, `go test ./...`,
  and `staticcheck ./...` where installed, named in the repo AGENTS.md like
  any other suite command.
- Build on the Mac; cross-compile with `GOOS=linux GOARCH=arm64` for the Pi
  and ship the binary by `mac-pi-repo`'s built-payload pattern (the
  `codexclean` precedent). No Go toolchain on the Pi.
- The boundary with the Python world is a CLI or HTTP, with shared
  vocabulary in a sidecar `.json`. A Go service that needs something a
  Python shared owner provides (tool settings, atomic JSON, automation
  records) reports that instead of quietly reimplementing it.
- A good first candidate is a new or small Pi or Mac service with an HTTP
  or CLI boundary, no CAN, no numpy and no dependency on the Python
  settings library.

## Shared vocabulary across languages

- One canonical contract in the representation its consumers need: a shared
  module between two Python processes, an existing schema, or a data file
  across languages. Existing sidecar files are the owners; reuse them.
- Where a data file is right: validate at the boundary, include the file in
  both build and deploy paths, derive language representations where
  practical, and define unknown-value behavior, because rolling deployments
  mix versions. An enum-equality test catches drift; it doesn't prove
  payload validity or packaging.
