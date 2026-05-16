---
name: board-deck-builder
description: >
  This skill should be used when the user asks to "build a board deck",
  "generate the monthly board report", "create the board meeting slides",
  "make the MoxyWolf board deck", or needs to prepare monthly reporting
  slides for a board meeting. It covers data collection from LivePlan,
  GA4, Taskade, GitHub (all-branch commit velocity via the native GitHub
  MCP + REST), and Gmail (RegGenome activity intelligence via the native
  Gmail MCP), JSON data assembly, and PptxGenJS deck generation.
version: 0.2.0
---

# Board Deck Builder

Generate a 10-slide MoxyWolf board deck from monthly data sources. The deck
follows a fixed layout with data-driven content populated from a JSON file.

## Workflow Overview

1. **Collect data** from five sources (see `references/data-collection.md`)
2. **Assemble JSON** following the schema in `references/data-schema.md`
3. **Generate PPTX** using the build template at `scripts/build-deck-template.js`
4. **QA verify** key slides using the workflow in `references/qa-workflow.md`

## Slide Structure (10 slides)

| # | Slide | Data Sources |
|---|-------|-------------|
| 1 | Title | meta (month, year, tagline) |
| 2 | Executive Summary | executiveSummary |
| 3 | Portfolio Dashboard | portfolio, kpis |
| 4 | Capital & Burn | financials |
| 5 | STIGViewer OKRs | stigviewerOKRs, githubVelocity |
| 6 | PRFAQ OKRs | prfaqOKRs |
| 7 | SAMS & RegGenome OKRs | samsOKRs, reggenomeOKRs, githubVelocity |
| 8 | Sprint Detail | sprint, githubVelocity |
| 9 | Risk Register | risks |
| 10 | Strategic Decisions | decisions |

## Data Sources

- **LivePlan** — Cash position, monthly burn, P&L, balance sheet, revenue, MRR
- **GA4** — TOF sessions by product, channel breakdown, engagement rates, key events
- **Taskade** — Sprint tasks (done/in-progress/to-do), story points, velocity
- **GitHub** (native GitHub MCP + REST) — All-branch commit velocity for STIGViewer (`MoxyWolfLLC/stigviewer`) and SAMS (`MoxyWolfLLC/SAMS`). Uses the native MCP's `list_branches` to enumerate branches, then the GitHub REST API directly via `Bash`/`curl` for per-branch commit listings (the MCP doesn't expose `list_commits`). Dedupes by SHA. Essential for products where feature branches don't reach main until go-live.
- **Gmail** (native Gmail MCP) — RegGenome activity intelligence from email. Uses `search_threads` to find RegGenome-related threads within the reporting month, then `get_thread` to extract meeting transcripts, partnership correspondence, action items, and decisions for `reggenomeActivity` and `reggenomeOKRs`.

## Portfolio Products (4)

1. **STIGViewer** — STIG compliance viewer (primary product)
2. **PRFAQ** — Press release/FAQ validation tool for product teams
3. **SAMS** — SaaS API management system
4. **RegGenome** — Regulatory genome API

## Critical PPTX Design Rules

These rules were hard-won through debugging PptxGenJS:

- **Never reuse option objects** — PptxGenJS mutates them silently
- **Use `makeShadow()` factory** — never share a single shadow object
- **Use `{ bullet: true }`** — never unicode bullet characters
- **Never put accent lines under slide titles**
- **Never use emoji** anywhere in slides
- **Always use `fontFace: "Calibri"`** for body text, `"Arial Black"` for headings

## MoxyWolf Brand Palette

```
orange: FF6B35    dark: 1A1A2E     darkLight: 2D2D44
white: FFFFFF     offWhite: F5F5F5
gray: 6B7280     grayLight: D1D5DB  grayMid: 9CA3AF
green: 10B981    greenBg: ECFDF5
yellow: F59E0B   yellowBg: FFFBEB
red: EF4444      redBg: FEF2F2
blue: 3B82F6     blueBg: EFF6FF
```

## Running the Build

```bash
npm install pptxgenjs   # if not already installed
node scripts/build-deck-template.js <data.json> [output.pptx]
```

Default output: `MoxyWolf-Board-{Month}-{Year}.pptx` in the same directory as the data file.

## Additional Resources

- **`references/data-collection.md`** — Step-by-step guide for collecting data from each source
- **`references/data-schema.md`** — Complete JSON schema with field descriptions
- **`references/qa-workflow.md`** — How to QA verify the generated deck
- **`references/example-data.json`** — February 2026 data file as a working example
