# Element templates

Drop-in JSON for common Excalidraw element types. All include the mandatory fields per the skill's element schema section.

## Rectangle (node / box)

```json
{
  "id": "rect-1",
  "type": "rectangle",
  "x": 100, "y": 100, "width": 200, "height": 80,
  "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "#a5d8ff",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": { "type": 3 },
  "seed": 100001, "version": 1, "isDeleted": false,
  "boundElements": null, "updated": 1, "link": null, "locked": false
}
```

## Ellipse

```json
{
  "id": "ell-1",
  "type": "ellipse",
  "x": 100, "y": 100, "width": 160, "height": 100,
  "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "#ffd8a8",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": { "type": 2 },
  "seed": 100002, "version": 1, "isDeleted": false,
  "boundElements": null, "updated": 1, "link": null, "locked": false
}
```

## Diamond (decision)

```json
{
  "id": "dia-1",
  "type": "diamond",
  "x": 100, "y": 100, "width": 160, "height": 100,
  "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "#ffd6e0",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": { "type": 2 },
  "seed": 100003, "version": 1, "isDeleted": false,
  "boundElements": null, "updated": 1, "link": null, "locked": false
}
```

## Text

```json
{
  "id": "txt-1",
  "type": "text",
  "x": 130, "y": 130, "width": 140, "height": 24,
  "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
  "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": null,
  "seed": 100004, "version": 1, "isDeleted": false,
  "boundElements": null, "updated": 1, "link": null, "locked": false,
  "text": "Label text",
  "fontSize": 20,
  "fontFamily": 5,
  "textAlign": "center",
  "verticalAlign": "middle",
  "baseline": 18
}
```

## Arrow (with bindings)

`points` is relative to `x`,`y`. `startBinding`/`endBinding` reference element `id`s.

```json
{
  "id": "arr-1",
  "type": "arrow",
  "x": 300, "y": 140, "width": 120, "height": 0,
  "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": { "type": 2 },
  "seed": 100005, "version": 1, "isDeleted": false,
  "boundElements": null, "updated": 1, "link": null, "locked": false,
  "points": [[0, 0], [120, 0]],
  "startBinding": { "elementId": "rect-1", "focus": 0, "gap": 4 },
  "endBinding":   { "elementId": "rect-2", "focus": 0, "gap": 4 },
  "lastCommittedPoint": null,
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

## Line (no arrowhead)

Same as arrow but `type: "line"` and no `startArrowhead` / `endArrowhead`.

## Color palette (Excalidraw defaults)

Use these for consistent visual language across diagrams:

| Role | Stroke | Fill |
|---|---|---|
| Primary node | `#1e1e1e` | `#a5d8ff` (blue) |
| Service / system | `#1e1e1e` | `#b2f2bb` (green) |
| Data store | `#1e1e1e` | `#ffd8a8` (orange) |
| Decision | `#1e1e1e` | `#ffd6e0` (pink) |
| External / third-party | `#1e1e1e` | `#e9ecef` (gray) |
| Highlight / warning | `#e03131` | `#ffc9c9` (red) |

`#1e1e1e` is the default stroke. Avoid pure black `#000000` — Excalidraw conventions use the warm-dark gray.

## Seed values

Seeds drive the hand-drawn jitter. Use unique seeds per element (any positive integer). Sequential `100001, 100002, ...` is fine — the hand-drawn variation is determined by the seed value, not the spacing.
