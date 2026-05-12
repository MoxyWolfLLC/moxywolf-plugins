---
name: figma-to-code
description: >
  This skill should be used when the user says "convert this Figma design",
  "implement this Figma file", "build this from Figma", "Figma to code",
  "code this design", "translate the design to React", "implement the mockup",
  "build from this Figma link", "match this design exactly",
  or any request to generate front-end code from a Figma design file or screenshot.
  Requires the Figma MCP integration to be connected.
version: 1.0.0
---

# Figma to Code — Design-to-Implementation Pipeline

Convert Figma designs into production-ready Next.js + React + Tailwind + shadcn/ui code. This skill bridges the gap between design intent and working implementation.

## Prerequisites

This skill requires the **Figma MCP** integration. If not connected, inform the user they need to enable the Figma connector in their Claude settings.

Available Figma MCP tools:
- `get_design_context` — Primary tool. Returns reference code, screenshot, and metadata for a Figma node
- `get_screenshot` — Visual preview of a specific node
- `get_metadata` — XML structure overview of node hierarchy
- `get_variable_defs` — Design token values (colors, spacing, etc.)
- `get_code_connect_map` — Existing code-to-Figma mappings

## Workflow

### Step 1: Extract Design Context

When the user provides a Figma URL, extract the file key and node ID, then fetch design context.

```
URL format: https://figma.com/design/:fileKey/:fileName?node-id=:nodeId
Example: https://figma.com/design/abc123/MyApp?node-id=1-2
  → fileKey: abc123
  → nodeId: 1:2
```

Use `get_design_context` as the primary tool. It returns:
- A screenshot of the design for visual reference
- Reference code (Figma's code suggestion)
- Asset download URLs for any images
- Component metadata

### Step 2: Analyze Design Decisions

From the design context, extract:

1. **Layout structure**: Flex vs grid, column count, alignment, spacing
2. **Typography**: Font sizes, weights, line heights, letter spacing
3. **Colors**: Map Figma fills to the nearest Tailwind color or design token
4. **Spacing**: Convert pixel values to Tailwind's 4px grid (`16px` → `p-4`)
5. **Border radius**: Map to standard radius tokens
6. **Shadows**: Map to Tailwind shadow utilities
7. **Component patterns**: Identify which shadcn/ui components match the design

### Step 3: Map to Stack

Translate design elements to the target stack:

| Figma Element | Implementation |
|---------------|----------------|
| Auto layout (horizontal) | `flex` + `gap-{n}` |
| Auto layout (vertical) | `flex flex-col` + `gap-{n}` |
| Grid layout | `grid grid-cols-{n}` + `gap-{n}` |
| Frame with padding | Container div + `p-{n}` |
| Text styles | Tailwind text utilities |
| Fill colors | Tailwind color classes or CSS variables |
| Stroke / border | `border` + `border-{color}` |
| Drop shadow | `shadow-{sm/md/lg}` |
| Corner radius | `rounded-{sm/md/lg/xl/full}` |
| Component instances | shadcn/ui components or custom components |
| Icon instances | lucide-react equivalents |
| Image fills | `next/image` with proper sizing |

### Step 4: Extract Design Tokens

If the Figma file uses variables/tokens, fetch them with `get_variable_defs`:

```
Figma variable → CSS variable → Tailwind config
--color-primary → --color-brand → brand color in tailwind.config.ts
--spacing-md → maps to Tailwind space scale
```

Use these to populate the design-system skill's token architecture.

### Step 5: Generate Code

Apply these rules when generating implementation code:

**Pixel-perfect is not the goal.** The goal is to capture design intent using the target stack's idioms. A Figma frame with 13px padding becomes `p-3` (12px) — snapped to the grid.

**Component decomposition**: Break the design into components matching these boundaries:
- Each distinct interactive region → separate client component
- Each repeated pattern → reusable component with props
- Static layout → server component
- Page-level structure → page.tsx with layout components

**Responsive adaptation**: Figma designs are typically one breakpoint. Generate mobile-first code and adapt up:
- If the design shows a desktop layout, infer the mobile collapse strategy
- Sidebar → hamburger menu on mobile
- Multi-column grid → single column on mobile
- Horizontal nav → stacked or drawer on mobile

### Step 6: Visual QA

After generating code, compare against the Figma screenshot:

1. **Layout fidelity**: Do major sections align correctly?
2. **Typography**: Are heading/body sizes proportionally correct?
3. **Color matching**: Are colors within the correct family?
4. **Spacing rhythm**: Does the vertical rhythm feel consistent?
5. **Interactive elements**: Are all buttons, inputs, and links properly styled?
6. **Responsive behavior**: Does the mobile layout make sense?

## Figma-to-Tailwind Quick Reference

### Spacing Conversion

| Figma pixels | Tailwind class | REM |
|-------------|----------------|-----|
| 4px | `1` | 0.25rem |
| 8px | `2` | 0.5rem |
| 12px | `3` | 0.75rem |
| 16px | `4` | 1rem |
| 20px | `5` | 1.25rem |
| 24px | `6` | 1.5rem |
| 32px | `8` | 2rem |
| 40px | `10` | 2.5rem |
| 48px | `12` | 3rem |
| 64px | `16` | 4rem |

### Font Size Conversion

| Figma size | Tailwind class |
|-----------|----------------|
| 12px | `text-xs` |
| 14px | `text-sm` |
| 16px | `text-base` |
| 18px | `text-lg` |
| 20px | `text-xl` |
| 24px | `text-2xl` |
| 30px | `text-3xl` |
| 36px | `text-4xl` |
| 48px | `text-5xl` |

### Font Weight Conversion

| Figma weight | Tailwind class |
|-------------|----------------|
| 300 / Light | `font-light` |
| 400 / Regular | `font-normal` |
| 500 / Medium | `font-medium` |
| 600 / SemiBold | `font-semibold` |
| 700 / Bold | `font-bold` |

### Border Radius Conversion

| Figma radius | Tailwind class |
|-------------|----------------|
| 2px | `rounded-sm` |
| 4px | `rounded` |
| 6px | `rounded-md` |
| 8px | `rounded-lg` |
| 12px | `rounded-xl` |
| 16px | `rounded-2xl` |
| 9999px | `rounded-full` |

## Common Figma Patterns → Code

### Auto Layout → Flexbox
Figma auto layout with gap 12, horizontal, center aligned:
```tsx
<div className="flex items-center gap-3">
```

### Frame → Container
Figma frame 1280px wide, centered, padding 24:
```tsx
<div className="mx-auto max-w-7xl px-6">
```

### Component Set → CVA Variants
Figma component with Property=Primary/Secondary/Ghost variants:
```tsx
const variants = cva("base-classes", {
  variants: {
    variant: {
      primary: "bg-brand text-white",
      secondary: "bg-surface-tertiary",
      ghost: "hover:bg-surface-secondary",
    },
  },
})
```

## Additional Resources

Consult `references/figma-patterns.md` for advanced Figma-to-code patterns including responsive variants, interactive prototyping translation, and design system sync workflows.
