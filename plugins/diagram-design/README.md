# diagram-design (pointer)

[diagram-design](https://github.com/cathrynlavery/diagram-design) (Cathryn Lavery, MIT) is an agent skill that draws diagrams as one self-contained HTML file with inline SVG, in an editorial style: one accent colour, hairline borders, no shadows, a 4px grid. Forty-five types, among them architecture, flowchart, sequence, state machine, ER, timeline, swimlane, quadrant, Gantt, Sankey, Wardley map, story map and database schema. Read at `11b08ea` (skill 2.6, 2026-10-13).

## Why this is a pointer, not a vendored build

It is markdown plus small scripts, so it could be copied in. It shouldn't be: it moved from 2.5.10 to 2.6 within days and ships its own Claude Code marketplace, so a copy under `plugins/` is stale the week it lands, the way obsidian-skills had to be re-synced. This entry documents and points; it installs nothing.

## Install it upstream (two lines)

```
/plugin marketplace add cathrynlavery/diagram-design
/plugin install diagram-design@diagram-design
```

PNG export needs Playwright (`pip install playwright && playwright install chromium`). HTML and SVG need nothing. The only network request a finished diagram makes is Google Fonts.

## Brand profiles

The skill refuses to ship default-skinned diagrams into a branded project. Onboard it once per brand, in plain language: `onboard diagram-design to https://thefrontierfounder.com`. It fetches the homepage, maps the palette and font stack to paper, ink, muted, accent and link, shows the diff, and saves the result as a named profile under `~/.diagram-design/profiles/<slug>.md`. A project selects one with a `.diagram-design` marker containing `profile: <slug>`.

Two profiles to make, on the Mac, with its own onboarding rather than by hand: `moxywolf` from moxywolf.com and `frontier-founder` from thefrontierfounder.com. The brand rules still apply on top: no black or near-black blocks, light tints for ground, no em dashes in labels.

## When to reach for it vs. what MoxyWolf already has

- **diagram-design**: a diagram that gets published. A blog or social hero, a figure in a paper or deck, an architecture picture for a README that people will look at rather than edit.
- **4d-blog-engine `hero-scene-composer`**: the Excalidraw story scene, `hero_style: excalidraw-story`, composed from a post's own artifacts. Keep it where a target names it; diagram-design is the route when the hero is a real diagram of the post's argument.
- **excalidraw-vault**: diagrams that live in Obsidian and get edited by hand.
- **Mermaid**: diagrams that live in git and change often. Mermaid is text and diffs cleanly; its own README says to keep using it for that.
- Its importers (`/diagram-design:import-mermaid`, `import-drawio`, `import-excalidraw`) redraw any of the above in the editorial style when one needs to be published.

## Attribution

diagram-design is MIT, Copyright Cathryn Lavery. No diagram-design code is in this repository. Fit note: `Taskade/Team Plugins/06 – Engineering/diagram-and-advisor-fit-2026-10-13.md`.
