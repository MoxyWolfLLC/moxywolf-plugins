---
description: Headless browser for verification and dogfooding via Rube
allowed-tools: Read, Grep, Bash, Write, Agent
argument-hint: [url]
---

Headless browser for page verification, deploy checking, and dogfooding. Uses Rube's remote Playwright. Lighter weight than `/gstack-qa` — point it at a URL and get a quick health check.

Read the gstack-execution skill for context, especially the "Browser Operations via Rube" section.

## Target

$ARGUMENTS — a URL to check.

## Quick Verification Workflow

Use `RUBE_REMOTE_WORKBENCH` to run a Playwright verification:

```python
from playwright.sync_api import sync_playwright
import json

results = {"url": "{url}", "checks": []}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})

    # Capture console errors
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # Capture network failures
    failed_requests = []
    page.on("requestfailed", lambda req: failed_requests.append({"url": req.url, "error": req.failure}))

    # Navigate
    response = page.goto("{url}", wait_until="networkidle", timeout=30000)

    # Screenshot
    page.screenshot(path="/tmp/browse-full.png", full_page=True)

    # Collect results
    results["status_code"] = response.status
    results["console_errors"] = console_errors
    results["failed_requests"] = failed_requests
    results["title"] = page.title()

    # Check key elements
    results["has_h1"] = page.locator("h1").count() > 0
    results["has_nav"] = page.locator("nav").count() > 0
    results["has_footer"] = page.locator("footer").count() > 0
    results["links_count"] = page.locator("a").count()
    results["images_count"] = page.locator("img").count()
    results["forms_count"] = page.locator("form").count()

    browser.close()

print(json.dumps(results, indent=2))
```

Read the returned screenshot to visually verify the page.

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
2. Extract all internal links
3. Visit each (up to 20 pages)
4. Report health for each page
5. Produce a site-wide summary

## Responsive Check

If asked to check responsive behavior:
1. Screenshot at 375px (mobile)
2. Screenshot at 768px (tablet)
3. Screenshot at 1280px (desktop)
4. Read all three screenshots and report layout issues at each breakpoint
