---
name: baseline-ui
description: >
  This skill should be used when the user says "fix the UI", "polish the interface",
  "clean up the design", "the UI looks rough", "make it look professional",
  "UI polish", "visual hierarchy is off", "spacing is inconsistent",
  "typography needs work", "colors clash", "improve readability",
  "remove AI slop", "make it look less AI-generated", "tighten up the design",
  or any request to audit and improve the visual quality of an existing interface.
version: 1.1.0
---

# Baseline UI — Visual Polish Pipeline

> Modified by MoxyWolf LLC (2026-06-25): folded in design-fluency material from [impeccable](https://github.com/pbakaus/impeccable) (Apache-2.0, (c) 2025 Paul Bakaus). The anti-pattern bans, OKLCH color strategy, typography craft, and two-altitude slop test below are adapted from impeccable; the `reference/` library is redistributed verbatim. See the plugin `NOTICE`.

Systematically raise the visual quality floor of an existing interface. Most UIs don't need redesign — they need consistent application of foundational decisions. Run this as a sequential audit.

## Audit Order (Highest Leverage First)

Fix in this exact order. Each step compounds on the previous.

### 1. Spacing Consistency

Replace arbitrary spacing with Tailwind's 4px grid. Scan every `p-`, `m-`, `gap-`, `space-` class.

**Red flags**: arbitrary values like `p-[13px]`, inconsistent padding between sibling elements, different gap values in similar grids.

**Fix**: Snap all spacing to the scale: 1 (4px), 2 (8px), 3 (12px), 4 (16px), 6 (24px), 8 (32px), 12 (48px), 16 (64px).

**Rules**:
- Cards: `p-4` (compact) or `p-6` (spacious) — pick ONE per density level
- Section gaps: `space-y-6` or `space-y-8` for form groups, `space-y-12` or `space-y-16` for page sections
- Between related items: `gap-2` or `gap-3`
- Between unrelated items: `gap-6` or `gap-8`
- Page margins: `px-4 sm:px-6 lg:px-8`

### 2. Typography Hierarchy

Every page needs exactly 4-5 distinct text levels. Scan for: same-size text everywhere, excessive bold, inconsistent font sizes.

**Standard type scale**:
```
Page title:     text-2xl font-bold text-gray-900 tracking-tight
Section head:   text-xl font-semibold text-gray-800
Subsection:     text-base font-semibold text-gray-800
Body:           text-sm text-gray-600 leading-relaxed
Caption/meta:   text-xs text-gray-500
```

**Common failures to fix**:
- Body text same weight as headings → reduce body to `font-normal`
- All text same color → use gray-900 for headings, gray-600 for body, gray-500 for meta
- Line height too tight → add `leading-relaxed` to body text
- Missing `tracking-tight` on large headings

### 3. Color Reduction

Count distinct colors used. If more than 5 (excluding semantic), reduce.

**Target palette**:
- 1 brand/primary color (blue-600 default)
- Neutral scale: gray-50 through gray-900
- Semantic only: green (success), yellow (warning), red (error)

**Fix pattern**: Replace any non-standard color with the nearest gray or brand equivalent. Remove decorative color that doesn't communicate state or hierarchy.

### 4. Border Radius Normalization

Scan for mixed radius values. Apply per element type:

| Element | Radius | Class |
|---------|--------|-------|
| Buttons | 6px | `rounded-md` |
| Inputs | 6px | `rounded-md` |
| Cards | 8px | `rounded-lg` |
| Badges/chips | full | `rounded-full` |
| Modals/sheets | 12px | `rounded-xl` |
| Avatars | full | `rounded-full` |

### 5. Shadow Hierarchy

Shadows communicate elevation. Audit for: shadows on flat content, inconsistent shadow depth, missing shadows on floating elements.

**Rules**:
- Flat inline elements: no shadow, use `border border-gray-200` instead
- Cards: `shadow-sm` or `border border-gray-200` (not both)
- Dropdowns/popovers: `shadow-md`
- Modals: `shadow-xl`
- Hover lift effect: `hover:shadow-md transition-shadow`

### 6. Interactive State Completeness

Every clickable element needs all four states. Audit buttons, links, inputs, and cards.

**Required states**:
```tsx
// Button states
className="
  bg-blue-600 text-white                    // default
  hover:bg-blue-700                          // hover
  focus:outline-none focus:ring-2            // focus
  focus:ring-blue-500 focus:ring-offset-2
  disabled:opacity-50                        // disabled
  disabled:cursor-not-allowed
  transition-colors duration-150
"

// Input states
className="
  border border-gray-300                     // default
  hover:border-gray-400                      // hover
  focus:border-blue-500 focus:ring-2         // focus
  focus:ring-blue-500/20 focus:outline-none
  disabled:bg-gray-50 disabled:text-gray-400 // disabled
"
```

**Common misses**: no focus ring, no disabled state, no hover on cards that are clickable, links with no underline-on-hover.

### 7. Loading and Empty States

Scan every data-dependent view. If any view can show zero items, it needs an empty state. If data loads asynchronously, it needs a loading state.

**Loading**: Use `Skeleton` components matching the shape of real content. Never show a bare spinner for content areas.

**Empty**: Icon + headline + description + single action button. Never leave a blank white void.

### 8. Form Polish

Forms are the highest-friction UI. Audit every form for:

- Labels above inputs (not inside as placeholders only)
- Inline error messages below the field (not a list at top)
- Consistent input heights (`h-9` or `h-10`)
- Focus states on all inputs
- Submit button disabled during submission with loading text
- Proper `htmlFor` and `id` pairing on labels and inputs

## Quick Fix Table

| Symptom | Fix |
|---------|-----|
| "Looks amateur" | Spacing grid + color reduction |
| "Hard to scan" | Typography hierarchy + section whitespace |
| "Feels cramped" | Increase padding + gap values by one step |
| "Colors clash" | Reduce to brand + grays + semantic |
| "Buttons look weak" | Add `font-medium`, ensure `px-4 py-2` minimum |
| "Text hard to read" | Increase contrast (gray-600 min for body) + line height |
| "Inputs look flat" | Add `border border-gray-300` + focus ring |
| "Cards feel heavy" | Replace thick borders with `shadow-sm`, lighter background |
| "Looks AI-generated" | Vary section layouts, reduce symmetry, add intentional whitespace |

## AI Slop Detection

AI-generated UIs have telltale patterns. Fix these to make output look human-crafted:

- **Excessive symmetry**: Not every section needs a centered heading. Left-align where appropriate
- **Uniform card grids**: Vary card sizes, use featured/large cards mixed with standard
- **Generic gradient backgrounds**: Replace with solid colors or subtle texture
- **Overuse of icons**: Not every list item needs an icon. Use icons only when they add meaning
- **Cookie-cutter sections**: Vary section layouts — full-width, split, offset, asymmetric
- **Too many CTAs**: One primary per section maximum
- **Gratuitous animation**: Remove decorative motion. Keep only functional transitions

## Absolute bans (match-and-refuse)

From impeccable. If you're about to write any of these, rewrite the element with different structure:

- **Side-stripe borders.** A `border-left`/`border-right` greater than 1px used as a colored accent on cards, list items, callouts, or alerts. Rewrite with full borders, background tints, leading numbers/icons, or nothing.
- **Gradient text.** `background-clip: text` over a gradient. Use a single solid color; emphasis via weight or size.
- **Glassmorphism as default.** Decorative blur/glass cards. Rare and purposeful, or nothing.
- **The hero-metric template.** Big number, small label, supporting stats, gradient accent. SaaS cliche.
- **Identical card grids.** Same-sized icon + heading + text cards repeated endlessly.
- **An eyebrow above every section.** Tiny uppercase tracked kicker ("ABOUT" / "PROCESS") on every heading. One named kicker as a deliberate system is voice; one on every section is AI grammar.
- **Numbered section markers as scaffolding (01 / 02 / 03).** Numbers earn their place only when the section IS a real sequence.
- **Text that overflows its container.** Test heading copy at every breakpoint; reduce the clamp max or rewrite if it overflows. The viewport is part of the design.

## Color strategy (OKLCH)

Pick a strategy before picking colors. Use OKLCH throughout.

- **Restrained** — tinted neutrals + one accent under 10%. Product default.
- **Committed** — one saturated color carries 30-60% of the surface. Identity-driven pages.
- **Full palette** — 3-4 named roles, each used deliberately. Campaigns; data viz.
- **Drenched** — the surface IS the color. Heroes, campaign pages.

**Verify contrast:** body text >= 4.5:1, large text (>= 18px or bold >= 14px) >= 3:1, placeholders the same 4.5:1. The most common AI failure is muted gray body text on a tinted near-white; bump the body color toward the ink end of the ramp.

**The cream / sand / beige body bg is the saturated AI default.** The warm-neutral band (OKLCH L 0.84-0.97, C < 0.06, hue 40-100) reads as cream/paper/parchment no matter what you name it; token names like `--paper`, `--sand`, `--linen`, `--ivory` are tells. Carry "warmth" in accent + type + imagery, not in a warm-tinted near-white body. Tint neutrals only 0.005-0.015 toward the brand's own hue.

## Typography craft

- Cap body line length at 65-75ch.
- Don't pair fonts that are similar-but-not-identical (two geometric sans). Pair on a contrast axis (serif + sans, geometric + humanist) or use one family in multiple weights.
- Display heading ceiling: `clamp()` max <= 6rem (~96px). Above that the page is shouting.
- Display letter-spacing floor: >= -0.04em. Tighter and letters touch.
- `text-wrap: balance` on h1-h3; `text-wrap: pretty` on long prose.

## The AI-slop test (two altitudes)

The slop-detection list above catches surface patterns. Also run the category-reflex check at two altitudes:

- **First-order:** if someone could guess the theme + palette from the category alone, it's the first training-data reflex. Rework the scene and color strategy until the answer isn't obvious from the domain.
- **Second-order:** if someone could guess the aesthetic family from category-plus-anti-reference ("AI tool that's not SaaS-cream -> editorial-typographic"; "fintech that's not navy-and-gold -> terminal dark"), it's the trap one tier deeper. Rework until neither answer is obvious.

If someone could look at the interface and say "AI made that" without doubt, it failed.

## Design-craft reference library

Deeper craft references (redistributed from impeccable, Apache-2.0) live in `reference/`. Read the matching one when a pass needs depth beyond the checklists above:

- `reference/craft.md` — build a feature end-to-end with taste
- `reference/layout.md` — layout, grid, spacing rhythm
- `reference/typeset.md` — typography systems
- `reference/colorize.md` — strategic color, OKLCH palettes
- `reference/interaction-design.md` — interaction and motion
- `reference/audit.md` — a11y / performance / responsive checks
- `reference/harden.md` — production: errors, i18n, edge cases
- `reference/distill.md` — strip to essence
- `reference/bolder.md` / `reference/quieter.md` — dial a design up or down

## Restraint layer (ponytail)

Restraint pairs with taste here: cut over-built markup while raising visual quality. See the `ponytail` skill — the YAGNI ladder (does it need to exist; stdlib before custom; native before dependency; one line before fifty), never cutting validation, error handling, security, or accessibility.
