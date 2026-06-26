---
description: Generate an Excalidraw diagram and save it as .excalidraw.md into the MoxyWolf Vault so the zsviczian Obsidian Excalidraw plugin renders it natively
argument-hint: "<description-of-diagram> [--scope Projects/<project> | --shared] [--name <slug>] [--type architecture|flow|mindmap|sequence|relationship]"
---

Generate an Excalidraw diagram from a natural-language description and write it into the MoxyWolf Vault as a properly-formatted `.excalidraw.md` file. The file opens directly in Obsidian's Excalidraw plugin and can be embedded in any note via `![[<filename>]]`.

## Steps

1. **Parse `$ARGUMENTS`**: extract the diagram description, optional `--scope`, optional `--name`, optional `--type`. If `--scope` is omitted, default to `_Shared Knowledge/Diagrams/`. If `--name` is omitted, derive a kebab-case slug from the description (e.g. "uber-brain architecture" → `uber-brain-architecture`).

2. **Read the runner protocol** at `${CLAUDE_PLUGIN_ROOT}/skills/excalidraw-vault-core/SKILL.md`, especially *Obsidian wrapping format*, *Element schema*, and *Routing*.

3. **Plan the diagram** before generating JSON:
   - Identify the concepts, relationships, and hierarchy in the description.
   - Pick a diagram type if not given: architecture (boxes + arrows + groups), flow (sequential steps), mindmap (radial), sequence (lanes), relationship (entities + labeled edges).
   - For complex diagrams (>20 elements), build in sections: title bar → primary nodes → connectors → annotations. The skill's *Depth assessment* guidance is load-bearing here.

4. **Generate the Excalidraw JSON** following the element schema in the skill — every element gets the required fields (`id`, `type`, `x`, `y`, `width`, `height`, `angle`, `strokeColor`, `backgroundColor`, `fillStyle`, `strokeWidth`, `strokeStyle`, `roughness`, `opacity`, `groupIds`, `roundness`, `seed`, `version`, `isDeleted`, `boundElements: null`, `updated: 1`, `link`, `locked`). Text elements use `fontFamily: 5` (Excalifont) by default.

5. **Wrap in the Obsidian format** exactly as shown in `references/obsidian-format.md`:
   - Frontmatter: `excalidraw-plugin: parsed` + `tags: [excalidraw]`.
   - The warning banner line (preserved verbatim).
   - `# Excalidraw Data` → `## Text Elements` (empty, just `%%`) → `## Drawing` with ```json fenced block → closing `%%`.
   - JSON `source` field set to `https://github.com/zsviczian/obsidian-excalidraw-plugin`.

6. **Route the file** per the skill's *Routing* table:
   - `--scope Projects/<project>` → `MoxyWolf Vault/Projects/<project>/06-Engineering/diagrams/<name>.excalidraw.md`
   - `--shared` or default → `MoxyWolf Vault/_Shared Knowledge/Diagrams/<name>.excalidraw.md`
   - Vault path resolves from `$MW_VAULT_PATH` if set, else the canonical Google Drive mount.

7. **Confirm path with the user** before writing. If a file exists at the target path, ask before overwriting.

8. **Write the file** to the vault via Desktop Commander (the vault is cloud-synced — do not write through the sandbox).

9. **Report in chat**:
   - The vault-relative path.
   - The exact wikilink to paste into any note: `![[<name>.excalidraw]]` (Obsidian resolves `.excalidraw.md` from the basename).
   - A 1-line description of the diagram structure.
   - Reminder: open in Obsidian, then "Switch to EXCALIDRAW VIEW" from the More Options menu if it opens as markdown.

## Notes

- The Obsidian Excalidraw plugin (zsviczian) treats `.excalidraw.md` as the preferred format. Plain `.md` with `excalidraw-plugin: parsed` frontmatter also works.
- The `## Text Elements` section stays empty — the plugin auto-fills it from the JSON.
- For embedding in DRs, specs, or decks, use `![[<name>.excalidraw]]` — it renders as a PNG inline.
- These files live in the same git-backed vault as everything else, so they version normally and survive obsidian-update / vault-code-learn passes (which should skip them — they're derived artifacts).
