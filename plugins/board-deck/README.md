# Board Deck Plugin

Generate the MoxyWolf monthly 10-slide board deck from LivePlan, GA4, and Taskade data.

## What It Does

This plugin automates the monthly board reporting workflow:

1. Collects financial data (LivePlan), analytics (GA4), and sprint data (Taskade)
2. Assembles everything into a structured JSON data file
3. Generates a branded 10-slide PPTX deck using PptxGenJS
4. QA verifies the output with visual inspection

## Slides

| # | Slide | Content |
|---|-------|---------|
| 1 | Title | Month, year, tagline |
| 2 | Executive Summary | Headline, learning, obstacle, priority |
| 3 | Portfolio Dashboard | 4-product table + KPI cards |
| 4 | Capital & Burn | Cash position, burn rate, P&L, balance sheet |
| 5 | STIGViewer OKRs | Marketing, dev, ops metrics + channel breakdown |
| 6 | PRFAQ OKRs | Traffic, engagement, product context, key actions |
| 7 | SAMS & RegGenome OKRs | Dev/ops status for both products |
| 8 | Sprint Detail | Velocity bar, KPIs, task lists |
| 9 | Risk Register | Priority-coded risk table |
| 10 | Strategic Decisions | Decision cards with context and recommendations |

## Usage

Use the `/board-deck` command:

```
/board-deck February 2026
```

Or ask Claude to "build the board deck" or "generate the monthly board report."

## Components

- **Skill: board-deck-builder** — Domain knowledge for the deck structure, data sources, brand palette, and PPTX design rules
- **Command: /board-deck** — Orchestrates the full data collection, assembly, generation, and QA workflow

## Requirements

- Node.js (for PptxGenJS)
- Access to LivePlan, GA4, and Taskade for data collection
- LibreOffice (optional, for QA image extraction)
