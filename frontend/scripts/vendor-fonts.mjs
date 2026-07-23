// Downloads the latin / latin-ext woff2 files referenced by a Google Fonts CSS
// response and rewrites the CSS to point at local paths.
import { readFile, writeFile, mkdir } from 'node:fs/promises'

const SRC = process.argv[2]
const OUT_DIR = process.argv[3]
const OUT_CSS = process.argv[4]

const css = await readFile(SRC, 'utf8')
await mkdir(OUT_DIR, { recursive: true })

// Blocks look like: /* subset */\n@font-face { ... }
const blocks = css.split(/(?=\/\* [a-z-]+ \*\/)/).filter(Boolean)
const kept = []

for (const block of blocks) {
  const subset = block.match(/\/\* ([a-z-]+) \*\//)?.[1]
  if (subset !== 'latin' && subset !== 'latin-ext') continue

  const family = block.match(/font-family: '([^']+)'/)[1]
  const style = block.match(/font-style: (\w+)/)[1]
  const weight = block.match(/font-weight: ([\d ]+)/)[1].replace(/ /g, '-')
  const url = block.match(/src: url\(([^)]+)\)/)[1]

  const slug = family.toLowerCase().replace(/\s+/g, '-')
  const name = `${slug}-${weight}${style === 'italic' ? '-italic' : ''}-${subset}.woff2`

  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  await writeFile(`${OUT_DIR}/${name}`, Buffer.from(await res.arrayBuffer()))

  kept.push(block.replace(url, `./fonts/${name}`).trimEnd())
  console.log(`${name}  ${(res.headers.get('content-length') / 1024).toFixed(1)}kB`)
}

const header = `/*
 * Self-hosted webfonts — latin + latin-ext subsets only, woff2.
 * Sourced from Google Fonts; all three families are SIL Open Font License 1.1.
 * Regenerate with scripts/vendor-fonts.mjs rather than editing by hand.
 */\n`

await writeFile(OUT_CSS, header + kept.join('\n') + '\n')
console.log(`\n${kept.length} faces -> ${OUT_CSS}`)
