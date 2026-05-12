---
description: Run an accessibility audit on UI code
allowed-tools: Read, Write, Edit, Glob, Grep
argument-hint: [file-or-directory-path]
---

Run a comprehensive accessibility audit on the code at: $ARGUMENTS

Follow the accessibility-audit skill checklist in full.

**Audit and fix in this order:**

1. **Semantic HTML** — Replace divs-as-buttons, divs-as-links, missing landmarks
2. **Heading hierarchy** — Ensure logical h1→h2→h3 order, one h1 per page
3. **Keyboard navigation** — All interactive elements reachable and operable via keyboard
4. **Focus management** — Visible focus indicators, skip-to-content link, focus trapping in modals
5. **Color contrast** — WCAG AA ratios (4.5:1 body, 3:1 large text, 3:1 UI components)
6. **Images and media** — Alt text, aria-hidden on decorative elements, figcaptions
7. **Form accessibility** — Label associations, error announcements, required field indicators
8. **ARIA patterns** — Live regions, current page indicators, expanded state management

**For each issue found:**
- State the issue and its WCAG success criterion
- Show the current code
- Apply the fix directly
- Explain why the fix matters

**Output a summary table:**
| Issue | Severity | File | Status |
|-------|----------|------|--------|
| ... | Critical/Major/Minor | path | Fixed/Needs manual review |
