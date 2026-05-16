---
description: Browser-based page verification and dogfooding via Claude in Chrome
allowed-tools: Read, Grep, Bash, Write, Agent
argument-hint: [url]
---

Browser-based page verification, deploy checking, and dogfooding. Uses Claude in Chrome (the user's real browser) so any authenticated session, cookies, and extensions are present. Lighter weight than `/gstack-qa` — point it at a URL and get a quick health check.

Read the gstack-execution skill for context, especially the "Browser Operations via Claude in Chrome" section.

## Target

$ARGUMENTS — a URL to check.

## Prerequisites

- The **Claude in Chrome** extension is installed, signed in, and at least one Chrome window is open.
- If the extension isn't connected, halt and ask the user to install it. Don't fall back to a headless tool — `/gstack-browse` is specifically about verifying what the real user sees.

## Quick Verification Workflow

Use the Claude in Chrome MCP. Open a tab, navigate, and inspect:

1. `mcp__Claude_in_Chrome__tabs_create_mcp` — opens a new tab (or reuse an existing one via `tabs_context_mcp` with `createIfEmpty: true`).
2. `mcp__Claude_in_Chrome__navigate` with `url: $ARGUMENTS`. Wait ~3 seconds after navigation for the page to fully render.
3. `mcp__Claude_in_Chrome__read_console_messages` — surface any errors logged during navigation.
4. `mcp__Claude_in_Chrome__read_network_requests` — surface any failed requests (status >= 400 or `failed`).
5. `mcp__Claude_in_Chrome__get_page_text` — get the rendered text content (this is what a user would see).
6. For structural checks, run a JS evaluation in-page:

   ```js
   mcp__Claude_in_Chrome__javascript_tool with code:
       JSON.stringify({
         title: document.title,
         has_h1: document.querySelectorAll("h1").length > 0,
         has_nav: document.querySelectorAll("nav").length > 0,
         has_footer: document.querySelectorAll("footer").length > 0,
         links: document.querySelectorAll("a").length,
         images: document.querySelectorAll("img").length,
         forms: document.querySelectorAll("form").length,
         status: window.performance.getEntriesByType('navigation')[0]?.responseStatus || null,
       })
   ```

7. If a visual record is needed, use `mcp__Claude_in_Chrome__gif_creator` for a short capture, or fall back to native `mcp__computer-use__screenshot` for a single frame.

## Report

```
BROWSE CHECK: {url}
═══════════════════
Status: {status_code}
Title: {title}
Console errors: {N}
Failed requests: {N}

Page structure:
  H1: {present/missing}
  Nav: {present/missing}
  Footer: {present/missing}
  Links: {N}
  Images: {N}
  Forms: {N}

Verdict: {HEALTHY | ISSUES FOUND | DOWN}
```

If issues are found, list each with severity. If the page is healthy, say so and stop.

## Multi-Page Check

If the user provides multiple URLs or asks to "check the whole site":
1. Start from the provided URL
2. Extract all internal links from the page (via `javascript_tool`: `[...document.querySelectorAll("a[href]")].map(a => a.href).filter(h => h.startsWith(location.origin))`)
3. Visit each (up to 20 pages) via `navigate` in the same tab — no need to open 20 tabs
4. Report health for each page
5. Produce a site-wide summary

## Responsive Check

If asked to check responsive behavior:
1. `mcp__Claude_in_Chrome__resize_window` to 375×667 (mobile), capture
2. Resize to 768×1024 (tablet), capture
3. Resize to 1280×800 (desktop), capture
4. Read each capture and report layout issues at each breakpoint

Restore the window to the user's preferred size when done.
