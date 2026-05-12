---
description: Design system consultation and UI generation
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: [design-brief-or-component-name]
---

Design system consultation: audit existing design, generate components, establish visual consistency. Adapted from gstack's `/design-consultation` methodology.

Read the gstack-execution skill for context.

## The Brief

$ARGUMENTS

If no arguments provided, ask the user what they need: new design system, component design, UI audit, or design iteration.

## Phase 1: Design Audit

If an existing codebase is mounted:
1. Detect UI framework (React, Vue, Svelte, vanilla HTML/CSS)
2. Detect CSS approach (Tailwind, CSS modules, styled-components, vanilla CSS)
3. Scan for existing design tokens (colors, spacing, typography)
4. Identify component library in use (shadcn/ui, MUI, Chakra, custom)
5. Map current visual patterns: how many different font sizes, color values, spacing values are in use?

Report the design state:
```
DESIGN AUDIT
════════════
Framework: {React + Next.js}
Styling: {Tailwind CSS}
Component lib: {shadcn/ui}
Design tokens: {found | missing | partial}

Consistency issues:
- {N} unique font sizes (recommend {M})
- {N} unique colors (recommend {M})
- {N} unique spacing values (recommend {M})
```

## Phase 2: Design System Definition

Based on the audit (or from scratch if no codebase):

1. **Color tokens** — primary, secondary, accent, semantic (success, warning, error, info), neutrals (background, surface, text levels)
2. **Typography scale** — font families, size scale (xs through 4xl), weight scale, line heights
3. **Spacing scale** — base unit, scale multipliers (4px base recommended)
4. **Border radius** — small, medium, large, full
5. **Shadow scale** — subtle, medium, elevated
6. **Breakpoints** — mobile-first responsive breakpoints

Output as Tailwind config extension or CSS custom properties, depending on the stack.

## Phase 3: Component Generation

For requested components:
1. Build with the design system tokens (no magic numbers)
2. Include all states (default, hover, focus, active, disabled, loading, error)
3. Responsive by default (mobile → tablet → desktop)
4. Accessible (proper ARIA labels, keyboard navigation, focus management)
5. Dark mode support if the design system defines it

Write components to the workspace. One file per component.

## Phase 4: Design Review

After generation, review against these dimensions (0-10 scale):
- Visual hierarchy — does the eye go where it should?
- Consistency — do patterns repeat predictably?
- Accessibility — WCAG 2.1 AA compliance
- Responsiveness — works at all breakpoints
- Performance — no unnecessary re-renders or heavy assets

Report scores and specific improvements for any dimension below 7.
