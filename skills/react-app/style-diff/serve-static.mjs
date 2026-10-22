// Serves a built SPA folder on loopback with index.html fallback for client
// routes, for bundlers without a preview server (CRA, esbuild).
// usage: node serve-static.mjs <dir> <port>
import { createReadStream, existsSync, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, normalize, resolve, sep } from 'node:path'

const TYPES = {
  '.css': 'text/css',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.map': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json',
}

const [dirArg, portArg] = process.argv.slice(2)
if (!dirArg || !portArg) {
  console.error('usage: node serve-static.mjs <dir> <port>')
  process.exit(2)
}
const root = resolve(dirArg)

function fileFor(url) {
  const path = decodeURIComponent(new URL(url, 'http://x').pathname)
  const candidate = normalize(join(root, path))
  if (candidate !== root && !candidate.startsWith(root + sep)) return null
  if (existsSync(candidate) && statSync(candidate).isFile()) return candidate
  if (existsSync(join(candidate, 'index.html'))) return join(candidate, 'index.html')
  return extname(path) ? null : join(root, 'index.html')
}

createServer((request, response) => {
  const file = fileFor(request.url)
  if (!file) {
    response.writeHead(404).end('Not found')
    return
  }
  response.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' })
  createReadStream(file).pipe(response)
}).listen(Number(portArg), '127.0.0.1', () => {
  console.log(`Serving ${root} on http://127.0.0.1:${portArg}`)
})
