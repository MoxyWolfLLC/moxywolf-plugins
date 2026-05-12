# WCAG 2.1 AA Compliance Checklist

Quick-reference checklist for the accessibility-audit skill. Each item maps to a WCAG success criterion.

## 1. Perceivable

### 1.1 Text Alternatives (SC 1.1.1)

| Check | Implementation |
|-------|---------------|
| Informative images have descriptive alt text | `<Image alt="Bar chart showing Q4 revenue growth of 23%" />` |
| Decorative images are hidden from AT | `<Image alt="" aria-hidden="true" />` or CSS background |
| Icon-only buttons have accessible labels | `<Button aria-label="Close dialog"><X /></Button>` |
| Complex images have extended descriptions | Use `<figure>` + `<figcaption>` or `aria-describedby` |
| SVG icons have title or aria-label | `<svg role="img" aria-label="Settings">` |

### 1.2 Color Contrast (SC 1.4.3, 1.4.11)

| Element | Minimum Ratio | Tool |
|---------|--------------|------|
| Body text (< 18px) | 4.5:1 | WebAIM Contrast Checker |
| Large text (≥ 18px or ≥ 14px bold) | 3:1 | |
| UI components and borders | 3:1 | |
| Focus indicators | 3:1 against adjacent colors | |
| Placeholder text | 4.5:1 (or don't rely on it) | |

### Common Failures

```
❌ text-gray-400 on white → 3.0:1 (fails AA)
✅ text-gray-600 on white → 5.7:1 (passes AA)

❌ text-blue-400 on white → 3.0:1 (fails)
✅ text-blue-700 on white → 4.6:1 (passes)
```

### 1.3 Content Structure (SC 1.3.1, 1.3.2)

| Check | Rule |
|-------|------|
| Heading hierarchy | One `<h1>` per page, no skipped levels (h1 → h2 → h3) |
| Lists use proper markup | `<ul>`, `<ol>`, `<dl>` — not styled divs |
| Tables have headers | `<th scope="col">` or `<th scope="row">` |
| Reading order matches visual order | DOM order = visual order (no CSS order tricks that break AT) |
| Landmarks present | `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>` |

## 2. Operable

### 2.1 Keyboard Accessible (SC 2.1.1, 2.1.2)

| Check | Implementation |
|-------|---------------|
| All interactive elements keyboard-reachable | Tab through entire page — nothing skipped |
| No keyboard traps | Esc closes modals/dialogs, focus returns to trigger |
| Custom controls have keyboard support | Dropdowns: arrow keys, Enter, Esc. Tabs: arrow keys. |
| Skip-to-content link present | First focusable element: `<a href="#main" className="sr-only focus:not-sr-only">Skip to content</a>` |

### Focus Management Patterns

**Modal Dialog:**
```tsx
// Focus trap: focus stays inside dialog when open
// On open: move focus to first focusable element or dialog itself
// On close: return focus to the element that triggered the dialog
<Dialog onOpenChange={(open) => {
  if (!open) triggerRef.current?.focus()
}}>
```

**Tab Panel:**
```tsx
// Arrow keys move between tabs
// Tab key moves into panel content
// Home/End move to first/last tab
<Tabs> {/* shadcn/ui handles this automatically */}
```

**Dropdown Menu:**
```tsx
// Enter/Space opens menu
// Arrow keys navigate items
// Esc closes menu, returns focus to trigger
<DropdownMenu> {/* shadcn/ui handles this automatically */}
```

### 2.2 Focus Indicators (SC 2.4.7)

```css
/* Minimum: 2px solid outline with offset */
:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

/* Never remove focus outlines globally */
/* ❌ *:focus { outline: none } */
```

### 2.3 Target Size (SC 2.5.8 — AAA, but recommended)

| Element | Minimum Size |
|---------|-------------|
| Buttons | 44×44px touch target (use min-h-11 min-w-11) |
| Links in body text | OK smaller if spaced adequately |
| Icon buttons | 44×44px (padding around 16px icon) |
| Mobile tap targets | 48×48px recommended |

## 3. Understandable

### 3.1 Forms (SC 3.3.1, 3.3.2, 3.3.3)

| Check | Implementation |
|-------|---------------|
| Every input has a visible label | `<Label htmlFor="email">Email</Label>` — not just placeholder |
| Required fields indicated | `<Label>Email <span aria-hidden="true">*</span></Label>` + `aria-required="true"` |
| Error messages linked to inputs | `aria-describedby="email-error"` on input, `id="email-error"` on message |
| Errors announced to screen readers | `aria-live="polite"` on error container or `role="alert"` |
| Instructions provided before form | Help text via `<FormDescription>` |
| Error prevention for destructive actions | Confirmation dialog before delete/submit |

### Form Error Pattern

```tsx
<FormItem>
  <FormLabel>Email</FormLabel>
  <FormControl>
    <Input
      aria-invalid={!!errors.email}
      aria-describedby={errors.email ? "email-error" : undefined}
      {...field}
    />
  </FormControl>
  {errors.email && (
    <FormMessage id="email-error" role="alert">
      {errors.email.message}
    </FormMessage>
  )}
</FormItem>
```

### 3.2 Page Language (SC 3.1.1)

```tsx
// app/layout.tsx
<html lang="en">
```

## 4. Robust

### 4.1 ARIA Usage Rules

1. **Don't use ARIA if native HTML works**
   - ❌ `<div role="button" tabIndex={0} onClick={...}>`
   - ✅ `<button onClick={...}>`

2. **Required ARIA for custom widgets**
   - Disclosure: `aria-expanded="true|false"`
   - Tabs: `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`
   - Dialog: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
   - Live regions: `aria-live="polite"` for non-urgent, `aria-live="assertive"` for urgent

3. **State management**
   - Loading: `aria-busy="true"` on container
   - Disabled: `aria-disabled="true"` (prefer native `disabled` attribute)
   - Current page: `aria-current="page"` on active nav link
   - Expanded: `aria-expanded` on disclosure triggers

### shadcn/ui Built-in A11y

These shadcn/ui components handle ARIA automatically via Radix primitives:

| Component | Built-in A11y |
|-----------|--------------|
| Dialog | Focus trap, Esc close, aria-modal, aria-labelledby |
| DropdownMenu | Keyboard nav, aria-expanded, roving tabindex |
| Tabs | Arrow key nav, aria-selected, tabpanel association |
| Tooltip | aria-describedby, Esc dismiss, hover+focus trigger |
| AlertDialog | Focus trap, required action, aria-labelledby |
| Select | Keyboard nav, listbox role, aria-expanded |
| Sheet | Focus trap, Esc close, slide animation |

Still verify: labels, descriptions, and custom trigger content.

## Screen Reader Testing Quick Check

Test these flows with VoiceOver (macOS) or NVDA (Windows):

1. **Page load** — Is the page title announced? Can you hear landmarks?
2. **Navigation** — Tab through nav. Is current page indicated?
3. **Forms** — Are labels announced with each field? Are errors described?
4. **Modals** — Does focus move into modal? Is it trapped? Does Esc work?
5. **Dynamic content** — Are toasts/alerts announced? Loading states?
6. **Data tables** — Are column headers associated with cells?

## Automated Testing Setup

```tsx
// vitest.config.ts — add axe-core for component tests
import { axe, toHaveNoViolations } from "jest-axe"
expect.extend(toHaveNoViolations)

// In test:
it("has no a11y violations", async () => {
  const { container } = render(<MyComponent />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

```bash
# Lighthouse CI for automated audits
npx lighthouse http://localhost:3000 --only-categories=accessibility --output=json
```
