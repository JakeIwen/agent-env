# react-app checks

Two dependency-free Node scripts (Node 22+), installed into an app and
owned by it from then on:

| File | Role |
|---|---|
| `checks/check-css.mjs` | CSS rules and CLI (`check:css`) |
| `checks/css-ownership.mjs` | colocate, ownership, coupling, orphan-stylesheet |
| `checks/check-structure.mjs` | structure rules and CLI (`check:structure`) |
| `checks/component-exports.mjs` | which components a `.tsx`/`.jsx` file exports |
| `checks/script-scanner.mjs` | string literals, markers and imports in scripts |
| `checks/source-files.mjs` | walking source roots, skipping tests |
| `checks/check-cli.mjs` | `.codeshape/config.json` blocks and the shared CLI |
| `checks/*.test.mjs` | fixture tests for the rules (`node --test checks/*.test.mjs`) |
| `templates/react-app-tree.test.mjs` | asserts the app's own tree passes both checks |

## Installing

```sh
node ~/.claude/skills/react-app/install-checks.mjs <app-dir> [--scripts-dir scripts] [--force]
```

`<app-dir>` holds the app's `package.json` (which must depend on
`react-dom` or `preact`). The installer refuses to overwrite a differing
file without `--force`; compare first. It sets `check:css` and
`check:structure`, prefixes `build` with both, and adds `test:react-app`
to `test` unless `test` already runs `node --test <scripts-dir>/*.test.mjs`.
Under vitest, add `<scripts-dir>/**` to vitest's `test.exclude`, or vitest
collects the node:test files. When the skill's checkers improve, re-run
with `--force` and review the diff like any other change.

## Settings

`<app>/.codeshape/config.json`, paths relative to the app directory.
Unknown keys fail, so typos surface. consolidate's `drift_check.py` reads
only its own keys (`file_lines`, `func_lines`, `exclude`, ...) from the
same file; `css` and `structure` coexist with them. `file_lines` also sets
the CSS `size` limit (default 800).

```json
{
  "css": {
    "sourceRoots": ["src"],
    "palette": "src/styles/palette.css",
    "globalStyles": "src/styles/",
    "html": ["index.html"],
    "jsxExtensions": [".tsx", ".jsx"],
    "scriptExtensions": [".ts", ".tsx", ".js", ".jsx", ".mjs"],
    "themeAttributes": ["data-theme", "data-palette"],
    "exclude": []
  },
  "structure": {
    "sourceRoot": "src",
    "scriptExtensions": [".ts", ".tsx", ".js", ".jsx", ".mjs"],
    "componentExtensions": [".tsx", ".jsx"],
    "contracts": [
      { "from": "content", "to": ["components", "pages"] },
      { "from": "components", "to": ["pages"] },
      { "from": "*", "to": ["dev"], "allowDynamic": true }
    ],
    "ignoredExports": [],
    "aliases": {},
    "exclude": []
  }
}
```

These are the defaults (example-web-app's layout); list only what differs.
Test files (`*.test.*`, `*.spec.*`, `__tests__/`) are never sources.

To audit an app without touching it, write the config elsewhere and pass
it: `node <skill>/checks/check-css.mjs --root <app> --config <file> --json`
(same for `check-structure.mjs`).

## CSS rules

- `size`: a stylesheet over `file_lines`; exempt with
  `/* codeshape: allow-size <reason> */`.
- `color-literal`: hex, named, or color-function colors outside the
  palette, in CSS declarations and in script strings.
- `theme-selector`: `[data-theme]`/`[data-palette]` outside the palette.
- `nesting`: a style rule inside a style rule.
- `duplicate-selector`: the same normalized selector in the same
  `@media`/`@supports`/`@container`/`@layer`/`@scope` context, anywhere
  in the app.
- `unused-class`: a class no script or HTML file mentions as a word and no
  Tailwind `@apply` uses. Classes built at runtime (`status-${kind}`) need
  a marker or a literal list in a data file.
- `colocate`: a global-layer class used by one module; move it beside it.
- `ownership`: a module renders a class defined only in component sheets
  it doesn't import.
- `coupling`: a component sheet styles a class that none of its importers
  render (and that isn't global). A parent restyles a child through a
  modifier class it passes or a custom property instead.
- `orphan-stylesheet`: a sheet no script imports, directly or through
  `@import`.

## How class references are found

String literals in `.tsx` and `.jsx` files (`jsxExtensions`), including
literals nested in template expressions (`` `card ${on ? 'is-on' : ''}` ``),
split on whitespace. Object keys are excluded. The attribute doesn't
matter, so Preact's `class` counts like `className`. Classes named only in
`.ts`/`.js` data files count as data-driven: they satisfy `unused-class`
but own no stylesheet. HTML files in `html` contribute `class="..."`
attributes. Stylesheets are imported with `import './X.css'`; CSS Modules
imported with `from` count as imported, and their classes (used as
`styles.x`) are outside the ownership rules.

## Structure rules

- `contract`: forbidden folder imports, folders relative to the source
  root. Defaults: `content/` imports no components or pages, `components/`
  never imports `pages/`, nothing outside `dev/` imports it except through
  `import()`. Type-only imports count.
- `cycle`: a cycle of static value imports. Type-only and dynamic imports
  don't count. Reported once per cycle.
- `colocate-component`: a component imported by exactly one module lives
  in that module's folder or beneath it (so `pages/home/Hero.tsx` used by
  `pages/HomePage.tsx` passes, and `components/x/Y.tsx` used only by one
  page doesn't). Modules loaded through `import()` anywhere are code-split
  boundaries (lazy routes, a view or dialog registry) and are skipped.
- `one-component`: a `.tsx`/`.jsx` file exports more than one component
  (PascalCase functions, arrow functions, `memo`/`forwardRef`/`lazy`
  wrappers, class components; types, hooks and camelCase values are
  fine). `ignoredExports` lists framework route-module exports.

Imports resolve relative specifiers (`.js` specifiers find `.ts` files)
and `aliases` prefixes; package imports are ignored.

## Exemptions

`codeshape: allow-marker` in a comment on the reported line (an import, an
export, a selector) exempts that line. Every exemption is reported to
the owner.
