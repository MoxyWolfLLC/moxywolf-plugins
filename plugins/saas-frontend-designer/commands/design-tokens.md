---
description: Generate or update design tokens and Tailwind config
allowed-tools: Read, Write, Edit, Glob, Grep
argument-hint: [brand-color-or-config-path]
---

Generate or update the design token system for this project. Brand input: $ARGUMENTS

Follow the design-system skill for the full token architecture.

**If setting up a new project:**

1. Create `globals.css` with three-layer tokens:
   - Primitive tokens (raw color/space/radius values)
   - Semantic tokens (purpose-named: bg-primary, text-secondary, etc.)
   - Dark mode overrides

2. Create/update `tailwind.config.ts`:
   - Wire CSS variables into Tailwind's theme.extend
   - Set up font families with next/font variables
   - Configure dark mode (class strategy)
   - Define type scale with line heights and weights

3. Create `lib/utils.ts` with the `cn()` utility:
   ```tsx
   import { type ClassValue, clsx } from "clsx"
   import { twMerge } from "tailwind-merge"
   export function cn(...inputs: ClassValue[]) {
     return twMerge(clsx(inputs))
   }
   ```

4. Create core component files with CVA variants:
   - Button (default, secondary, ghost, destructive, outline × sm, md, lg, icon)
   - Badge (default, success, warning, error, outline)

5. Set up theme toggle component with next-themes

**If updating an existing project:**

1. Read existing tokens and Tailwind config
2. Identify gaps or inconsistencies
3. Merge new values without breaking existing usage
4. Update component variants if tokens changed

**If a brand color is provided:**
Generate the full color scale (50-900) from the provided hex value and wire it as the brand color throughout all token layers.
