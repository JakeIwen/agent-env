// Writes a runnable copy of style-diff.js with an app's settings inlined, so
// a repo supplies routes and origins without editing the harness.
// usage: node make-run.mjs <config.json> <out.js>
// Put <out.js> inside the repo (e.g. <repo>/.agent/style-diff/run.js): the
// browser tool only reads files under its allowed roots.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const DEFAULTS = {
  widths: [360, 768, 1280],
  themes: ['light', 'dark'],
  // How a theme is applied after load: `attribute` on <html> set to the
  // theme name, and/or `classes` per theme ({ "dark": "dark", "light": "" }).
  // light/dark also emulate prefers-color-scheme.
  theme: { attribute: 'data-theme' },
  // Interactive states: { name, route, steps: [{ click | hover | focus |
  // press | scroll, wait? }] }, captured at every width and theme.
  states: [],
  // Selectors whose subtrees are skipped (dev overlays, live clocks).
  ignore: [],
  // Regex sources removed from both serialized bodies before the DOM diff.
  domNormalize: [],
  tolerance: 0,
  examples: 40,
  height: 900,
}
const MARKER = '/* STYLE_DIFF_CONFIG */ null'

const [configPath, outPath] = process.argv.slice(2)
if (!configPath || !outPath) {
  console.error('usage: node make-run.mjs <config.json> <out.js>')
  process.exit(2)
}
const config = { ...DEFAULTS, ...JSON.parse(readFileSync(configPath, 'utf8')) }
const unknown = Object.keys(config).filter((key) => !(key in DEFAULTS) && !['base', 'next', 'routes'].includes(key))
const missing = ['base', 'next', 'routes'].filter((key) => !config[key])
if (unknown.length || missing.length) {
  console.error(`Config problems: ${[...missing.map((k) => `missing ${k}`), ...unknown.map((k) => `unknown ${k}`)].join(', ')}`)
  process.exit(2)
}
const harness = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'style-diff.js'), 'utf8')
const body = harness.slice(harness.search(/^async \(page\) =>/m))
const out = resolve(outPath)
mkdirSync(dirname(out), { recursive: true })
writeFileSync(out, body.replace(MARKER, JSON.stringify(config)))
console.log(`Wrote ${out}`)
