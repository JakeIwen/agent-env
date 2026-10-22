---
name: react-app
description: Organize and check React or Preact web apps (DOM rendering, plain CSS). Use when creating or reorganizing an app in a repo whose package.json depends on react-dom or preact, or adding pages, components, styles or themes to one; when setting up its CSS, import or structure checks; and when verifying that a refactor did not change rendering. Not for React Native.
---

# react-app

The React layer over the global Code shape rules (organize by role then
feature, entry points only wire, colocate until shared, keyed maps over
repeated conditionals, styles as tokens, verify reorganizations by output).
Those rules are not repeated here. The repo's own AGENTS.md wins over this
skill. Applies to React and Preact DOM apps with plain CSS.

## Layout

- `main.tsx` bootstraps: fonts, then the global stylesheet, then dev-only
  tools behind the bundler's dev flag, then `<App />`.
- `App.tsx` holds only the layout shell and the routes. `routes.ts` holds
  path constants and path helpers; nothing else spells a path.
- `pages/`: one file per route (`HomePage.tsx`); a page's sections in
  `pages/<page>/` (`pages/home/Hero.tsx`).
- `components/<feature>/` for components shared across pages (`layout/`,
  `screenshots/`), never by kind. `content/` for data and copy. `styles/`
  for the global style layer. `dev/` for development-only tools.
- Hooks sit beside the components that use them (`useSwipe.ts` next to
  the viewer), not in a global `hooks/`.
- Named exports, one component per file, filename equal to the export
  (`Header.tsx` exports `Header`). Helpers, types and hooks may share it.
- Per-slug media or behavior goes through one map keyed by a typed slug
  union: an app’s `components/projects/projectMedia.tsx` maps
  `ProjectSlug` to card images and case-study figures.

## Styles

- Each component's stylesheet sits beside it as `Name.css`, imported for
  its side effect (`import './Name.css'`). Siblings that render the same
  classes share one descriptively named sheet in their folder
  (`case-study.css`).
- The global layer in `styles/` stays small: `palette.css`, base and
  shared primitives, `motion.css`, and `index.css` importing them in order.
- Plain CSS with custom properties. No SCSS for variables. CSS Modules
  only where a repo already uses them. No nesting (the checker rejects it).
- A parent restyles a child through a modifier class it passes
  (`hero-feature`) or a custom property (`--gallery-height`), never by
  selecting the child's own classes.
- Cascade order: Vite, webpack and esbuild emit CSS in module import order,
  depth first. So `main` imports the global stylesheet before `App`, and
  each module imports its child components before its own stylesheet, so
  the parent's rules come after the child's defaults. Lazy chunks bring
  their CSS later; watch for conflicts there. The coupling rule prevents
  most conflicts, and the computed-style diff is the final judge.

## Theming

See `theming.md` for the palette template. In short: every color is an
`oklch()` token in `palette.css` with its lightness fixed (so contrast
holds) and hue and chroma driven by `--hue-neutral`, `--hue-brand`,
`--hue-accent` and `--chroma`. Dark mode and named profiles override
tokens with `:root[data-theme]` and `[data-palette]` selectors that appear
nowhere else. The `theme-color` meta takes the computed token at runtime;
a pre-render script sets only the first-paint value. An optional dev-only
palette panel loads through a dev-only dynamic import, and the production
bundle is checked to be free of it (`grep -r palette-panel <out>/assets`).

## Checks

`node ~/.claude/skills/react-app/install-checks.mjs <app-dir>` copies the
checkers and their tests into `<app>/scripts/`, wires `check:css` and
`check:structure` into `build` and the tests into `npm test`, and prints
what the checks find. The repo owns its copy; a build never depends on
`~/.claude`. Fix or exempt every finding (moves as tidying commits) before
committing the wiring, so the suite stays green. Rules, settings (`css` and
`structure` blocks in `<app>/.codeshape/config.json`), how class references
are found, and read-only audits (`--root <app> --config <file>`): see
`checks.md`.

## Bundler specifics

Serve builds only on a spare loopback port, and build into a scratch
folder, never the `dist/` or `build/` a local service serves.

- Vite: dev-only code behind `if (import.meta.env.DEV) void
  import('./dev/…')`. Build with `npx vite build --outDir <dir>
  --emptyOutDir`; serve with `npx vite preview --outDir <dir> --host
  127.0.0.1 --port <spare> --strictPort`.
- React Router framework mode (example-ssr-app): `import.meta.env.DEV`
  applies. `react-router build` always writes `build/client` and
  `build/server` in the project, so build in a scratch copy (a detached
  worktree with `node_modules` symlinked) and serve it from there with
  the repo's server and its port flag (`node --import tsx server/index.ts
  --port <spare>`; its data comes from the repo's fixture script, as in
  `scripts/preview.sh`). `@react-router/serve` is not installed there.
  Set `structure.ignoredExports` to
  `["Layout","ErrorBoundary","HydrateFallback"]`.
- Create React App (example-cra-app): dev-only code behind
  `process.env.NODE_ENV === 'development'`. Build with
  `BUILD_PATH=<dir> npx react-scripts build` (needs `npm ci` first; ask
  before downloading on a metered uplink); serve with
  `node ~/.claude/skills/react-app/style-diff/serve-static.mjs <dir>
  <spare>` (loopback, index.html fallback for client routes).
- esbuild (example-toolkit dashboard): the repo's `tools/build.mjs` with
  `--out-dir <dir>`; its `define` sets `process.env.NODE_ENV`, so gate
  dev-only code on that. Serve `<dir>` with `serve-static.mjs` as above.

## Verifying a refactor changed nothing

See `verify-refactor.md`: build the baseline from a detached worktree and
the change into separate scratch folders, serve both, then run the
computed-style and DOM diff in `style-diff/` across routes, widths, both
themes and interactive states. Under Claude, run it with browser_clean's
`browser_run_code_unsafe` and an absolute `filename` inside the repo; under
Codex, the same `browser_clean` MCP server's run-code tool. Never launch a
browser from a shell.

## Boundaries

- The repo's AGENTS.md wins. Moves land as tidying commits, separate from
  behavior changes, verified by the diff above.
- Exemptions use `codeshape:` comments (`allow-marker` on the reported
  line, `allow-size <reason>` in a stylesheet), and every one is reported.
- Never restructure live-service code to satisfy a check; report it.
