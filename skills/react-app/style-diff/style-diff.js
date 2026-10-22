// Computed-style and DOM diff between two builds of an app. Don't edit or run
// this file directly: make-run.mjs writes a copy with the app's CONFIG inlined
// in place of the marker below. Run that copy through Playwright's
// browser_run_code (an `async (page) =>` function). Colors are normalized
// through a canvas, so rgb() and oklch() serializations compare by their
// rendered sRGB value.
// codeshape: allow-functions browser_run_code takes one `async (page) =>` expression, so every helper nests inside it.
async (page) => {
  const CONFIG = /* STYLE_DIFF_CONFIG */ null
  const PROPS = ['display', 'position', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left', 'font-size', 'font-weight', 'font-family', 'font-style', 'line-height', 'letter-spacing', 'text-align', 'text-transform', 'color', 'background-color', 'background-image', 'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color', 'border-top-width', 'border-bottom-width', 'border-left-width', 'border-right-width', 'border-radius', 'box-shadow', 'outline-color', 'opacity', 'gap', 'grid-template-columns', 'flex-direction', 'justify-content', 'align-items', 'text-decoration-color', 'fill', 'stroke', 'z-index', 'transform', 'filter', 'visibility', 'object-fit', 'aspect-ratio', 'max-width', 'overflow-x']

  // Runs in the page: every element's computed style, box and class, keyed by
  // its tag/index path, plus the serialized body for the DOM diff.
  const collect = ({ props, ignore }) => {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 1
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    const cache = new Map()
    const norm = (c) => {
      if (cache.has(c)) return cache.get(c)
      ctx.clearRect(0, 0, 1, 1)
      ctx.fillStyle = '#000'
      ctx.fillStyle = c
      ctx.fillRect(0, 0, 1, 1)
      const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data
      const out = `rgba(${r},${g},${b},${a})`
      cache.set(c, out)
      return out
    }
    const colorRe = /(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\([^()]*\)|#[0-9a-fA-F]{3,8}\b/g
    const ignored = (el) => ignore.some((selector) => el.closest(selector))
    const path = (el) => {
      const parts = []
      for (let n = el; n && n.nodeType === 1 && n !== document.documentElement; n = n.parentElement) {
        parts.unshift(`${n.tagName.toLowerCase()}:${Array.prototype.indexOf.call(n.parentElement.children, n)}`)
      }
      return parts.join('>')
    }
    const styles = {}
    for (const el of [document.documentElement, ...document.querySelectorAll('body *')]) {
      if (ignored(el)) continue
      const cs = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      const rec = { rect: [r.x, r.y + scrollY, r.width, r.height].map((v) => Math.round(v)).join(',') }
      for (const p of props) rec[p] = cs.getPropertyValue(p).replace(colorRe, norm)
      rec.cls = el.getAttribute('class') || ''
      styles[path(el) || 'html'] = rec
    }
    const body = document.body.cloneNode(true)
    for (const selector of ignore) body.querySelectorAll(selector).forEach((el) => el.remove())
    return { styles, dom: body.outerHTML }
  }

  const applyTheme = async (theme) => {
    const { attribute, classes } = CONFIG.theme
    await page.evaluate(({ attribute, classes, theme }) => {
      const root = document.documentElement
      if (attribute) root.setAttribute(attribute, theme)
      if (classes) {
        for (const name of Object.values(classes)) if (name) root.classList.remove(name)
        if (classes[theme]) root.classList.add(classes[theme])
      }
    }, { attribute, classes, theme })
  }

  const runStep = async (step) => {
    if (step.click) await page.click(step.click)
    else if (step.hover) await page.hover(step.hover)
    else if (step.focus) await page.focus(step.focus)
    else if (step.press) await page.keyboard.press(step.press)
    else if (step.scroll) await page.evaluate((y) => scrollTo(0, y), step.scroll)
    if (step.wait) await page.waitForTimeout(step.wait)
  }

  const capture = async (origin, view, width, theme) => {
    await page.setViewportSize({ width, height: CONFIG.height })
    if (theme === 'light' || theme === 'dark') await page.emulateMedia({ colorScheme: theme })
    await page.goto(origin + view.route, { waitUntil: 'networkidle' })
    await page.addStyleTag({ content: '*,*::before,*::after{transition:none!important;animation:none!important;caret-color:transparent!important}' })
    await applyTheme(theme)
    for (const step of view.steps) await runStep(step)
    await page.evaluate(() => document.fonts.ready)
    await page.waitForTimeout(80)
    return page.evaluate(collect, { props: PROPS, ignore: CONFIG.ignore })
  }

  const colorDist = (a, b) => {
    const pa = [...a.matchAll(/rgba\((\d+),(\d+),(\d+),(\d+)\)/g)].map((m) => m.slice(1).map(Number))
    const pb = [...b.matchAll(/rgba\((\d+),(\d+),(\d+),(\d+)\)/g)].map((m) => m.slice(1).map(Number))
    if (!pa.length || pa.length !== pb.length) return null
    if (a.replace(/rgba\([^)]*\)/g, '') !== b.replace(/rgba\([^)]*\)/g, '')) return null
    let max = 0
    pa.forEach((c, i) => c.forEach((v, j) => { max = Math.max(max, Math.abs(v - pb[i][j])) }))
    return max
  }

  const normalizeDom = (html) => CONFIG.domNormalize.reduce((text, pattern) => text.replace(new RegExp(pattern, 'g'), ''), html)
  const firstDifference = (a, b) => {
    let i = 0
    while (i < a.length && a[i] === b[i]) i++
    return { base: a.slice(Math.max(0, i - 80), i + 120), next: b.slice(Math.max(0, i - 80), i + 120) }
  }

  const views = [
    ...CONFIG.routes.map((route) => ({ name: route, route, steps: [] })),
    ...CONFIG.states.map((state) => ({ steps: [], ...state })),
  ]
  const summary = { states: 0, missing: 0, extra: 0, byProp: {}, colorShiftMax: 0, colorShifts: {}, examples: [], missingExamples: [], dom: { differing: 0, examples: [] } }
  for (const view of views) {
    for (const width of CONFIG.widths) {
      for (const theme of CONFIG.themes) {
        const label = { view: view.name, width, theme }
        const a = await capture(CONFIG.base, view, width, theme)
        const b = await capture(CONFIG.next, view, width, theme)
        summary.states++
        const domA = normalizeDom(a.dom)
        const domB = normalizeDom(b.dom)
        if (domA !== domB) {
          summary.dom.differing++
          if (summary.dom.examples.length < 5) summary.dom.examples.push({ ...label, ...firstDifference(domA, domB) })
        }
        for (const key of Object.keys(a.styles)) {
          const ra = a.styles[key], rb = b.styles[key]
          if (!rb) {
            summary.missing++
            if (summary.missingExamples.length < 10) summary.missingExamples.push({ ...label, el: key })
            continue
          }
          for (const prop of Object.keys(ra)) {
            if (prop === 'cls') continue
            const va = ra[prop], vb = rb[prop]
            if (va === vb) continue
            const d = colorDist(va, vb)
            if (d !== null && d <= CONFIG.tolerance) continue
            if (d !== null) {
              summary.colorShiftMax = Math.max(summary.colorShiftMax, d)
              const k = `${prop}: ${va} -> ${vb}`
              summary.colorShifts[k] = (summary.colorShifts[k] || 0) + 1
              continue
            }
            summary.byProp[prop] = (summary.byProp[prop] || 0) + 1
            if (summary.examples.length < CONFIG.examples) {
              summary.examples.push({ ...label, el: `${key.split('>').slice(-2).join('>')} .${ra.cls}`, prop, base: va, next: vb })
            }
          }
        }
        for (const key of Object.keys(b.styles)) if (!a.styles[key]) summary.extra++
      }
    }
  }
  const shifts = Object.entries(summary.colorShifts).sort((x, y) => y[1] - x[1])
  summary.colorShiftCount = shifts.length
  summary.colorShifts = Object.fromEntries(shifts.slice(0, 40))
  summary.identical = summary.missing === 0 && summary.extra === 0 && summary.dom.differing === 0 && Object.keys(summary.byProp).length === 0 && shifts.length === 0
  return summary
}
