// Installs the react-app checks into an app (the folder holding its
// package.json): copies checks/* into <app>/scripts/, adds check:css and
// check:structure, runs both before `build`, adds the tests to `npm test`,
// then runs the checks once and prints what they find. The app owns its copy.
// usage: node install-checks.mjs <app-dir> [--scripts-dir scripts] [--force]
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const SKILL = dirname(fileURLToPath(import.meta.url))
const CHECKS = join(SKILL, 'checks')
const TEMPLATES = join(SKILL, 'templates')
const TREE_TEST = 'react-app-tree.test.mjs'
const TESTS = ['check-css.test.mjs', 'check-structure.test.mjs', TREE_TEST]

function options(argv) {
  const parsed = { app: null, force: false, scriptsDir: 'scripts' }
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--force') parsed.force = true
    else if (argv[index] === '--scripts-dir') parsed.scriptsDir = argv[(index += 1)]
    else if (!parsed.app) parsed.app = resolve(argv[index])
    else throw new Error(`Unknown argument: ${argv[index]}`)
  }
  if (!parsed.app) throw new Error('usage: node install-checks.mjs <app-dir> [--scripts-dir scripts] [--force]')
  return parsed
}

function copyChecks(target, force) {
  mkdirSync(target, { recursive: true })
  const files = readdirSync(CHECKS).filter((name) => name.endsWith('.mjs'))
  const sources = [...files.map((name) => [name, join(CHECKS, name)]), [TREE_TEST, join(TEMPLATES, TREE_TEST)]]
  const clashes = sources
    .filter(([name, source]) => {
      const path = join(target, name)
      return existsSync(path) && readFileSync(path, 'utf8') !== readFileSync(source, 'utf8')
    })
    .map(([name]) => name)
  if (clashes.length && !force) {
    throw new Error(`Would overwrite ${clashes.join(', ')} in ${target}; compare them, then rerun with --force.`)
  }
  for (const name of files) copyFileSync(join(CHECKS, name), join(target, name))
  copyFileSync(join(TEMPLATES, TREE_TEST), join(target, TREE_TEST))
  return [...files, TREE_TEST]
}

function wireScripts(pkg, dir, notes) {
  const scripts = (pkg.scripts ??= {})
  scripts['check:css'] = `node ${dir}/check-css.mjs`
  scripts['check:structure'] = `node ${dir}/check-structure.mjs`
  const gate = 'npm run check:css && npm run check:structure'
  if (!scripts.build) notes.push('No build script: run check:css and check:structure from whatever builds the app.')
  else if (!scripts.build.includes('check:structure')) {
    scripts.build = `${gate} && ${scripts.build.replace(/npm run check:css && /, '')}`
  }
  const covered = scripts.test?.includes(`node --test ${dir}/*.test.mjs`)
  if (!covered) {
    scripts['test:react-app'] = `node --test ${TESTS.map((name) => `${dir}/${name}`).join(' ')}`
    const placeholder = !scripts.test || /no test specified/.test(scripts.test)
    scripts.test = placeholder ? 'npm run test:react-app' : `${scripts.test} && npm run test:react-app`
  }
  if (/\bvitest\b/.test(scripts.test ?? '')) {
    notes.push(`vitest collects **/*.test.mjs: add "${dir}/**" to test.exclude in the vitest config.`)
  }
}

async function main() {
  const { app, force, scriptsDir } = options(process.argv.slice(2))
  const packagePath = join(app, 'package.json')
  const raw = readFileSync(packagePath, 'utf8')
  const pkg = JSON.parse(raw)
  const deps = { ...pkg.dependencies, ...pkg.devDependencies }
  if (!deps['react-dom'] && !deps.preact) throw new Error(`${packagePath} depends on neither react-dom nor preact.`)
  const files = copyChecks(join(app, scriptsDir), force)
  const notes = []
  wireScripts(pkg, scriptsDir, notes)
  const indent = /^(\s+)"/m.exec(raw)?.[1] ?? '  '
  writeFileSync(packagePath, `${JSON.stringify(pkg, null, indent)}\n`)
  console.log(`Copied ${files.length} files to ${join(app, scriptsDir)} and wired package.json.`)
  for (const note of notes) console.log(`NOTE: ${note}`)
  const load = (name) => import(pathToFileURL(join(app, scriptsDir, name)).href)
  const { checkCss } = await load('check-css.mjs')
  const { checkStructure } = await load('check-structure.mjs')
  for (const [label, check] of [['CSS', checkCss], ['Structure', checkStructure]]) {
    const violations = check({ root: app })
    const byRule = Object.groupBy(violations, (item) => item.rule)
    const counts = Object.entries(byRule).map(([rule, items]) => `${rule} ${items.length}`)
    console.log(`${label}: ${violations.length ? counts.join(', ') : 'clean'}`)
  }
  console.log('The build and npm test stay red until every finding is fixed or exempted.')
}

main().catch((error) => {
  console.error(error.message)
  process.exitCode = 1
})
