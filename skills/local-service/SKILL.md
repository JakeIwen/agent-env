---
name: local-service
description: Use for creating, installing, restarting, debugging, or publishing an always-on local app or service managed by launchd or systemd, especially on a fixed loopback port with a health endpoint and graceful stop. Do not use for foreground development servers, one-off commands, cron jobs, or deployments without a persistent local process.
---

# local-service

The operating layer for the owner's persistent local applications. The repo's own
`AGENTS.md` and service/deployment docs win over this skill. Inspect the live
service before changing it; a prepared config, copied plist/unit, or detached
manual process is not proof of boot registration.

Use `python-tool` for Python layout, stdlib-first choices, tests, and entry
points. Use `mac-pi-repo` for a repository that spans the Mac and Pi, including
`macbook/`, `pi/`, and `shared/` layout, deployment order, and SSH routes. This
skill owns service supervision, health, lifecycle, ports, and publication.

## Start with the live state

1. Read the repo's `AGENTS.md`, service docs, controller, and generated config.
2. Identify the host, supervisor, boot versus login scope, service account,
   fixed port, bind address, working/data directories, and current ownership.
3. Run read-only status before install, restart, repair, or publication. Check
   the supervisor, listener, health response, private ownership record, and
   logs; do not infer one from another.
4. Reuse the nearest reference implementation rather than copying a controller.
   Preserve a mature repo's stronger safety, drain, rollback, and hardening.
5. Run the repo's whole suite. Exercise real lifecycle behavior where the task
   authorizes an interruption; otherwise report that controlled restart was not
   reverified.

## Mac launchd contract

### Scope and plist

Default to a boot-time system LaunchDaemon:

- Label `com.example.<app>` and install at
  `/Library/LaunchDaemons/<label>.plist`, owned `root:wheel`, mode `644`.
- Run the worker as `UserName=<user>`, never root.
- Set `RunAtLoad=true`, `KeepAlive=true`, `ThrottleInterval=10`,
  `ExitTimeOut=20`, `ProcessType=Background`, and `Umask=077` (plist integer
  `63`).
- Set an explicit `WorkingDirectory`. Send stdout/stderr to private ignored
  state such as `.local/service/launchd.stdout.log` and
  `.local/service/launchd.stderr.log`.
- Give `EnvironmentVariables` a minimal `PATH` plus only what the app needs.
  Never put credentials in the plist.
- `ProgramArguments` starts with the absolute interpreter from the installed
  Node version or `.venv`, followed by the entry script/module and arguments.
  Boot must not use a login shell, initialize nvm, install dependencies, build,
  migrate, index, or download anything.

Use a per-user LaunchAgent under `~/Library/LaunchAgents` in the
`gui/<uid>` domain only when the process truly needs the login session, such as
GUI, keychain, or Chrome access. A login agent starts at login and stops at logout; it is not a
boot-time service. Uninstall before changing boot/login scope.

### Worker and ownership

- Bind `127.0.0.1` only, on one fixed port.
- Serve a health endpoint and an authenticated graceful-stop endpoint.
- After a successful bind, atomically write a private ownership record
  containing at least PID, unique instance ID, and random stop token. Use mode
  `600`; never print or return the token from health/status.
- Remove ownership only when the exiting instance still owns the record.
  Controllers match launchd PID, HTTP health PID/instance, and the record
  before acting; they never guess a PID.
- Reject a foreign listener on the port and an installed plist belonging to a
  different workspace or user.

### Project controller

Every project ships its own lifecycle controller exposed through:

```text
service:prepare | service:install | service:status | service:start
service:stop    | service:restart | service:verify | service:uninstall
```

Keep these meanings:

- `prepare`: write and lint/validate a reviewable plist without installing or
  loading it.
- `install`: preflight ownership and the port, install the plist, load/enable
  it, wait for health, and normally verify automatic recovery.
- `status`: read-only; exit nonzero unless the expected plist is installed,
  enabled, and loaded and its launchd PID agrees with health and ownership.
- `start`: re-enable and load a deliberately stopped installed job.
- `stop`: disable before unloading so KeepAlive and reboot cannot immediately
  undo the stop; leave code and application data intact.
- `restart`: gracefully stop the owned worker while KeepAlive stays enabled,
  then require a different healthy PID and instance. Do not unload/reinstall
  an already registered job for a routine reload.
- `verify`: deliberately exit the owned worker with KeepAlive enabled and prove
  launchd replaces it with a different healthy PID/instance. It does not prove
  a full reboot and briefly interrupts the app.
- `uninstall`: remove only this service's registration, preserving code, data,
  environments, and logs.

Only plist installation and `launchctl` operations use sudo. Never run npm,
Node, Python, or the worker as root. Agent shells usually cannot write
`/Library/LaunchDaemons`; do not retry or substitute a detached process. Give
the owner the project's exact normal-Terminal command, usually
`npm run service:install` (including arguments such as `-- --boot` when the
repo requires them), and continue to describe it as uninstalled until
`service:status` and `service:verify` prove otherwise.

After a build, use `service:restart` or the authenticated stop endpoint and let
KeepAlive relaunch. Never use `service:stop` or reinstall for a routine reload.
Inspect with `launchctl print system/<label>` (or `gui/<uid>/<label>` for a
LaunchAgent) and the launchd logs. Uninstall before moving a checkout; reinstall
at the new path. Reinstall when the configured interpreter path changes.

## Pi and Linux systemd variant

Use the repo runbook for target access and deployment.

Default a machine service to a system unit:

- Install a root-owned regular file at
  `/etc/systemd/system/<name>.service`, not a symlink into a service-account-
  writable checkout. Use `WantedBy=multi-user.target`.
- Set `Type=simple`, a non-root `User`/`Group`, explicit `WorkingDirectory`,
  absolute `ExecStart`, minimal `Environment`, and `UMask=0077`. Do not use a
  login shell or install/build at startup.
- Use `After=`/`Wants=network-online.target` only when startup really needs the
  network. Prefer `Restart=on-failure` for an ordinary server; use
  `Restart=always` when a clean exit must also recover, and document why.
  `RestartSec=5` and `TimeoutStopSec=20` are the local precedent.
- Add applicable hardening: `NoNewPrivileges`, `PrivateTmp`,
  `ProtectSystem=strict`, `ProtectHome`, empty capability sets, and explicit
  writable paths. Add resource/device/network restrictions from the service's
  threat model rather than copying them blindly.
- Validate with `systemd-analyze verify`; install, `daemon-reload`, and
  `enable --now` through the project controller. Status must check enabled,
  active, MainPID, listener/health where applicable, and the installed unit's
  ownership/content. Use `journalctl -u <unit>` for logs.

Use a user unit under `~/.config/systemd/user/` with
`WantedBy=default.target` only when its state and lifecycle are intentionally
user-scoped. Boot survival then requires linger; check it rather than assuming.
Control it with `systemctl --user`. For a new Pi service, prefer a project-owned wrapper with the same prepare/install/
status/start/stop/restart/verify/uninstall meanings: make persistent stop use
`disable --now`, keep routine restart enabled, and prove recovery plus health.
Do not retrofit a working specialized deployer merely for naming consistency.
Bind to the least exposed addresses the app needs: loopback for a tunnel
upstream, explicit LAN/Tailscale addresses for a private-network UI, and
`0.0.0.0` only when the repo's security model requires it.

## Verification and debugging

Prefer the project's controller because it knows ownership and rollback. For a
Mac service, correlate controller status, `launchctl print`, `lsof`, health, and
logs. For systemd, correlate `systemctl is-enabled`, `is-active`, `show -p
MainPID`, the listener/health, and `journalctl`. Never print ownership tokens,
Access assertions, environment files, or tunnel credentials.

A controlled `verify` proves supervisor recovery, not reboot behavior. Record
when it was skipped. A successful config linter or unit test proves neither
installation nor live health.

For browser verification, under Claude use the isolated `browser_clean` tools;
under Codex use the same browser_clean MCP server's corresponding tools. Never
launch a GUI browser from a shell. Test through `127.0.0.1` before publication,
then test the public hostname and authorization boundary when publication is in
scope.
