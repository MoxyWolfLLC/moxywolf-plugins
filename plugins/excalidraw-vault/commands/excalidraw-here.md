---
description: Generate an Excalidraw diagram of the current document/topic and save it next to the active note in the MoxyWolf Vault
argument-hint: "[--name <slug>] [--type architecture|flow|mindmap|sequence|relationship]"
---

Same as `/excalidraw`, but uses the **current document context** as the source material and saves the diagram next to that note instead of in a shared/project folder.

## Steps

1. **Determine source context**: read the current document the user is working in (active editor, last attached file, or the file most recently discussed in the conversation). If ambiguous, ask the user to confirm the source path.

2. **Determine destination**: place the diagram in the same folder as the source note, or in a sibling `diagrams/` subfolder if many diagrams are expected. Confirm the path with the user before writing.

3. **Parse `$ARGUMENTS`**: optional `--name` (defaults to a slug derived from the source note's title); optional `--type` (see `/excalidraw` for options).

4. **Read the runner protocol** at `${CLAUDE_PLUGIN_ROOT}/skills/excalidraw-vault-core/SKILL.md`.

5. **Analyze the source document** and extract the visual structure worth diagramming — section hierarchy, decision points, data flow, system components, relationships, etc. Confirm the chosen structure with the user before generating JSON.

6. **Generate, wrap, and write** the `.excalidraw.md` file per the skill's *Obsidian wrapping format* and *Element schema* sections.

7. **Update the source note** (with user confirmation): append a section like `## Diagram` with `![[<name>.excalidraw]]` so the diagram is embedded directly into the document it illustrates.

8. **Report** the diagram path, the wikilink, and the update applied to the source note.

## Notes

- This is the right command when the user says "diagram this", "draw this out", "make me an illustration of this", or "visualize what we just discussed" — the diagram lands next to the thing it explains.
- If the source document already has an embedded diagram, ask whether to replace, version (`<name>-v2`), or skip the embed.
