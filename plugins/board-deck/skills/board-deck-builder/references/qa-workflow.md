# QA Workflow

How to verify the generated board deck before sharing with the board.

## Quick QA (5 minutes)

Run after every build to catch obvious issues.

### Step 1: Generate the Deck

```bash
node scripts/build-deck-template.js <data.json> [output.pptx]
```

### Step 2: Convert to Images for Visual Inspection

Use LibreOffice headless to convert PPTX to PDF, then extract page images:

```bash
# Convert PPTX to PDF
libreoffice --headless --convert-to pdf output.pptx --outdir /tmp/

# Extract each page as JPEG
pdftoppm -jpeg -r 150 /tmp/output.pdf /tmp/qa-slide
```

This produces `/tmp/qa-slide-01.jpg`, `/tmp/qa-slide-02.jpg`, etc.

### Step 3: Visual Checklist

Inspect each slide image against this checklist:

| Slide | Check |
|-------|-------|
| 1 – Title | Dark background, MOXYWOLF header, correct month/year, tagline |
| 2 – Exec Summary | 4 colored cards (green/blue/red/orange), text fits in cards |
| 3 – Portfolio | 4 products in table (no DeepFeedback), KPI cards below, health badges colored |
| 4 – Capital & Burn | Left column: 4 financial cards. Right column: P&L + Balance Sheet sections |
| 5 – STIGViewer OKRs | Marketing/Dev/Ops columns, channel breakdown, highlights render green |
| 6 – PRFAQ OKRs | Big stat number, marketing items, context panel, key actions |
| 7 – SAMS & RegGenome | Two-column layout, dev/ops items, footer text |
| 8 – Sprint Detail | Velocity bar, 5 KPI cards, done/in-progress/to-do task lists |
| 9 – Risk Register | Table with P0-P3 rows, colored priority badges, no empty rows |
| 10 – Decisions | Decision cards with colored left borders, context + recommendation |

### Step 4: Content Spot-Checks

Verify these high-signal fields match your data JSON:

- [ ] Title slide month and year match `meta.month` and `meta.year`
- [ ] Cash position on Slide 4 matches `financials.leftCards[0].value`
- [ ] Sprint velocity percentage on Slide 8 matches `sprint.velocityPct`
- [ ] Number of done tasks on Slide 8 matches `sprint.doneTasks.length`
- [ ] Number of risks on Slide 9 matches `risks.length`

## Full QA (15 minutes)

Run before board distribution. Includes everything in Quick QA plus:

### Data Accuracy

Open the PPTX in PowerPoint or Google Slides and verify:

1. **Financials (Slide 4)**: Cross-reference every number against LivePlan
2. **GA4 metrics (Slides 5-7)**: Cross-reference session counts, percentages against GA4 reports
3. **Sprint data (Slide 8)**: Cross-reference task counts and velocity against Taskade
4. **Risk register (Slide 9)**: Confirm all active risks are listed, no stale risks remain

### Text Overflow

Check that no text is clipped or overflowing its container:

- Executive Summary cards (Slide 2) — each card text fits
- Portfolio table cells (Slide 3) — dev status text fits
- Sprint task lists (Slide 8) — all tasks visible
- Risk descriptions (Slide 9) — no truncation

### Brand Compliance

- [ ] No emoji anywhere in the deck
- [ ] No unicode bullet characters (should use PptxGenJS `bullet: true`)
- [ ] No accent lines under slide titles
- [ ] Body text uses Calibri
- [ ] Headings use Arial Black
- [ ] MoxyWolf orange (`#FF6B35`) used for accent elements

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Shadow renders as black box | Shared shadow object mutated | Ensure `makeShadow()` factory is used |
| Bullets show as squares | Unicode characters used | Use `{ bullet: true }` instead |
| Text overlaps | Content too long for card | Shorten text in data JSON |
| Wrong colors | Color key typo | Check against palette in SKILL.md |
| Missing slide content | Null/undefined in JSON | Add `"Needs input"` placeholder |
