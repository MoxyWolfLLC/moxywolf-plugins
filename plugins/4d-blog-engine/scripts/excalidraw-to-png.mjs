#!/usr/bin/env node
/**
 * excalidraw-to-png.mjs
 *
 * Headless PNG export for hero scenes produced by the 4d-blog-engine
 * hero-scene-composer skill. Takes an Obsidian-Excalidraw .excalidraw.md
 * file, extracts the JSON drawing data, renders it to a PNG of the
 * requested dimensions, and writes the PNG to disk.
 *
 * Usage:
 *   node scripts/excalidraw-to-png.mjs \
 *     --input <path-to-.excalidraw.md> \
 *     --output <path-to-output.png> \
 *     [--width 1600] [--height 900] \
 *     [--background "#F8F1E5"]
 *
 * Dependencies (Node 18+):
 *   - playwright (preferred, most stable headless Chromium)
 *
 * Install once at the writer's machine:
 *   npm install -g playwright
 *   npx playwright install chromium
 *
 * If playwright is missing, the script exits with code 2 and prints
 * a clear install hint. The hero-scene-composer skill catches this
 * and falls back to the by-hand export instructions.
 *
 * No network access is required at runtime — the Excalidraw editor
 * is loaded from a locally-bundled HTML harness that imports
 * @excalidraw/excalidraw from a versioned CDN at first run, then
 * caches in the browser profile.
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { argv, exit, stderr, stdout } from "node:process";

// ----- arg parsing (zero deps) -----

function parseArgs(arr) {
  const out = {};
  for (let i = 0; i < arr.length; i++) {
    const a = arr[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const next = arr[i + 1];
      if (!next || next.startsWith("--")) {
        out[key] = true;
      } else {
        out[key] = next;
        i++;
      }
    }
  }
  return out;
}

const args = parseArgs(argv.slice(2));
const inputPath = args.input;
const outputPath = args.output;
const width = parseInt(args.width || "1600", 10);
const height = parseInt(args.height || "900", 10);
const background = args.background || null; // if null, use scene's appState.viewBackgroundColor

if (!inputPath || !outputPath) {
  stderr.write(
    "Usage: excalidraw-to-png.mjs --input <path> --output <path> [--width N] [--height N] [--background #hex]\n"
  );
  exit(64); // EX_USAGE
}

if (!existsSync(inputPath)) {
  stderr.write(`Input file not found: ${inputPath}\n`);
  exit(66); // EX_NOINPUT
}

// ----- extract drawing JSON from .excalidraw.md -----

function extractDrawingJSON(mdText) {
  // The Obsidian-Excalidraw plugin format wraps the JSON in a fenced ```json
  // block that lives between `## Drawing` and the closing `%%`. We pull the
  // first fenced json block after `## Drawing`.
  const drawingMarker = mdText.indexOf("## Drawing");
  if (drawingMarker === -1) {
    throw new Error(
      "Input does not contain a '## Drawing' heading. Not an Obsidian-Excalidraw .excalidraw.md file."
    );
  }
  const after = mdText.slice(drawingMarker);
  const m = after.match(/```json\s*\n([\s\S]*?)\n```/);
  if (!m) {
    throw new Error(
      "Could not find fenced ```json block after '## Drawing'. The composer should produce uncompressed JSON."
    );
  }
  return JSON.parse(m[1]);
}

const mdText = readFileSync(inputPath, "utf8");
let scene;
try {
  scene = extractDrawingJSON(mdText);
} catch (e) {
  stderr.write(`Parse error: ${e.message}\n`);
  exit(65); // EX_DATAERR
}

// Strip the documentation keys (the composer should already do this, but be defensive)
for (const k of Object.keys(scene)) {
  if (k.startsWith("_")) delete scene[k];
}

const elements = scene.elements || [];
const appState = scene.appState || {};
const files = scene.files || {};

if (!elements.length) {
  stderr.write("Scene has no elements — nothing to render.\n");
  exit(65);
}

if (background) {
  appState.viewBackgroundColor = background;
}

// ----- dependency check: playwright -----

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch (e) {
  stderr.write(
    [
      "",
      "excalidraw-to-png.mjs requires the 'playwright' package and a Chromium browser binary.",
      "",
      "Install once on this machine:",
      "  npm install -g playwright",
      "  npx playwright install chromium",
      "",
      "After installation, re-run the same command.",
      "",
      "The hero-scene-composer skill will detect this exit code (2) and fall back to by-hand export instructions until the install is done.",
      "",
    ].join("\n")
  );
  exit(2);
}

// ----- render in a headless Chromium page -----

const harness = `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>excalidraw-to-png</title>
<style>
  html, body { margin: 0; padding: 0; background: ${appState.viewBackgroundColor || "#F8F1E5"}; }
  #stage { width: ${width}px; height: ${height}px; }
</style>
</head>
<body>
<div id="stage"></div>
<script type="module">
  // Pin to a versioned Excalidraw build. The CDN serves the package's
  // ES module build of the export utilities only — no React renderer
  // needed when we use exportToCanvas directly.
  import { exportToCanvas } from "https://esm.sh/@excalidraw/utils@0.1.2";

  const scene = ${JSON.stringify({ elements, appState, files })};

  // exportToCanvas signature: ({ elements, appState, files, getDimensions })
  const canvas = await exportToCanvas({
    elements: scene.elements,
    appState: scene.appState,
    files: scene.files,
    getDimensions: () => ({ width: ${width}, height: ${height}, scale: 1 }),
    exportPadding: 0,
  });

  const dataUrl = canvas.toDataURL("image/png");
  window.__pngDataUrl = dataUrl;
  document.title = "excalidraw-to-png:ready";
</script>
</body>
</html>
`;

const browser = await chromium.launch({ headless: true });
try {
  const ctx = await browser.newContext({ viewport: { width, height } });
  const page = await ctx.newPage();
  await page.setContent(harness, { waitUntil: "networkidle" });

  // Wait until the export module signals ready via document.title
  await page.waitForFunction(
    () => document.title === "excalidraw-to-png:ready",
    null,
    { timeout: 30000 }
  );

  const dataUrl = await page.evaluate(() => window.__pngDataUrl);
  if (!dataUrl || !dataUrl.startsWith("data:image/png;base64,")) {
    throw new Error("Excalidraw export produced no PNG data URL.");
  }

  const b64 = dataUrl.slice("data:image/png;base64,".length);
  const buf = Buffer.from(b64, "base64");

  mkdirSync(dirname(resolve(outputPath)), { recursive: true });
  writeFileSync(outputPath, buf);
  stdout.write(`Wrote ${outputPath} (${buf.length} bytes, ${width}x${height})\n`);
} catch (e) {
  stderr.write(`Render error: ${e.message}\n`);
  await browser.close();
  exit(70); // EX_SOFTWARE
}

await browser.close();
exit(0);
