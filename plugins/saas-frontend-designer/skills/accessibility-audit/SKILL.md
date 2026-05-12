---
name: accessibility-audit
description: >
  This skill should be used when the user says "fix accessibility", "a11y audit",
  "make this accessible", "keyboard navigation broken", "screen reader support",
  "WCAG compliance", "fix focus states", "add aria labels", "semantic HTML",
  "color contrast issues", "accessibility review", "fix tab order",
  or any request to audit or improve the accessibility of a web interface.
version: 1.0.0
---

# Accessibility Audit — WCAG AA Compliance

Audit and fix web interfaces for WCAG 2.1 AA compliance. Run this as a systematic checklist after generating or polishing UI code.

## Audit Checklist (Priority Order)

### 1. Semantic HTML

Replace non-semantic elements with their correct counterparts.

**Critical fixes**:
```tsx
// ❌ Div as button
<div onClick={handleClick} className="cursor-pointer">Click me</div>

// ✅ Native button
<button onClick={handleClick}>Click me</button>

// ❌ Div as link
<div onClick={() => router.push('/about')}>About</div>

// ✅ Native anchor
<Link href="/about">About</Link>

// ❌ Div as list
<div>{items.map(i => <div key={i.id}>{i.name}</div>)}</div>

// ✅ Semantic list
<ul>{items.map(i => <li key={i.id}>{i.name}</li>)}</ul>
```

**Element selection rules**:
- Actions (do something) → `<button>`
- Navigation (go somewhere) → `<a>` / `<Link>`
- Main content → `<main>` (one per page)
- Navigation → `<nav>` with `aria-label` when multiple
- Sections → `<section>` with heading
- Side content → `<aside>`
- Page header → `<header>`
- Page footer → `<footer>`

### 2. Heading Hierarchy

Headings must follow logical order: h1 → h2 → h3. Never skip levels for styling.

**Rules**:
- One `<h1>` per page (the page title)
- Don't skip levels: h1 → h3 is invalid (must be h1 → h2 → h3)
- Use CSS for styling, not heading levels
- Every `<section>` should begin with a heading

```tsx
// ❌ Wrong: skipping levels for style
<h1>Dashboard</h1>
<h3>Recent Activity</h3>   {/* Skipped h2 */}

// ✅ Correct: logical hierarchy, styled with CSS
<h1 className="text-2xl font-bold">Dashboard</h1>
<h2 className="text-lg font-semibold">Recent Activity</h2>
```

### 3. Keyboard Navigation

Every interactive element must be operable via keyboard.

**Requirements**:
- Tab to reach all interactive elements in logical order
- Enter/Space to activate buttons and links
- Escape to close modals, dropdowns, and popovers
- Arrow keys to navigate within composite widgets (tabs, menus, listboxes)

**Fix pattern for custom interactive elements**:
```tsx
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }}
>
  Custom button
</div>
```

Better: replace with `<button>` which handles this natively.

### 4. Focus Management

**Focus visibility**: Every focusable element must have a visible focus indicator.

```tsx
// Standard focus ring (never remove without replacement)
className="focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"

// Never do this without a replacement
className="outline-none"  // ❌ Makes element invisible to keyboard users
```

**Focus trapping**: Modals and dialogs must trap focus inside while open. When a modal opens, focus moves to the first focusable element inside. When it closes, focus returns to the trigger element. shadcn/ui `Dialog` handles this automatically.

**Skip link**: Add a skip-to-content link as the first focusable element on the page.

```tsx
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-white focus:px-4 focus:py-2 focus:rounded-md focus:shadow-md focus:text-sm focus:font-medium"
>
  Skip to main content
</a>
{/* ... navigation ... */}
<main id="main-content">
  {/* Page content */}
</main>
```

### 5. Color Contrast

All text must meet minimum contrast ratios against its background.

| Text type | Minimum ratio | Example |
|-----------|--------------|---------|
| Body text (< 18px) | 4.5:1 | gray-600 on white ✅ |
| Large text (≥ 18px bold or ≥ 24px) | 3:1 | gray-500 on white ✅ |
| UI components (borders, icons) | 3:1 | gray-400 on white ⚠️ borderline |
| Placeholder text | 4.5:1 | gray-400 on white ❌ |

**Common failures**:
- `text-gray-400` on white background → fails for body text (use `text-gray-500` or `text-gray-600`)
- Light colored text on colored backgrounds → always check
- `placeholder:text-gray-400` → acceptable because placeholders have additional context from labels

### 6. Images and Media

```tsx
// Informative image: descriptive alt text
<Image src="/chart.png" alt="Monthly revenue chart showing 23% growth" />

// Decorative image: empty alt
<Image src="/pattern.svg" alt="" aria-hidden="true" />

// Icon buttons: aria-label required
<button aria-label="Close dialog">
  <X className="h-4 w-4" aria-hidden="true" />
</button>

// Complex images: use figcaption
<figure>
  <Image src="/architecture.png" alt="System architecture diagram" />
  <figcaption className="mt-2 text-sm text-gray-500">
    Figure 1: Overview of the microservices architecture
  </figcaption>
</figure>
```

### 7. Form Accessibility

Every form input must have an associated label.

```tsx
// ✅ Explicit label association
<label htmlFor="email" className="text-sm font-medium text-gray-700">
  Email address
</label>
<input id="email" type="email" aria-describedby="email-error" />
<p id="email-error" role="alert" className="text-sm text-red-600">
  Please enter a valid email.
</p>

// ✅ Required field indication
<label htmlFor="name">
  Name <span aria-hidden="true" className="text-red-500">*</span>
  <span className="sr-only">(required)</span>
</label>
<input id="name" required aria-required="true" />
```

**Error announcement**: Use `role="alert"` or `aria-live="polite"` on error messages so screen readers announce them.

### 8. ARIA Patterns

Use ARIA only when native HTML semantics are insufficient.

**Common patterns**:
```tsx
// Live region for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

// Current page in navigation
<nav aria-label="Main navigation">
  <a href="/dashboard" aria-current="page">Dashboard</a>
  <a href="/settings">Settings</a>
</nav>

// Expandable content
<button aria-expanded={isOpen} aria-controls="panel-content">
  Show details
</button>
<div id="panel-content" hidden={!isOpen}>
  {/* Content */}
</div>

// Table with caption
<table>
  <caption className="sr-only">Monthly revenue by product</caption>
  <thead>...</thead>
  <tbody>...</tbody>
</table>
```

## Screen Reader Testing Quick Check

Verify these read correctly with a screen reader (VoiceOver on Mac: Cmd+F5):

1. Page title announced on load
2. Navigation landmarks identified ("Main navigation", "Main content")
3. Headings navigable in logical order (VO+Cmd+H)
4. All buttons and links have descriptive text
5. Form fields announce their labels
6. Error messages announced when they appear
7. Dynamic content changes announced (toasts, updates)
8. Modals announce when opened, trap focus, and return focus on close

## Additional Resources

Consult `references/wcag-checklist.md` for the complete WCAG 2.1 AA success criteria mapped to common SaaS patterns.
