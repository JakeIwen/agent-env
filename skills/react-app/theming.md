# Theming a React app

Reference: `~/dev/example-web-app/src/styles/palette.css`,
`public/theme.js`, `src/components/layout/ThemeToggle.tsx`, `src/dev/`.

## palette.css

Every color in the app is a semantic token here, and only here (the
`color-literal` and `theme-selector` checks enforce it). Components use
`var(--token)` or `color-mix(in oklch, var(--a), var(--b) 30%)`.

```css
/* Retheme by editing the knobs or adding a data-palette profile.
   Mode-specific profile overrides use :root[data-palette='x'][data-theme='dark']. */
:root {
  --hue-neutral: 120;
  --hue-brand: 145;
  --hue-accent: 40;
  --chroma: 1;
  color-scheme: light;

  /* L is fixed per role, so contrast holds whatever the knobs say. */
  --paper: oklch(0.967 calc(0.008 * var(--chroma)) var(--hue-neutral));
  --ink: oklch(0.294 calc(0.012 * var(--chroma)) var(--hue-brand));
  --muted: oklch(0.539 calc(0.015 * var(--chroma)) var(--hue-neutral));
  --line: oklch(0.896 calc(0.014 * var(--chroma)) var(--hue-neutral));
  --accent: oklch(0.523 calc(0.121 * var(--chroma)) var(--hue-accent));

  /* Roles built from other tokens stay on the same ramps. */
  --border-soft: color-mix(in oklch, var(--line), var(--ink) 10%);
}

:root[data-theme='dark'] {
  color-scheme: dark;
  --paper: oklch(0.21 calc(0.012 * var(--chroma)) var(--hue-neutral));
  --ink: oklch(0.93 calc(0.01 * var(--chroma)) var(--hue-brand));
  /* ...every mode-sensitive role, nothing else */
}

/* A profile changes knobs only. */
:root[data-palette='sea'] {
  --hue-neutral: 220;
  --hue-brand: 230;
  --hue-accent: 30;
  --chroma: 0.9;
}
```

- Pick each role's lightness for the contrast the owner wants against white
  and black, then leave it alone; retheme through hue and chroma.
- Fixed colors (screenshot backdrops, pure white, a device shadow) are
  still tokens in this file, with a comment saying they don't follow the
  knobs.
- `[data-theme]` and `[data-palette]` selectors appear nowhere else. A
  component that needs a mode-specific value gets its own token.

## Mode and first paint

- A small script in `public/` (loaded by a blocking `<script>` in
  `index.html`, before the app) reads the saved choice or
  `prefers-color-scheme`, sets `document.documentElement.dataset.theme`,
  and sets the `theme-color` meta to a hex first-paint value. That hex
  pair is the only color outside the palette; keep it in step by hand.
- After render, the theme control copies the computed token into the meta
  (`getComputedStyle(root).backgroundColor`) and re-copies it on
  `data-theme`, `data-palette` or `style` changes (a MutationObserver), so
  profiles and dark mode stay right without a second color list.
- Storage access is wrapped in try/catch; the app renders without it.

## Optional dev-only palette panel

- `src/dev/PalettePanel.tsx` (+ `PalettePanel.css`) edits the knobs live
  and copies the result as CSS; `src/dev/mountPalettePanel.tsx` creates its
  own root in a host element and disposes it on hot reload.
- `main.tsx`: `if (import.meta.env.DEV) void import('./dev/mountPalettePanel')`
  (`process.env.NODE_ENV === 'development'` under CRA and esbuild
  `define`). The structure check's `contract` rule rejects a static
  import of `dev/`.
- After a production build, confirm it is absent:
  `grep -rl -e PalettePanel -e palette-panel <out>/assets` prints nothing.
