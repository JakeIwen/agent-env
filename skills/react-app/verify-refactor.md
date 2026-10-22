# Verifying that a refactor changed nothing

A pure reorganization (moving components, splitting stylesheets, renaming
classes consistently) must render the same DOM and computed styles. Verify
by output, not by reading.

## 1. Two builds in scratch folders

```sh
S=<scratchpad>            # never the repo's dist/ or build/
git -C <repo> worktree add --detach $S/base <base-commit>
ln -s <repo>/node_modules $S/base/node_modules
(cd $S/base && npx vite build --outDir $S/out-base --emptyOutDir)
(cd <repo> && npx vite build --outDir $S/out-next --emptyOutDir)
```

Use the bundler's equivalent from SKILL.md for other stacks. Remove the
worktree afterwards (`git -C <repo> worktree remove $S/base`).

## 2. Serve both on spare loopback ports

```sh
npx vite preview --outDir $S/out-base --host 127.0.0.1 --port 4180 --strictPort
npx vite preview --outDir $S/out-next --host 127.0.0.1 --port 4181 --strictPort
```

Run each in the background. Check the ports are free first
(`lsof -nP -iTCP:<port> -sTCP:LISTEN`) and never reuse a local service's
port. Other stacks: `style-diff/serve-static.mjs <dir> <port>`.

## 3. Write the run file

A JSON config per app (keep it in the repo's ignored `.agent/style-diff/`):

```json
{
  "base": "http://127.0.0.1:4180",
  "next": "http://127.0.0.1:4181",
  "routes": ["/", "/work/van-dashboard", "/missing-page"],
  "widths": [350, 700, 1000, 1600],
  "themes": ["light", "dark"],
  "theme": { "attribute": "data-theme" },
  "states": [
    { "name": "viewer-open", "route": "/work/example-project",
      "steps": [{ "click": ".screenshot-figure button", "wait": 150 }] }
  ]
}
```

Other keys (defaults in `style-diff/make-run.mjs`): `theme.classes` for
class-based themes, `ignore` selectors, `domNormalize` regexes, `tolerance`
(max sRGB channel difference counted as equal), `examples`, `height`.

```sh
node ~/.claude/skills/react-app/style-diff/make-run.mjs \
  <repo>/.agent/style-diff/config.json <repo>/.agent/style-diff/run.js
```

## 4. Run it in the clean browser

- Under Claude: browser_clean's `browser_run_code_unsafe` with
  `filename` set to the absolute path of `run.js`. The tool only reads
  files under its allowed roots (repo directories), which is why the run
  file lives inside the repo.
- Under Codex: the same `browser_clean` MCP server's run-code tool with
  that filename (or the file's contents as `code`).
- Never launch a browser from a shell.

The result is a summary: `identical` (true when nothing differs),
`states`, `missing`/`extra` elements, `byProp` counts with `examples`,
`colorShifts` (color changes beyond `tolerance`), and `dom.differing` with
the first differing snippet per example. Anything but `identical: true`
needs an explanation before the refactor lands.

## 5. Clean up

Stop both servers, remove the worktree and scratch builds, and keep the
config if the repo will need it again.
