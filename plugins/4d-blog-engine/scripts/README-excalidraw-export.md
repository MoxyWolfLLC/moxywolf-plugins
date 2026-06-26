# Hero PNG export — one-time setup

The 4d-blog-engine plugin renders blog hero images by composing a labeled Excalidraw scene and exporting it to PNG via the headless `excalidraw-to-png.mjs` script in this folder.

The script needs Playwright + a Chromium binary, installed once on the writer's machine:

```bash
npm install -g playwright
npx playwright install chromium
```

That's it. After install, `/4d-blog-engine:blog-pipeline` will export hero PNGs automatically as part of the Release Owner Gate.

If you skip this install, the gate still works — it will save the `.excalidraw.md` source to `<BLOG_PROJECT_DIR>/drafts/blog-media/<slug>.excalidraw.md` and ask you to open it in Obsidian's Excalidraw view and export PNG to `<piece>/04-diligence/og-hero.png` by hand. Either path produces the same final hero image; the script just removes the manual click.

The plugin **never** calls an AI image-generation model for heroes. Heroes are always deterministic Excalidraw compositions derived from the post's own H1, H2s, and named concrete nouns.
