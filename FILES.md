# File inventory

Every file in the public snapshot is listed below. No live configuration is linked.

| File | Why it is included |
|---|---|
| [`.gitignore`](.gitignore) | Keeps handoff state, bytecode and desktop metadata out of the snapshot. |
| [`AGENTS.md`](AGENTS.md) | Defines this snapshot’s ownership map, test command and publication boundary. |
| [`FILES.md`](FILES.md) | Lists every published file and its inclusion reason. |
| [`README.md`](README.md) | Explains each piece, the failure it addresses and the limits of the snapshot. |
| [`hooks/claude_ntfy_notify.py`](hooks/claude_ntfy_notify.py) | Shows detached notification delivery with scrubbed SSH destinations. |
| [`hooks/plus_commands.py`](hooks/plus_commands.py) | Reads command help from the same definitions the agent receives. |
| [`hooks/settings.example.json`](hooks/settings.example.json) | Shows only the selected hook registrations with placeholder paths. |
| [`hooks/tests/test_plus_commands.py`](hooks/tests/test_plus_commands.py) | Verifies help parsing, bare-command handling and pass-through behavior. |
| [`instructions/AGENTS.md`](instructions/AGENTS.md) | Preserves the scrubbed Codex working conventions. |
| [`instructions/CLAUDE.md`](instructions/CLAUDE.md) | Preserves the scrubbed Claude working conventions. |
| [`instructions/synchronization.md`](instructions/synchronization.md) | Explains how four globals stay aligned without publishing maintenance notes. |
| [`run_tests.py`](run_tests.py) | Runs every bundled suite and parses Python/JSON without a build step. |
| [`skills/backend-layout/SKILL.md`](skills/backend-layout/SKILL.md) | Sets backend module boundaries, deployment contracts and layout gates. |
| [`skills/backend-layout/checks/backend_layout/__init__.py`](skills/backend-layout/checks/backend_layout/__init__.py) | Marks the independently installable checker package. |
| [`skills/backend-layout/checks/backend_layout/advisory_rules.py`](skills/backend-layout/checks/backend_layout/advisory_rules.py) | Reports review signals for coupling, stale shims and misplaced effects. |
| [`skills/backend-layout/checks/backend_layout/baseline.py`](skills/backend-layout/checks/backend_layout/baseline.py) | Loads layout baselines and classifies findings against them. |
| [`skills/backend-layout/checks/backend_layout/cli.py`](skills/backend-layout/checks/backend_layout/cli.py) | Runs layout rules and reports the result through one CLI. |
| [`skills/backend-layout/checks/backend_layout/cochange.py`](skills/backend-layout/checks/backend_layout/cochange.py) | Measures source files that repeatedly change together. Deliberate copy for independent installation; guarded by a mirror test. |
| [`skills/backend-layout/checks/backend_layout/config.py`](skills/backend-layout/checks/backend_layout/config.py) | Validates the layout checker configuration and default rules. |
| [`skills/backend-layout/checks/backend_layout/contracts_table.py`](skills/backend-layout/checks/backend_layout/contracts_table.py) | Reads externally called paths from a repository’s contracts table. |
| [`skills/backend-layout/checks/backend_layout/edges.py`](skills/backend-layout/checks/backend_layout/edges.py) | Resolves local import edges for structural checks. |
| [`skills/backend-layout/checks/backend_layout/files.py`](skills/backend-layout/checks/backend_layout/files.py) | Discovers relevant source files while honoring exclusions. |
| [`skills/backend-layout/checks/backend_layout/findings.py`](skills/backend-layout/checks/backend_layout/findings.py) | Defines the canonical finding record and rule vocabulary. |
| [`skills/backend-layout/checks/backend_layout/git_adapter.py`](skills/backend-layout/checks/backend_layout/git_adapter.py) | Keeps Git discovery and history reads behind one boundary. |
| [`skills/backend-layout/checks/backend_layout/import_graph.py`](skills/backend-layout/checks/backend_layout/import_graph.py) | Measures Python/JavaScript import cycles and shared-module coupling. Deliberate copy for independent installation; guarded by a mirror test. |
| [`skills/backend-layout/checks/backend_layout/json_splice.py`](skills/backend-layout/checks/backend_layout/json_splice.py) | Updates one JSON key while preserving unrelated configuration bytes. |
| [`skills/backend-layout/checks/backend_layout/references.py`](skills/backend-layout/checks/backend_layout/references.py) | Resolves external command and module references into repository paths. |
| [`skills/backend-layout/checks/backend_layout/report.py`](skills/backend-layout/checks/backend_layout/report.py) | Renders layout findings as text or JSON. |
| [`skills/backend-layout/checks/backend_layout/structure_rules.py`](skills/backend-layout/checks/backend_layout/structure_rules.py) | Checks contracts, entry points, feature groups and import cycles. |
| [`skills/backend-layout/checks/backend_layout/targets.py`](skills/backend-layout/checks/backend_layout/targets.py) | Checks declared paths against service units, plists and script manifests. |
| [`skills/backend-layout/checks/check_layout.py`](skills/backend-layout/checks/check_layout.py) | Provides the standalone backend checker entry point. |
| [`skills/backend-layout/checks.md`](skills/backend-layout/checks.md) | Documents backend-layout checker rules, settings and exceptions. |
| [`skills/backend-layout/install-checks.py`](skills/backend-layout/install-checks.py) | Copies the backend checks and wires the destination’s existing suite. |
| [`skills/backend-layout/install_plan.py`](skills/backend-layout/install_plan.py) | Plans checker installation and refuses conflicting destination edits. |
| [`skills/backend-layout/stacks.md`](skills/backend-layout/stacks.md) | Explains language-specific applications of the backend layout rules. |
| [`skills/backend-layout/templates/test_layout_tree.py`](skills/backend-layout/templates/test_layout_tree.py) | Supplies the destination-repository layout gate template. |
| [`skills/backend-layout/tests/layout_fixture.py`](skills/backend-layout/tests/layout_fixture.py) | Builds temporary repository fixtures for backend checks. |
| [`skills/backend-layout/tests/test_import_graph_copy.py`](skills/backend-layout/tests/test_import_graph_copy.py) | Ensures the independently shipped graph readers match consolidate. |
| [`skills/backend-layout/tests/test_install_checks.py`](skills/backend-layout/tests/test_install_checks.py) | Verifies installation planning, idempotence and conflict refusal. |
| [`skills/backend-layout/tests/test_layout_advisory.py`](skills/backend-layout/tests/test_layout_advisory.py) | Verifies advisory layout findings on fixture trees. |
| [`skills/backend-layout/tests/test_layout_baseline.py`](skills/backend-layout/tests/test_layout_baseline.py) | Verifies baseline comparisons, exemptions and rebaselining. |
| [`skills/backend-layout/tests/test_layout_rules.py`](skills/backend-layout/tests/test_layout_rules.py) | Verifies structural findings on fixture repositories. |
| [`skills/backend-layout/tests/test_layout_targets.py`](skills/backend-layout/tests/test_layout_targets.py) | Verifies service and deployment references against declared paths. |
| [`skills/backend-layout/verify.md`](skills/backend-layout/verify.md) | Defines output comparison before and after backend reorganization. |
| [`skills/codex-artifact/SKILL.md`](skills/codex-artifact/SKILL.md) | Defines local HTML reports and retention for long replies. |
| [`skills/codex-artifact/scripts/agent_art.py`](skills/codex-artifact/scripts/agent_art.py) | Writes self-contained local reports, their index and retention state. |
| [`skills/consolidate/SKILL.md`](skills/consolidate/SKILL.md) | Defines measurement, audit, ticket and rebaseline workflows. |
| [`skills/consolidate/cochange.py`](skills/consolidate/cochange.py) | Measures source files that repeatedly change together. |
| [`skills/consolidate/css_metrics.py`](skills/consolidate/css_metrics.py) | Measures repeated selectors and color literals outside palette files. |
| [`skills/consolidate/drift_check.py`](skills/consolidate/drift_check.py) | Measures code shape and compares it with tracked baselines. |
| [`skills/consolidate/import_graph.py`](skills/consolidate/import_graph.py) | Measures Python/JavaScript import cycles and shared-module coupling. |
| [`skills/consolidate/org_metrics.py`](skills/consolidate/org_metrics.py) | Combines the optional organization metrics for explicit checks. |
| [`skills/consolidate/stop_hook.py`](skills/consolidate/stop_hook.py) | Scopes automatic notices to successful edits in the current turn. |
| [`skills/consolidate/tests/test_drift_check.py`](skills/consolidate/tests/test_drift_check.py) | Verifies code-shape measurement and ratchets on temporary repositories. |
| [`skills/consolidate/tests/test_session_attribution.py`](skills/consolidate/tests/test_session_attribution.py) | Verifies writer-only notices and repeated-Stop suppression. |
| [`skills/consolidate/ticket-template.md`](skills/consolidate/ticket-template.md) | Preserves refactor boundaries and independent verification in delegated briefs. |
| [`skills/consolidate/turn_activity.py`](skills/consolidate/turn_activity.py) | Recognizes successful structured edits with exact turn identifiers. |
| [`skills/local-service/SKILL.md`](skills/local-service/SKILL.md) | Defines supervised service ownership, lifecycle and recovery checks. |
| [`skills/mac-pi-repo/SKILL.md`](skills/mac-pi-repo/SKILL.md) | Defines source ownership and verification across two operating systems. |
| [`skills/python-tool/SKILL.md`](skills/python-tool/SKILL.md) | Defines interpreter, package, import and whole-suite contracts. |
| [`skills/react-app/SKILL.md`](skills/react-app/SKILL.md) | Defines component, CSS, theme and rendering-verification rules. |
| [`skills/react-app/checks/check-cli.mjs`](skills/react-app/checks/check-cli.mjs) | Runs the React CSS and structure checkers through a shared CLI. |
| [`skills/react-app/checks/check-css.mjs`](skills/react-app/checks/check-css.mjs) | Checks tokens, selector ownership, cascade coupling and stylesheet structure. |
| [`skills/react-app/checks/check-css.test.mjs`](skills/react-app/checks/check-css.test.mjs) | Verifies CSS rules and explicit exceptions on temporary app trees. |
| [`skills/react-app/checks/check-structure.mjs`](skills/react-app/checks/check-structure.mjs) | Checks React module boundaries, component placement and imports. |
| [`skills/react-app/checks/check-structure.test.mjs`](skills/react-app/checks/check-structure.test.mjs) | Verifies React structure rules against fixture apps. |
| [`skills/react-app/checks/component-exports.mjs`](skills/react-app/checks/component-exports.mjs) | Recognizes exported components for ownership and placement checks. |
| [`skills/react-app/checks/css-ownership.mjs`](skills/react-app/checks/css-ownership.mjs) | Connects stylesheet classes to their importing and rendering components. |
| [`skills/react-app/checks/script-scanner.mjs`](skills/react-app/checks/script-scanner.mjs) | Scans script imports and references without executing source files. |
| [`skills/react-app/checks/source-files.mjs`](skills/react-app/checks/source-files.mjs) | Discovers React source files consistently across checks. |
| [`skills/react-app/checks.md`](skills/react-app/checks.md) | Documents react-app checker rules, settings and exceptions. |
| [`skills/react-app/install-checks.mjs`](skills/react-app/install-checks.mjs) | Copies UI checks into an app and wires its build and test commands. |
| [`skills/react-app/style-diff/make-run.mjs`](skills/react-app/style-diff/make-run.mjs) | Builds a browser comparison harness from explicit route/state scenarios. |
| [`skills/react-app/style-diff/serve-static.mjs`](skills/react-app/style-diff/serve-static.mjs) | Serves scratch builds on loopback for rendering comparisons. |
| [`skills/react-app/style-diff/style-diff.js`](skills/react-app/style-diff/style-diff.js) | Compares DOM and computed styles across browser scenarios. |
| [`skills/react-app/templates/react-app-tree.test.mjs`](skills/react-app/templates/react-app-tree.test.mjs) | Supplies the destination-app structure test template. |
| [`skills/react-app/theming.md`](skills/react-app/theming.md) | Defines the palette and theme token convention. |
| [`skills/react-app/verify-refactor.md`](skills/react-app/verify-refactor.md) | Defines rendering comparison across routes, widths, themes and states. |
| [`skills/thermo-nuclear-code-quality-review/LICENSE`](skills/thermo-nuclear-code-quality-review/LICENSE) | Retains the upstream review skill’s MIT notice and attribution. |
| [`skills/thermo-nuclear-code-quality-review/SKILL.md`](skills/thermo-nuclear-code-quality-review/SKILL.md) | Preserves the strict review rubric, provenance and local scope rules. |
| [`tools/tests/test_uncommitted_owners.py`](tools/tests/test_uncommitted_owners.py) | Verifies attribution, renames, child-session rollup and open-state reporting. |
| [`tools/uncommitted_owners.py`](tools/uncommitted_owners.py) | Maps dirty files to candidate owning sessions and parent sessions. |
