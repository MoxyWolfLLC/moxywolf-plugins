---
description: Browser QA testing with bug fixing via Rube
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: [url-or-route]
---

QA testing in a real browser via Rube's remote Playwright. Adapted from gstack's `/qa` methodology. Tests like a real user, documents issues with screenshots, fixes bugs with atomic commits.

Read the gstack-execution skill for context, especially the "Browser Operations via Rube" section.

## Target

$ARGUMENTS — a URL to test, or a route path if the codebase is mounted.

If no arguments, ask the user for the URL or page to test.

## Phase 1: Setup

Use `RUBE_REMOTE_WORKBENCH` to prepare the browser environment:

```python
# Install Playwright if not cached
import subprocess
subprocess.run(["pip", "install", "playwright"], check=True)
subprocess.run(["playwright", "install", "chromium"], check=True)
```

## Phase 2: Baseline Capture

Use `RUBE_REMOTE_WORKBENCH` to run Playwright scripts:

1. **Navigate** to the target URL
2. **Screenshot** the initial state (full page)
3. **Check console** for errors or warnings
4. **Check network** for failed requests (4xx, 5xx)
5. **Check accessibility** — basic automated a11y audit

Return screenshots as base64 for visual review. Read the images to assess the page state.

## Phase 3: Interactive Testing

For each page/route:

1. **Identify interactive elements** — buttons, forms, links, dropdowns
2. **Test happy paths** — fill forms correctly, click primary actions, verify expected outcomes
3. **Test error paths** — submit empty forms, enter invalid data, verify error messages
4. **Test edge cases** — long text, special characters, rapid clicks, browser back button
5. **Test responsive** — run at 3 viewports: mobile (375px), tablet (768px), desktop (1280px)

For each test:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto("{url}")
    # ... test steps
    page.screenshot(path="/tmp/test-{name}.png", full_page=True)
    browser.close()
```

## Phase 4: Issue Documentation

For each issue found:

```
## Issue: {title}

**Severity:** P0 (broken) | P1 (major UX) | P2 (minor) | P3 (cosmetic)
**Page:** {URL or route}
**Steps to reproduce:**
1. {step}
2. {step}
**Expected:** {what should happen}
**Actual:** {what happens}
**Screenshot:** {before/after if applicable}
**Console errors:** {if any}
```

## Phase 5: Fix (if workspace has codebase)

For each P0/P1 issue:
1. Locate the source code responsible (Grep + Read)
2. Apply minimal fix
3. Commit atomically (one commit per fix)
4. Re-test via Rube to verify the fix
5. Screenshot the fixed state

## Phase 6: Health Score

```
QA REPORT
═════════
Target: {URL}
Pages tested: {N}
Issues found: {N} (P0: {n}, P1: {n}, P2: {n}, P3: {n})
Issues fixed: {N}
Console errors: {N}
Failed network requests: {N}

Health Score: {weighted score}/100
  Console:      {score}/15
  Links:        {score}/10
  Functional:   {score}/20
  UX:           {score}/15
  Accessibility:{score}/15
  Performance:  {score}/10
  Visual:       {score}/10
  Content:      {score}/5

Ship readiness: {READY | NEEDS FIXES | BLOCKED}
```

Save report to workspace as `qa-report-{date}.md`.
