---
name: design-system
description: >
  This skill should be used when the user says "build a design system",
  "create a component library", "set up design tokens", "create a theming system",
  "establish visual consistency", "create a style guide", "Tailwind config setup",
  "dark mode support", "brand colors setup", "component variants",
  "create reusable components", "design token architecture",
  or any request to create systematic, reusable design infrastructure for a SaaS product.
version: 1.0.0
---

# Design System — Token Architecture & Component Library

Build a design system that enforces visual consistency without requiring team members to memorize arbitrary values. A design system is a shared language — it lets people make independent decisions without diverging.

## Token Architecture (Three Layers)

### Layer 1: Primitive Tokens

Raw values with no semantic meaning. These never appear directly in component code.

```css
/* globals.css — primitive tokens */
:root {
  /* Color primitives */
  --color-blue-50: #eff6ff;
  --color-blue-100: #dbeafe;
  --color-blue-500: #3b82f6;
  --color-blue-600: #2563eb;
  --color-blue-700: #1d4ed8;

  --color-gray-50: #f9fafb;
  --color-gray-100: #f3f4f6;
  --color-gray-200: #e5e7eb;
  --color-gray-300: #d1d5db;
  --color-gray-400: #9ca3af;
  --color-gray-500: #6b7280;
  --color-gray-600: #4b5563;
  --color-gray-700: #374151;
  --color-gray-800: #1f2937;
  --color-gray-900: #111827;

  --color-green-50: #f0fdf4;
  --color-green-600: #16a34a;
  --color-yellow-50: #fefce8;
  --color-yellow-600: #ca8a04;
  --color-red-50: #fef2f2;
  --color-red-600: #dc2626;

  /* Space scale (4px base) */
  --space-0: 0px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
  --radius-full: 9999px;
}
```

### Layer 2: Semantic Tokens

Purpose-named values that reference primitives. Components use these.

```css
:root {
  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: var(--color-gray-50);
  --bg-tertiary: var(--color-gray-100);
  --bg-inverse: var(--color-gray-900);

  /* Text */
  --text-primary: var(--color-gray-900);
  --text-secondary: var(--color-gray-600);
  --text-tertiary: var(--color-gray-500);
  --text-disabled: var(--color-gray-400);
  --text-inverse: #ffffff;

  /* Brand / Action */
  --color-brand: var(--color-blue-600);
  --color-brand-hover: var(--color-blue-700);
  --color-brand-light: var(--color-blue-50);
  --color-brand-text: #ffffff;

  /* Borders */
  --border-default: var(--color-gray-200);
  --border-hover: var(--color-gray-300);
  --border-focus: var(--color-blue-500);

  /* Semantic status */
  --color-success: var(--color-green-600);
  --color-success-light: var(--color-green-50);
  --color-warning: var(--color-yellow-600);
  --color-warning-light: var(--color-yellow-50);
  --color-error: var(--color-red-600);
  --color-error-light: var(--color-red-50);

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
}
```

### Layer 3: Dark Mode

Override semantic tokens with dark values using the `.dark` class.

```css
.dark {
  --bg-primary: var(--color-gray-900);
  --bg-secondary: var(--color-gray-800);
  --bg-tertiary: var(--color-gray-700);
  --bg-inverse: #ffffff;

  --text-primary: var(--color-gray-50);
  --text-secondary: var(--color-gray-400);
  --text-tertiary: var(--color-gray-500);
  --text-disabled: var(--color-gray-600);
  --text-inverse: var(--color-gray-900);

  --border-default: var(--color-gray-700);
  --border-hover: var(--color-gray-600);

  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4);
}
```

## Tailwind Config

Wire tokens into Tailwind so utilities reference your design system:

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "var(--color-brand)",
          hover: "var(--color-brand-hover)",
          light: "var(--color-brand-light)",
        },
        surface: {
          primary: "var(--bg-primary)",
          secondary: "var(--bg-secondary)",
          tertiary: "var(--bg-tertiary)",
        },
        foreground: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          tertiary: "var(--text-tertiary)",
        },
        success: { DEFAULT: "var(--color-success)", light: "var(--color-success-light)" },
        warning: { DEFAULT: "var(--color-warning)", light: "var(--color-warning-light)" },
        error: { DEFAULT: "var(--color-error)", light: "var(--color-error-light)" },
      },
      borderColor: {
        DEFAULT: "var(--border-default)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      fontSize: {
        display: ["3rem", { lineHeight: "1.1", fontWeight: "700" }],
        "2xl": ["1.5rem", { lineHeight: "1.25", fontWeight: "700" }],
        xl: ["1.25rem", { lineHeight: "1.4", fontWeight: "600" }],
        lg: ["1.125rem", { lineHeight: "1.5", fontWeight: "600" }],
        base: ["1rem", { lineHeight: "1.6", fontWeight: "400" }],
        sm: ["0.875rem", { lineHeight: "1.5", fontWeight: "400" }],
        xs: ["0.75rem", { lineHeight: "1.4", fontWeight: "400" }],
      },
      borderRadius: {
        DEFAULT: "var(--radius-md)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
      },
    },
  },
}

export default config
```

## Component Variant Pattern (CVA)

Use `class-variance-authority` for type-safe, variant-driven components.

```tsx
// components/ui/button.tsx
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { forwardRef } from "react"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        default: "bg-brand text-white hover:bg-brand-hover focus-visible:ring-brand",
        secondary: "bg-surface-tertiary text-foreground-primary hover:bg-gray-200",
        ghost: "hover:bg-surface-secondary text-foreground-secondary",
        destructive: "bg-error text-white hover:bg-red-700",
        outline: "border bg-surface-primary hover:bg-surface-secondary text-foreground-primary",
      },
      size: {
        sm: "h-8 px-3 text-xs gap-1.5",
        md: "h-9 px-4 gap-2",
        lg: "h-10 px-6 gap-2",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
)

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  )
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

## Icon System

Standardize icon sizes across the product:

```tsx
export const ICON_SIZES = {
  xs: "h-3 w-3",     // Inline text, badges
  sm: "h-4 w-4",     // Buttons, table actions
  md: "h-5 w-5",     // Navigation, feature icons
  lg: "h-6 w-6",     // Empty states, section headers
  xl: "h-8 w-8",     // Hero callouts
} as const

type IconSize = keyof typeof ICON_SIZES
```

Always pair icon-only interactive elements with `aria-label`.

## Theme Toggle

```tsx
"use client"
import { useTheme } from "next-themes"
import { Sun, Moon } from "lucide-react"
import { Button } from "@/components/ui/button"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      <Sun className="h-4 w-4 dark:hidden" />
      <Moon className="h-4 w-4 hidden dark:block" />
    </Button>
  )
}
```

## Design System Scaffolding Checklist

When setting up a new project:

- [ ] Primitive tokens defined in `globals.css`
- [ ] Semantic tokens referencing primitives
- [ ] Dark mode overrides (if applicable)
- [ ] `tailwind.config.ts` extended with token references
- [ ] `cn()` utility for conditional class merging
- [ ] Button component with CVA variants
- [ ] Input component with consistent styling
- [ ] Card component with Header/Content/Footer slots
- [ ] Badge component with semantic color variants
- [ ] Icon size constants exported
- [ ] `next/font` configured for body and mono fonts
- [ ] `next-themes` configured for dark mode toggle

## Additional Resources

Consult `references/component-catalog.md` for the full component catalog with usage examples and variant specifications.
