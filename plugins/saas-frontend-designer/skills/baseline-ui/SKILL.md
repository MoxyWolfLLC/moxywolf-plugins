---
name: baseline-ui
description: >
  This skill should be used when the user says "fix the UI", "polish the interface",
  "clean up the design", "the UI looks rough", "make it look professional",
  "UI polish", "visual hierarchy is off", "spacing is inconsistent",
  "typography needs work", "colors clash", "improve readability",
  "remove AI slop", "make it look less AI-generated", "tighten up the design",
  or any request to audit and improve the visual quality of an existing interface.
version: 1.0.0
---

# Baseline UI — Visual Polish Pipeline

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
