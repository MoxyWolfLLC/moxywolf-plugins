---
description: Run the full UI polish pipeline on existing code
allowed-tools: Read, Write, Edit, Glob, Grep
argument-hint: [file-or-directory-path]
---

Run the complete UI polish pipeline on the code at: $ARGUMENTS

Execute these four phases in order. Each phase builds on the previous.

**Phase 1: Baseline UI Audit** (baseline-ui skill)
- Fix spacing to 4px grid
- Normalize typography hierarchy (4-5 distinct levels)
- Reduce color palette (1 brand + grays + semantic)
- Normalize border radius per element type
- Fix shadow hierarchy
- Complete all interactive states (default, hover, focus, disabled)
- Add missing loading and empty states
- Polish form elements
- Detect and fix AI slop patterns

**Phase 2: Accessibility Audit** (accessibility-audit skill)
- Replace non-semantic elements with correct HTML
- Fix heading hierarchy
- Ensure keyboard navigation works
- Add focus management (visible indicators, skip links)
- Check color contrast (WCAG AA)
- Add alt text and aria labels
- Verify form accessibility

**Phase 3: Performance Check** (performance-optimization skill)
- Replace raw `<img>` with `next/image`
- Verify `next/font` usage
- Identify components that should be dynamically imported
- Check for layout shift causes
- Verify animations use GPU-accelerated properties
- Add `prefers-reduced-motion` support
- Ensure Server Components are used where possible

**Phase 4: Summary Report**
Present a summary of all changes made, grouped by phase.
List any items that require manual attention or design decisions.

Apply all fixes directly to the files. Do not just report — fix.
