# Story → Scene Extraction

> Single-source-of-truth recipe for turning a staged blog draft into a structured `scene-outline.json` that the hero-scene-composer skill can render. Called from `skills/release-owner-gate/SKILL.md` STEP 2, sub-step 2 (extract concrete artifacts).

The extractor's job is to produce a strict JSON object — not prose. The composer skill consumes that JSON to lay out the Excalidraw scene by filling fixed slots in `references/excalidraw-canvas-template.json`. No improvisation between extraction and rendering.

## Input

The staged blog at `<piece>/04-diligence/blog.md`. Read the YAML frontmatter, the title (H1), all H2 subheads, and the first 800 words of body.

## Output contract

Write the extracted outline to `<piece>/04-diligence/scene-outline.json`. The file MUST validate against this schema:

```json
{
  "title": "string — the post's literal H1, trimmed; <= 90 chars",
  "left_panel": {
    "label": "string — the H2 (or paraphrase) that names the problem/before; <= 36 chars",
    "icons": [
      { "name": "string — must be a key in references/excalidraw-icon-vocab.md", "label": "string — <= 18 chars" }
    ],
    "arrow_label": "string — phrase quoted or paraphrased from the post; <= 24 chars; optional, may be empty"
  },
  "right_panel": {
    "label": "string — the H2 (or paraphrase) that names the solution/after; <= 36 chars",
    "icons": [
      { "name": "string — icon vocab key", "label": "string — <= 18 chars" }
    ],
    "arrow_label": "string — phrase from the post; <= 24 chars; optional, may be empty"
  },
  "bridge_arrow_label": "string — present-continuous verb of motion connecting left -> right; <= 18 chars",
  "chart": {
    "present": "boolean",
    "kind": "string — one of: bars3 | count_of | contrast_pair | none",
    "values": ["string — <= 16 chars each, max 3 entries"],
    "caption": "string — quoted or paraphrased from the post; <= 90 chars"
  },
  "callouts": [
    { "anchor": "string — left_panel | right_panel", "text": "string — quoted phrase from the post; <= 110 chars" }
  ],
  "source_artifacts": {
    "h1": "string — verbatim H1",
    "h2s": ["string — verbatim H2 text"],
    "concrete_nouns": ["string — tangible objects named in the post"],
    "numbers": ["string — e.g. '500 emails, 0 replies', '32 plugins', 'c09f14d'"],
    "verb_of_motion": "string — one verb in present continuous"
  }
}
```

## Extraction rules (in order — apply top to bottom)

1. **Title.** Take the H1 verbatim. If longer than 90 chars, trim to the last full word ≤ 90 chars and append `…`.

2. **Concrete nouns.** Scan the title, the first 200 words, and every H2 for tangible objects. Allowed sources:
   - Common-noun objects (envelope, vault, brain, graph, code window, capture pad, key, lock, signature, chart, door, document, calendar, clock, ladder, scaffold, layer/plate, notebook).
   - Domain objects named in this post specifically (e.g. "obsidian-update", "graphify", "DR-010" → render as a labeled document icon).
   - Do **not** invent nouns the post does not name. If the post is fully abstract, fall back to: `notebook`, `graph`, `vault`, `chart`.
   - Output as `source_artifacts.concrete_nouns`.

3. **Numbers and contrasts.** Capture every distinctive number, count, contrast, or named identifier (commit SHA, DR ID, version). Examples: `"500 emails, 0 replies"`, `"32 plugins"`, `"5 of 32"`, `"polished vs. real"`, `"commit c09f14d"`, `"DR-010"`. Output as `source_artifacts.numbers`.

4. **Verb of motion.** Read the post's central action and write **one** present-continuous verb: `capturing`, `compounding`, `shipping`, `forgetting`, `connecting`, `auditing`, `signing`, `breaking`, `layering`, `routing`. Output as `source_artifacts.verb_of_motion`. This drives `bridge_arrow_label` (you may wrap it in 1–2 prep words, e.g. "compounding into", "routing through").

5. **Panel split.** Choose two H2s that frame a before/after or problem/solution contrast. Defaults if no H2 pair obviously fits:
   - Left = "The problem" / "Before" / "What goes wrong"
   - Right = "The fix" / "After" / "How it compounds"
   Paraphrase to ≤ 36 chars per panel label.

6. **Icons per panel.** Map 2–4 of the post's concrete nouns into each panel. Every icon name MUST exist as a key in `references/excalidraw-icon-vocab.md`. If a noun has no matching icon, either pick the closest vocab key or drop it. Never invent an icon name.

7. **Arrow labels.** Each panel may have one internal arrow connecting its icons; the label is a short phrase quoted or paraphrased from the post (≤ 24 chars). The `bridge_arrow_label` (left panel → right panel) uses the verb of motion (≤ 18 chars).

8. **Micro-chart.** Set `chart.present: true` ONLY if the post centers on a specific numeric story. Pick `kind`:
   - `bars3` — three labeled bars (before / middle / after). Values are short axis labels.
   - `count_of` — "X of Y" callout (values = `["X", "Y"]`).
   - `contrast_pair` — two bars labeled with the contrast pair (values = the two contrast terms).
   - `none` — no chart; set `present: false` and `values: []`.
   The `caption` quotes a phrase from the post that names the chart's meaning.

9. **Callouts.** Up to 2 callouts total across both panels. Each anchors to one panel. Text is a **verbatim or near-verbatim** phrase from the post — never invented copy. ≤ 110 chars.

10. **No invented copy.** Every piece of text in the outline must either be (a) verbatim from the post, (b) a paraphrase that preserves the post's named entities and numbers, or (c) one of the fixed structural labels above. If an output field would require invention, leave it empty or omit it.

## Validation before write

Before writing `scene-outline.json`, verify:

- `title` is non-empty.
- `left_panel.icons` has 2–4 entries; same for `right_panel`.
- Every `icons[].name` exists as a key in `references/excalidraw-icon-vocab.md`.
- All length caps are respected.
- `source_artifacts` contains the post's H1 and at least one H2.
- If `chart.present === true`, `chart.values` has the right cardinality for `chart.kind` (3 for `bars3`, 2 for `count_of` and `contrast_pair`).

If any check fails, re-extract — do not write an invalid outline.

## Example (for the Frontier Founder Toolkit launch post)

```json
{
  "title": "The Frontier Founder Toolkit — Public Scaffolding for Private Judgment",
  "left_panel": {
    "label": "Before: The Sprawl",
    "icons": [
      { "name": "notebook", "label": "loose notes" },
      { "name": "question_mark", "label": "?" },
      { "name": "robot", "label": "amnesiac agent" }
    ],
    "arrow_label": "treats notes as paper"
  },
  "right_panel": {
    "label": "After: The 5-Layer Tape",
    "icons": [
      { "name": "capture_pad", "label": "cowork session" },
      { "name": "vault", "label": "vault" },
      { "name": "notebook", "label": "obsidian-update" },
      { "name": "graph", "label": "graphify" },
      { "name": "code_window", "label": "vault-code-learn" }
    ],
    "arrow_label": "compounding judgment"
  },
  "bridge_arrow_label": "build the tape",
  "chart": {
    "present": true,
    "kind": "bars3",
    "values": ["before", "uber-brain v1", "today"],
    "caption": "Two major launches before lunch"
  },
  "callouts": [
    { "anchor": "left_panel", "text": "Claude confidently invented an answer that contradicted DR-010." },
    { "anchor": "right_panel", "text": "Apache-2.0 plus a working plugin marketplace is a manifesto with a receipt." }
  ],
  "source_artifacts": {
    "h1": "The Frontier Founder Toolkit — Public Scaffolding for Private Judgment",
    "h2s": ["The thirty-day arc", "What the uber-brain actually is", "Today, the actual ship", "The earned-secret core"],
    "concrete_nouns": ["notebook", "vault", "graph", "code window", "capture pad", "commit", "license"],
    "numbers": ["32 plugins", "5 plugins", "commit c09f14d", "commit 9280072", "DR-010", "Apache-2.0"],
    "verb_of_motion": "compounding"
  }
}
```

The composer skill reads this file and produces the Excalidraw scene by populating the slots in `references/excalidraw-canvas-template.json` with the icon JSON snippets from `references/excalidraw-icon-vocab.md`.
