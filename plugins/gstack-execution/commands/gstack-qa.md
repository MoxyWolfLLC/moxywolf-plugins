---
description: Browser QA testing with bug fixing via Claude in Chrome
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: [url-or-route]
---

QA testing in a real browser via Claude in Chrome — the user's own logged-in browser, not a headless sandbox. Adapted from gstack's `/qa` methodology. Tests like a real user, documents issues, fixes bugs with atomic commits.

Read the gstack-execution skill for context, especially the "Browser Operations via Claude in Chrome" section.

## Target

$ARGUMENTS — a URL to test, or a route path if the codebase is mounted.

If no arguments, ask the user for the URL or page to test.

## Phase 1: Setup

Confirm the Claude in Chrome extension is connected. If not, halt and ask the user to install it from the Chrome Web Store and sign in. Browser ops below assume the extension is active.

Open a fresh tab so the QA session doesn't interfere with other open work:

```
mcp__Claude_in_Chrome__tabs_create_mcp
```

## Phase 2: Baseline Capture

1. `mcp__Claude_in_Chrome__navigate` to the target URL. Wait ~3 seconds for full render.
2. `mcp__Claude_in_Chrome__read_console_messages` — capture any errors or warnings logged during navigation. Persist to `/tmp/qa-console-{timestamp}.json`.
3. `mcp__Claude_in_Chrome__read_network_requests` — capture failed requests (status >= 400 or `failed`). Persist to `/tmp/qa-network-{timestamp}.json`.
4. `mcp__Claude_in_Chrome__get_page_text` — capture rendered page text (what a user actually sees).
5. For a visual baseline, use `mcp__computer-use__screenshot` while the Chrome window is frontmost, or `mcp__Claude_in_Chrome__gif_creator` for short interaction captures.
6. Run a basic a11y sweep via `javascript_tool`:

   ```js
   JSON.stringify({
     missing_alt: [...document.querySelectorAll("img:not([alt])")].length,
     missing_labels: [...document.querySelectorAll("input,select,textarea")].filter(el => !el.labels?.length && !el.getAttribute("aria-label")).length,
     missing_lang: !document.documentElement.lang,
     contrast_skip: "use axe-core for full a11y; this is a quick proxy"
   })
   ```

## Phase 3: Interactive Testing

For each page/route:

1. **Identify interactive elements** — `get_page_text` plus `javascript_tool` to enumerate buttons, forms, links, dropdowns.
2. **Test happy paths** — use `form_input` or `javascript_tool` to fill forms correctly, click primary actions, verify expected outcomes via `get_page_text` after each action.
3. **Test error paths** — submit empty forms, enter invalid data, verify error messages appear.
4. **Test edge cases** — long text, special characters, rapid clicks, browser back button (`shortcuts_execute` can trigger Cmd+Left).
5. **Test responsive** — use `resize_window` at 3 viewports: 375×667 (mobile), 768×1024 (tablet), 1280×800 (desktop). Capture each and compare.

Persist each test artifact to `/tmp/qa-{phase}-{test-name}.{ext}` so the final report can reference them.

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
**Console errors:** {if any from Phase 2's capture}
```

## Phase 5: Fix (if workspace has codebase)

For each P0/P1 issue:
1. Locate the source code responsible (Grep + Read)
2. Apply minimal fix
3. Commit atomically (one commit per fix) — leave the actual `git commit` to the user via GitHub Desktop if your tooling can't write to `.git/`
4. Reload the page in Chrome (`shortcuts_execute` with Cmd+R, or `navigate` to the same URL again) and re-run the failing test from Phase 3
5. Capture the fixed state

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

## Headless mode (alternative)

For unattended regression runs where the real-browser fidelity isn't needed, install Playwright in the workspace bash sandbox and drive it directly:

```bash
npm i -g playwright
npx playwright install chromium
node /tmp/qa-script.js
```

The script structure is the same as the original Playwright-based gstack patterns. Use this path only when nobody's around to host the Chrome session (e.g., a CI-style scheduled run).
