# Excalidraw Icon Vocabulary

> Library of hand-drawn icon primitives the hero-scene-composer drops into the canvas template. Each icon is a small set of Excalidraw JSON elements at coordinates **relative to `(0, 0)`** — the composer translates by adding the slot anchor's `(x, y)` to each element's `x` and `y`. Every icon fits inside a **140×140** bounding box; the composer also places a separate text label below the icon (≤ 18 chars, centered).

## How to use this file

1. Look up the icon by `name` (the keys in the registry below).
2. Copy the JSON element array.
3. For each element, set:
   - `x = anchor_x + relative_x + slot_offset_x`
   - `y = anchor_y + relative_y + slot_offset_y`
   - `id = <icon-name>-<element-tag>-<scene-seq>` (e.g. `vault-body-3`)
   - `seed`, `version`, `versionNonce` = arbitrary stable integers
   - `strokeColor` from brand `accent` (e.g. `#2C3E50`)
   - `backgroundColor` from brand `secondary` for filled accents (e.g. `#C9A66B`), else `transparent`
4. Append a text element below the icon's bounding box for the label (icon bottom + 8px gap, fontSize 18, fontFamily 1, color `#1A1A1A`, centered).

## Grid placement rules

The composer places icons in a grid inside the panel slot. For an icon count `n`:

| Icons | Grid | Cell size | Spacing |
|---|---|---|---|
| 1 | 1×1 | full slot | n/a |
| 2 | 2×1 horizontal | 290×400 | 60px gap |
| 3 | 3×1 horizontal | 180×400 | 50px gap |
| 4 | 2×2 | 290×190 | 60px h, 40px v |
| 5 | 1×5 vertical (stack-of-plates pattern) | 600×80 | 12px v |
| 6 | 3×2 | 180×190 | 50px h, 40px v |

The `1×5 vertical` pattern is reserved for "layered tape" scenes (uber-brain, memory stacks). For 5 icons NOT depicting layers, use 3×2 with one slot empty.

---

## Registry

Every entry uses:
- `roughness: 1` (hand-drawn feel)
- `strokeWidth: 2`
- `fillStyle: hachure` for filled shapes; `solid` for line-only
- `fontFamily: 1` (Virgil — hand-drawn font)
- Relative coordinates inside a 140×140 box, origin top-left

### `vault`

A safe/vault with a circular dial and a small handle. Use for: durable knowledge stores, the Vault layer, archives, authoritative records.

```json
[
  { "tag": "body", "type": "rectangle", "x": 10, "y": 20, "width": 120, "height": 100, "roundness": { "type": 3 }, "fillStyle": "hachure" },
  { "tag": "dial", "type": "ellipse", "x": 45, "y": 50, "width": 50, "height": 50, "fillStyle": "solid", "fill": "secondary" },
  { "tag": "dial-inner", "type": "ellipse", "x": 60, "y": 65, "width": 20, "height": 20, "fillStyle": "solid", "fill": "ground" },
  { "tag": "handle", "type": "line", "points": [[115, 70], [130, 80]], "strokeWidth": 3 }
]
```

### `brain`

A two-lobed brain outline. Use for: cognition, agents, judgment, knowledge.

```json
[
  { "tag": "left-lobe", "type": "ellipse", "x": 10, "y": 30, "width": 65, "height": 80 },
  { "tag": "right-lobe", "type": "ellipse", "x": 65, "y": 30, "width": 65, "height": 80 },
  { "tag": "fold-1", "type": "line", "points": [[30, 60], [60, 80]], "strokeWidth": 1 },
  { "tag": "fold-2", "type": "line", "points": [[80, 60], [110, 80]], "strokeWidth": 1 },
  { "tag": "stem", "type": "line", "points": [[70, 110], [70, 130]], "strokeWidth": 2 }
]
```

### `graph`

Three connected nodes (not a giant network — deliberately small to avoid the network-graph cliché). Use for: graphify, connections, links.

```json
[
  { "tag": "node-a", "type": "ellipse", "x": 10, "y": 30, "width": 24, "height": 24, "fillStyle": "solid", "fill": "secondary" },
  { "tag": "node-b", "type": "ellipse", "x": 60, "y": 80, "width": 24, "height": 24, "fillStyle": "solid", "fill": "secondary" },
  { "tag": "node-c", "type": "ellipse", "x": 110, "y": 30, "width": 24, "height": 24, "fillStyle": "solid", "fill": "secondary" },
  { "tag": "edge-ab", "type": "line", "points": [[28, 48], [66, 86]], "strokeWidth": 2 },
  { "tag": "edge-bc", "type": "line", "points": [[80, 86], [116, 48]], "strokeWidth": 2 },
  { "tag": "edge-ac", "type": "line", "points": [[28, 42], [116, 42]], "strokeWidth": 1, "strokeStyle": "dashed" }
]
```

### `code_window`

A window with a title bar and three lines of "code" (just horizontal strokes). Use for: vault-code-learn, code memory, repositories, scripts.

```json
[
  { "tag": "frame", "type": "rectangle", "x": 5, "y": 20, "width": 130, "height": 100, "roundness": { "type": 3 } },
  { "tag": "title-bar", "type": "rectangle", "x": 5, "y": 20, "width": 130, "height": 18, "fillStyle": "solid", "fill": "secondary" },
  { "tag": "dot-1", "type": "ellipse", "x": 12, "y": 25, "width": 8, "height": 8, "fillStyle": "solid", "fill": "accent" },
  { "tag": "dot-2", "type": "ellipse", "x": 26, "y": 25, "width": 8, "height": 8, "fillStyle": "solid", "fill": "accent" },
  { "tag": "dot-3", "type": "ellipse", "x": 40, "y": 25, "width": 8, "height": 8, "fillStyle": "solid", "fill": "accent" },
  { "tag": "line-1", "type": "line", "points": [[20, 55], [90, 55]], "strokeWidth": 2 },
  { "tag": "line-2", "type": "line", "points": [[20, 75], [110, 75]], "strokeWidth": 2 },
  { "tag": "line-3", "type": "line", "points": [[20, 95], [70, 95]], "strokeWidth": 2 }
]
```

### `capture_pad`

A small notepad with lines and a corner curl. Use for: obsidian-update, daily capture, intake, journaling.

```json
[
  { "tag": "page", "type": "rectangle", "x": 20, "y": 15, "width": 95, "height": 115, "roundness": { "type": 3 } },
  { "tag": "binding", "type": "line", "points": [[20, 30], [115, 30]], "strokeWidth": 1 },
  { "tag": "line-1", "type": "line", "points": [[30, 50], [105, 50]], "strokeWidth": 1 },
  { "tag": "line-2", "type": "line", "points": [[30, 70], [100, 70]], "strokeWidth": 1 },
  { "tag": "line-3", "type": "line", "points": [[30, 90], [105, 90]], "strokeWidth": 1 },
  { "tag": "line-4", "type": "line", "points": [[30, 110], [85, 110]], "strokeWidth": 1 },
  { "tag": "curl", "type": "line", "points": [[100, 120], [115, 130], [115, 115]], "strokeWidth": 2 }
]
```

### `notebook`

A bound notebook (closed). Use for: notes, papers, drafts, generic documents when nothing more specific applies.

```json
[
  { "tag": "cover", "type": "rectangle", "x": 15, "y": 15, "width": 110, "height": 110, "roundness": { "type": 3 }, "fillStyle": "hachure", "fill": "secondary" },
  { "tag": "spine", "type": "line", "points": [[25, 15], [25, 125]], "strokeWidth": 2 },
  { "tag": "title-line", "type": "line", "points": [[40, 55], [110, 55]], "strokeWidth": 2 },
  { "tag": "sub-line", "type": "line", "points": [[40, 75], [95, 75]], "strokeWidth": 1 }
]
```

### `envelope`

A sealed envelope with a flap and (optional) wax-seal dot. Use for: cold email, outreach, sending, communication.

```json
[
  { "tag": "body", "type": "rectangle", "x": 10, "y": 35, "width": 120, "height": 80, "roundness": { "type": 3 } },
  { "tag": "flap-left", "type": "line", "points": [[10, 35], [70, 80]], "strokeWidth": 2 },
  { "tag": "flap-right", "type": "line", "points": [[130, 35], [70, 80]], "strokeWidth": 2 },
  { "tag": "seal", "type": "ellipse", "x": 60, "y": 70, "width": 20, "height": 20, "fillStyle": "solid", "fill": "secondary" }
]
```

### `key`

A simple key with a round bow and a few teeth. Use for: access, secrets, credentials, OpenRouter key.

```json
[
  { "tag": "bow", "type": "ellipse", "x": 15, "y": 50, "width": 40, "height": 40 },
  { "tag": "bow-hole", "type": "ellipse", "x": 27, "y": 62, "width": 16, "height": 16 },
  { "tag": "shaft", "type": "line", "points": [[55, 70], [125, 70]], "strokeWidth": 3 },
  { "tag": "tooth-1", "type": "line", "points": [[100, 70], [100, 85]], "strokeWidth": 2 },
  { "tag": "tooth-2", "type": "line", "points": [[115, 70], [115, 90]], "strokeWidth": 2 }
]
```

### `lock`

A padlock (closed). Use for: governance, gates, controls, sign-off.

```json
[
  { "tag": "shackle", "type": "ellipse", "x": 45, "y": 20, "width": 50, "height": 50 },
  { "tag": "shackle-cover", "type": "rectangle", "x": 45, "y": 50, "width": 50, "height": 30, "fillStyle": "solid", "fill": "ground" },
  { "tag": "body", "type": "rectangle", "x": 30, "y": 60, "width": 80, "height": 65, "roundness": { "type": 3 }, "fillStyle": "hachure", "fill": "secondary" },
  { "tag": "keyhole", "type": "ellipse", "x": 64, "y": 80, "width": 12, "height": 12, "fillStyle": "solid", "fill": "accent" }
]
```

### `chart`

A 3-bar chart with a baseline. Use for: trends, before/after, KPIs, compounding.

```json
[
  { "tag": "axis", "type": "line", "points": [[15, 120], [125, 120]], "strokeWidth": 2 },
  { "tag": "bar-1", "type": "rectangle", "x": 25, "y": 85, "width": 25, "height": 35, "fillStyle": "hachure", "fill": "secondary" },
  { "tag": "bar-2", "type": "rectangle", "x": 60, "y": 60, "width": 25, "height": 60, "fillStyle": "hachure", "fill": "secondary" },
  { "tag": "bar-3", "type": "rectangle", "x": 95, "y": 25, "width": 25, "height": 95, "fillStyle": "hachure", "fill": "secondary" }
]
```

### `document`

A single sheet with a folded corner. Use for: ADRs, DRs, runbooks, specs, signed papers.

```json
[
  { "tag": "page", "type": "rectangle", "x": 25, "y": 15, "width": 90, "height": 115, "roundness": { "type": 3 } },
  { "tag": "fold", "type": "line", "points": [[95, 15], [95, 35], [115, 35]], "strokeWidth": 2 },
  { "tag": "line-1", "type": "line", "points": [[35, 55], [100, 55]], "strokeWidth": 1 },
  { "tag": "line-2", "type": "line", "points": [[35, 70], [105, 70]], "strokeWidth": 1 },
  { "tag": "line-3", "type": "line", "points": [[35, 85], [95, 85]], "strokeWidth": 1 },
  { "tag": "stamp", "type": "rectangle", "x": 75, "y": 100, "width": 30, "height": 18, "fillStyle": "solid", "fill": "secondary" }
]
```

### `signature`

A stylized signature swoosh. Use for: sign-off, authorship, the Release Owner Gate.

```json
[
  { "tag": "swoosh", "type": "line", "points": [[15, 80], [40, 50], [60, 90], [85, 60], [110, 85], [130, 70]], "strokeWidth": 3 },
  { "tag": "line", "type": "line", "points": [[10, 105], [130, 105]], "strokeWidth": 2 }
]
```

### `door`

A simple labeled door. Use for: thresholds, transitions, "leaving"/"entering", retired/launched.

```json
[
  { "tag": "frame", "type": "rectangle", "x": 30, "y": 15, "width": 80, "height": 115, "roundness": { "type": 3 } },
  { "tag": "panel", "type": "line", "points": [[45, 35], [95, 35], [95, 110], [45, 110], [45, 35]], "strokeWidth": 1 },
  { "tag": "knob", "type": "ellipse", "x": 85, "y": 70, "width": 8, "height": 8, "fillStyle": "solid", "fill": "secondary" }
]
```

### `clock`

A clock face with two hands. Use for: time, cadence, scheduled, weekly cron.

```json
[
  { "tag": "face", "type": "ellipse", "x": 15, "y": 15, "width": 110, "height": 110 },
  { "tag": "hour-hand", "type": "line", "points": [[70, 70], [70, 40]], "strokeWidth": 3 },
  { "tag": "minute-hand", "type": "line", "points": [[70, 70], [95, 60]], "strokeWidth": 2 },
  { "tag": "center", "type": "ellipse", "x": 67, "y": 67, "width": 8, "height": 8, "fillStyle": "solid", "fill": "accent" },
  { "tag": "tick-12", "type": "line", "points": [[70, 22], [70, 30]], "strokeWidth": 1 },
  { "tag": "tick-3", "type": "line", "points": [[113, 70], [105, 70]], "strokeWidth": 1 },
  { "tag": "tick-6", "type": "line", "points": [[70, 118], [70, 110]], "strokeWidth": 1 },
  { "tag": "tick-9", "type": "line", "points": [[27, 70], [35, 70]], "strokeWidth": 1 }
]
```

### `calendar`

A small calendar with a header band and grid dots. Use for: dates, deadlines, scheduling.

```json
[
  { "tag": "frame", "type": "rectangle", "x": 15, "y": 25, "width": 110, "height": 105, "roundness": { "type": 3 } },
  { "tag": "header", "type": "rectangle", "x": 15, "y": 25, "width": 110, "height": 22, "fillStyle": "solid", "fill": "secondary" },
  { "tag": "ring-1", "type": "line", "points": [[35, 15], [35, 30]], "strokeWidth": 3 },
  { "tag": "ring-2", "type": "line", "points": [[105, 15], [105, 30]], "strokeWidth": 3 },
  { "tag": "dot-1", "type": "ellipse", "x": 30, "y": 60, "width": 6, "height": 6, "fillStyle": "solid", "fill": "accent" },
  { "tag": "dot-2", "type": "ellipse", "x": 55, "y": 60, "width": 6, "height": 6, "fillStyle": "solid", "fill": "accent" },
  { "tag": "dot-3", "type": "ellipse", "x": 80, "y": 60, "width": 6, "height": 6, "fillStyle": "solid", "fill": "accent" },
  { "tag": "dot-4", "type": "ellipse", "x": 105, "y": 60, "width": 6, "height": 6, "fillStyle": "solid", "fill": "accent" },
  { "tag": "dot-5", "type": "ellipse", "x": 55, "y": 85, "width": 6, "height": 6, "fillStyle": "solid", "fill": "accent" },
  { "tag": "dot-6", "type": "ellipse", "x": 80, "y": 85, "width": 10, "height": 10, "fillStyle": "solid", "fill": "secondary" }
]
```

### `robot`

A simple "amnesiac agent" robot head. Use for: AI agents, especially the failing/forgetful one in problem panels.

```json
[
  { "tag": "head", "type": "rectangle", "x": 25, "y": 25, "width": 90, "height": 80, "roundness": { "type": 3 }, "fillStyle": "hachure", "fill": "secondary" },
  { "tag": "antenna", "type": "line", "points": [[70, 25], [70, 10]], "strokeWidth": 2 },
  { "tag": "antenna-dot", "type": "ellipse", "x": 65, "y": 4, "width": 10, "height": 10, "fillStyle": "solid", "fill": "accent" },
  { "tag": "eye-l", "type": "ellipse", "x": 40, "y": 50, "width": 14, "height": 14, "fillStyle": "solid", "fill": "ground" },
  { "tag": "eye-r", "type": "ellipse", "x": 86, "y": 50, "width": 14, "height": 14, "fillStyle": "solid", "fill": "ground" },
  { "tag": "mouth", "type": "line", "points": [[50, 85], [90, 85]], "strokeWidth": 2 },
  { "tag": "neck", "type": "line", "points": [[60, 105], [60, 120]], "strokeWidth": 2 },
  { "tag": "neck-2", "type": "line", "points": [[80, 105], [80, 120]], "strokeWidth": 2 }
]
```

### `question_mark`

A bold question mark in a circle. Use for: doubt, the agent's confusion, the "?" in problem panels.

```json
[
  { "tag": "ring", "type": "ellipse", "x": 25, "y": 25, "width": 90, "height": 90 },
  { "tag": "q-curve", "type": "line", "points": [[55, 50], [70, 40], [85, 50], [80, 65], [70, 75], [70, 85]], "strokeWidth": 4 },
  { "tag": "q-dot", "type": "ellipse", "x": 66, "y": 95, "width": 8, "height": 8, "fillStyle": "solid", "fill": "accent" }
]
```

### `ladder`

A 4-rung ladder. Use for: progression, climbing, stepwise improvement.

```json
[
  { "tag": "rail-l", "type": "line", "points": [[40, 15], [40, 125]], "strokeWidth": 3 },
  { "tag": "rail-r", "type": "line", "points": [[100, 15], [100, 125]], "strokeWidth": 3 },
  { "tag": "rung-1", "type": "line", "points": [[40, 35], [100, 35]], "strokeWidth": 2 },
  { "tag": "rung-2", "type": "line", "points": [[40, 60], [100, 60]], "strokeWidth": 2 },
  { "tag": "rung-3", "type": "line", "points": [[40, 85], [100, 85]], "strokeWidth": 2 },
  { "tag": "rung-4", "type": "line", "points": [[40, 110], [100, 110]], "strokeWidth": 2 }
]
```

### `scaffold`

A scaffold/trellis frame. Use for: public scaffolding, infrastructure, the toolkit itself.

```json
[
  { "tag": "post-l", "type": "line", "points": [[25, 15], [25, 130]], "strokeWidth": 3 },
  { "tag": "post-r", "type": "line", "points": [[115, 15], [115, 130]], "strokeWidth": 3 },
  { "tag": "rail-top", "type": "line", "points": [[25, 30], [115, 30]], "strokeWidth": 2 },
  { "tag": "rail-mid", "type": "line", "points": [[25, 70], [115, 70]], "strokeWidth": 2 },
  { "tag": "rail-bot", "type": "line", "points": [[25, 110], [115, 110]], "strokeWidth": 2 },
  { "tag": "cross-1", "type": "line", "points": [[25, 30], [115, 70]], "strokeWidth": 1 },
  { "tag": "cross-2", "type": "line", "points": [[115, 30], [25, 70]], "strokeWidth": 1 },
  { "tag": "cross-3", "type": "line", "points": [[25, 70], [115, 110]], "strokeWidth": 1 },
  { "tag": "cross-4", "type": "line", "points": [[115, 70], [25, 110]], "strokeWidth": 1 }
]
```

### `layer_plate`

A single layer/plate (use when stacking 5 layers vertically). Use for: a single layer in the 5-layer memory model.

```json
[
  { "tag": "plate", "type": "rectangle", "x": 5, "y": 35, "width": 130, "height": 70, "roundness": { "type": 3 }, "fillStyle": "hachure", "fill": "secondary" }
]
```

---

## Composer responsibilities

The composer skill:

1. Reads `scene-outline.json` and looks up each icon by `name`.
2. Resolves `fill: "secondary"` / `"accent"` / `"ground"` strings to the brand hex codes from the project marker's `## Hero image brand style` block.
3. Assigns unique `id`, `seed`, `version`, `versionNonce` integers per element (offset by a per-icon base + element index).
4. Translates relative coordinates to absolute by adding the slot anchor + grid cell offset.
5. Drops the resulting elements into the canvas template's `elements` array.
6. Appends a label text element below each icon (icon center x, icon bottom + 8px, fontSize 18, color `#1A1A1A`, textAlign "center").
7. For 5-icon vertical layer stacks, also renders a thin gold arrow on the right edge of the stack (start = top plate, end = bottom plate) labeled with the panel's `arrow_label`.

## Icon-not-found policy

If the extractor produced an icon `name` not in this registry, the composer:

1. Logs the missing name to `<piece>/04-diligence/og-hero-prompt.md` under `## Composer warnings`.
2. Falls back to `notebook` for the missing slot.
3. Continues — never blocks the gate on an icon miss.

The next time the registry is updated to add the missing icon, the gate can be re-run to regenerate the scene with the proper icon.
