// Re-render hand-drawn diagrams from SVG to PNG.
//
//   node docs/agents/render-diagrams.mjs                  # every .svg in this folder
//   node docs/agents/render-diagrams.mjs ticket-lifecycle-lanes
//   node docs/agents/render-diagrams.mjs docs/design/foundation-components.svg
//
// A bare name is looked for next to this script; a path is taken as given, so a
// hand-drawn diagram living beside the doc that embeds it renders too. The PNG is
// always written next to its SVG.
//
// Only hand-drawn diagrams come through here. Mermaid diagrams go through mmdc
// with docs/agents/mermaid-theme.json — see docs/agents/diagramming.md.
//
// Why this exists rather than a one-line converter: the SVGs name web fonts
// (IBM Plex Sans, IBM Plex Mono, Space Grotesk) that rsvg-convert and friends
// cannot fetch. They fall back to system fonts, every text width changes, and
// labels that were clear of their arrows stop being clear. So the render goes
// through a real browser with the fonts loaded.
//
// Chrome comes from the puppeteer that ships with mermaid-cli, which this repo
// already uses for the Mermaid diagrams elsewhere in docs/. If `mmdc` is not
// installed, install it first: npm i -g @mermaid-js/mermaid-cli

import { createRequire } from 'module';
import { execFileSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCALE = 2;

const FONTS =
  'https://fonts.googleapis.com/css2' +
  '?family=IBM+Plex+Mono:wght@400;500' +
  '&family=IBM+Plex+Sans:wght@400;500;600' +
  '&family=Space+Grotesk:wght@500;700&display=swap';

// Each SVG carries its own size in its viewBox, so a name is all we need. With
// no arguments, render every hand-drawn diagram sitting next to this script.
function located(argument) {
  const named = argument.endsWith('.svg') ? argument : `${argument}.svg`;
  for (const candidate of [path.resolve(named), path.join(HERE, path.basename(named))]) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error(`no such SVG: ${argument}`);
}

const DIAGRAMS = process.argv.slice(2).length
  ? process.argv.slice(2).map(located)
  : fs
      .readdirSync(HERE)
      .filter((f) => f.endsWith('.svg'))
      .map((f) => path.join(HERE, f))
      .sort();

if (!DIAGRAMS.length) {
  console.log('No .svg files next to this script — nothing to render.');
  process.exit(0);
}

function findPuppeteer() {
  const mmdc = execFileSync('sh', ['-c', 'command -v mmdc'], { encoding: 'utf8' }).trim();
  if (!mmdc) throw new Error('mmdc not found — npm i -g @mermaid-js/mermaid-cli');
  return createRequire(fs.realpathSync(mmdc))('puppeteer');
}

const puppeteer = findPuppeteer();
const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox'] });

for (const source of DIAGRAMS) {
  const name = path.basename(source, '.svg');
  const svg = fs.readFileSync(source, 'utf8');
  const box = /viewBox="0 0 (\d+) (\d+)"/.exec(svg);
  if (!box) throw new Error(`${name}.svg has no viewBox to size the render by`);
  const [width, height] = [Number(box[1]), Number(box[2])];

  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: SCALE });
  await page.setContent(
    `<!doctype html><html><head><meta charset="utf-8">` +
      `<link href="${FONTS}" rel="stylesheet">` +
      `<style>html,body{margin:0;padding:0;background:#0F1622}svg{display:block}</style>` +
      `</head><body>${svg}</body></html>`,
    { waitUntil: 'networkidle0' },
  );
  await page.evaluate(() => document.fonts.ready);

  const out = source.replace(/\.svg$/, '.png');
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width, height } });
  await page.close();
  console.log(`${name}.svg → ${name}.png  (${width}×${height} at ${SCALE}x)`);
}

await browser.close();
