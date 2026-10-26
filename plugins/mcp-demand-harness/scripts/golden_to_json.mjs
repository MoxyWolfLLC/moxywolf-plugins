#!/usr/bin/env node
// Convert a TypeScript golden-set module to plain JSON so the stdlib Python
// seeder can read it without a TS parser.
//
//   node golden_to_json.mjs <repo> <path/to/golden-set.ts> <out.json> [EXPORT_NAME]
//
// Uses the `typescript` package the target repo already depends on (resolved
// from the repo, then from this plugin's cwd). Types are stripped with
// transpileModule, never type-checked: this reads data, it does not build.
// RegExp values become {source, flags} because JSON has no regex type and a
// pattern that silently became a string would match literally.

import { createRequire } from 'node:module'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'

const [repo, rel, out, exportName = 'GOLDEN_SET'] = process.argv.slice(2)
if (!repo || !rel || !out) {
  console.error('usage: golden_to_json.mjs <repo> <golden-set.ts> <out.json> [EXPORT_NAME]')
  process.exit(2)
}

const source = resolve(repo, rel)
let ts
for (const base of [repo, join(repo, 'apps/web'), process.cwd()]) {
  try {
    ts = createRequire(join(resolve(base), 'noop.js'))('typescript')
    break
  } catch {}
}
if (!ts) {
  console.error('ERROR typescript not found. Run pnpm install in the repo, or npm i typescript in the plugin folder.')
  process.exit(3)
}

const code = ts.transpileModule(readFileSync(source, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText

if (/^\s*import\s/m.test(code)) {
  console.error('ERROR the golden set imports other modules; only self-contained data modules are supported.')
  process.exit(4)
}

const tmp = join(dirname(resolve(out)), '.golden-set.tmp.mjs')
mkdirSync(dirname(resolve(out)), { recursive: true })
writeFileSync(tmp, code)
const mod = await import(pathToFileURL(tmp).href + `?t=${Date.now()}`)
const data = mod[exportName]
if (!Array.isArray(data)) {
  console.error(`ERROR export ${exportName} is not an array`)
  process.exit(5)
}

const json = JSON.stringify(
  { source: rel, export: exportName, items: data },
  (_k, v) => (v instanceof RegExp ? { $regex: v.source, flags: v.flags } : v),
  2,
)
writeFileSync(out, json + '\n')
try {
  (await import('node:fs')).unlinkSync(tmp)
} catch {}
console.log(`items=${data.length} wrote ${out}`)
