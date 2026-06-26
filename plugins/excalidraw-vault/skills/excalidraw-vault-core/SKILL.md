---
name: excalidraw-vault-core
description: Runner protocol for generating Excalidraw diagrams directly into the MoxyWolf Vault in the zsviczian Obsidian-Excalidraw plugin's native .excalidraw.md format. Single source of truth for the wrapping format, element schema, depth assessment, and routing used by /excalidraw and /excalidraw-here.
---

# excalidraw-vault-core

The canonical runner protocol for emitting Excalidraw diagrams into the MoxyWolf Vault. Both `/excalidraw` and `/excalidraw-here` delegate here. Future plugins that need to generate diagrams (board-deck, saas-frontend-designer, github-repo-analyzer) should reference this skill rather than reinventing the wrapping.

## Why a vault-native format

The Obsidian Excalidraw plugin (zsviczian) treats `.excalidraw.md` as the preferred storage format — a markdown file with `excalidraw-plugin: parsed` frontmatter and a fenced JSON block. Storing diagrams this way means:

- They render natively when opened in Obsidian (no separate canvas server, no external link).
- They embed in any note via `![[<name>.excalidraw]]` and render inline as a PNG.
- They version in the git-backed vault alongside the notes that reference them.
- They cross-link with the rest of the vault (graphify-vault picks up their backlinks if any text content is added between frontmatter and the `# Text Elements` heading).

The headless Excalidraw MCP servers (mcp.excalidraw.com, yctimlin/mcp_excalidraw-canvas) do **not** write to this format — they live outside the vault. This skill replaces them for MoxyWolf's "everything in the vault" pattern.

## Obsidian wrapping format

Every diagram written to the vault MUST follow this structure exactly:

```
---
excalidraw-plugin: parsed
tags: [excalidraw]
---

==⚠ Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements

%%
## Drawing
```json
{ ...Excalidraw JSON... }
```
%%
```

Critical rules:

- Frontmatter MUST include `excalidraw-plugin: parsed` AND `tags: [excalidraw]`.
- The warning banner line is preserved verbatim — the plugin keys on it.
- `## Text Elements` stays empty (just `%%` on the next line). The plugin auto-fills it from the JSON.
- The JSON block is fenced with ```json (not ```excalidraw, not ```compressed-json — we do not compress).
- The closing `%%` must be present (it closes the embed wrapper).

See `references/obsidian-format.md` for a copy-pasteable template.

## JSON root structure

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
  "elements": [ /* ... */ ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

The `source` field MUST be the zsviczian GitHub URL when writing to the vault — that's what the Obsidian plugin checks. Setting it to `https://excalidraw.com` will make the file open in compatibility (read-only) mode.

## Element schema

Every element requires these fields (do not add extras like `frameId`, `index`, `versionNonce`, `rawText` — they cause issues on excalidraw.com round-trips):

```json
{
  "id": "unique-id-string",
  "type": "rectangle | ellipse | diamond | text | arrow | line | freedraw",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 50,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": { "type": 3 },
  "seed": 123456789,
  "version": 1,
  "isDeleted": false,
  "boundElements": null,
  "updated": 1,
  "link": null,
  "locked": false
}
```

- `boundElements` is `null`, not `[]`.
- `updated` is `1`, not a real timestamp (real timestamps cause noisy git diffs on no-op opens).
- Text elements additionally need `text`, `fontSize` (16/20/24/32), `fontFamily: 5` (Excalifont), `textAlign`, `verticalAlign`.
- Arrow elements need `points: [[0,0],[dx,dy]]` (relative) and optionally `startBinding`/`endBinding` to attach to nodes.

See `references/element-templates.md` for ready-to-use templates per element type.

## Depth assessment

Before generating JSON, classify the diagram by element count and structure:

| Tier | Elements | Approach |
|---|---|---|
| Simple | ≤ 10 | Generate in one pass. |
| Medium | 11–25 | Generate in two passes: layout skeleton (positions only) → fill content. |
| Complex | 26+ | Generate section-by-section: title bar → primary nodes → connectors → annotations. Validate after each section. |

For Medium and Complex, after generating the JSON, mentally walk the layout: do positions overlap? Are arrows attached to the right nodes? Are groups visually distinct? Adjust before writing.

## Routing

| Scope | Destination |
|---|---|
| `--shared` or default (no scope) | `_Shared Knowledge/Diagrams/<name>.excalidraw.md` |
| `--scope Projects/<project>` | `Projects/<project>/06-Engineering/diagrams/<name>.excalidraw.md` |
| `/excalidraw-here` (sibling to source note) | Same folder as source note, or `<source-folder>/diagrams/<name>.excalidraw.md` if `diagrams/` exists or is preferred |

Vault root resolves from `$MW_VAULT_PATH` if set, otherwise the canonical mount: `/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/MoxyWolf Vault`.

Filenames are kebab-case with a `.excalidraw.md` extension. Examples: `uber-brain-architecture.excalidraw.md`, `dr-routing-flow.excalidraw.md`.

## Writing path

The vault is cloud-synced Google Drive. From the sandbox, write via Desktop Commander / `pc files write` — never via raw filesystem APIs that would create local-only copies.

## Embedding into notes

Once written, any note can embed the diagram as a rendered image:

```markdown
![[uber-brain-architecture.excalidraw]]
```

Obsidian resolves `.excalidraw` from the basename (ignoring `.md`) and renders the diagram as a PNG. To embed a specific size: `![[uber-brain-architecture.excalidraw|600]]`.

## What NOT to do

- Don't use `compressed-json` fences — we keep diagrams readable and diffable.
- Don't put `excalidraw-plugin: raw` in frontmatter — that disables most plugin features.
- Don't add text content between the frontmatter and the warning banner — the plugin tolerates it but it makes diffs noisy.
- Don't write through the sandbox filesystem — the vault is cloud-synced; use Desktop Commander.
- Don't have obsidian-update or vault-code-learn ingest these files — they're derived artifacts. (They're already covered by the `_Templates/`, `99 – Archive/`, etc. exclusions in those skills; diagrams in `diagrams/` subfolders should be added to the ignore lists going forward.)
