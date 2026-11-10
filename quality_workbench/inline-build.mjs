import { readFile, rm, writeFile } from 'node:fs/promises';

const entry = new URL('./dist/index.html', import.meta.url);
const html = await readFile(entry, 'utf8');
const scriptTag = html.match(/<script type="module" crossorigin src="\.\/([^"<>]+)"><\/script>/);
const styleTag = html.match(/<link rel="stylesheet" crossorigin href="\.\/([^"<>]+)">/);
if (!scriptTag || !styleTag) throw new Error('Expected one Vite script and stylesheet');

const scriptFile = new URL(scriptTag[1], entry);
const styleFile = new URL(styleTag[1], entry);
const [script, style] = await Promise.all([readFile(scriptFile, 'utf8'), readFile(styleFile, 'utf8')]);
const bundled = html
  .replace(scriptTag[0], () => `<script type="module">${script.replace(/<\/script/gi, '<\\/script')}</script>`)
  .replace(styleTag[0], () => `<style>${style}</style>`);
await writeFile(entry, bundled);
await Promise.all([rm(scriptFile), rm(styleFile)]);
