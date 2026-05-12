---
name: playwright-testing
description: >
  This skill should be used when the user asks to "write E2E tests",
  "set up Playwright", "write browser tests", "test user flows",
  "automate browser testing", "fix flaky tests", "debug E2E failures",
  "add end-to-end testing", or needs guidance on Playwright locators,
  fixtures, page objects, accessibility testing, visual regression,
  mobile testing, or CI/CD test infrastructure.
version: 0.1.0
---

# Playwright Best Practices

End-to-end testing patterns for web applications using Playwright. Covers test writing, debugging, CI/CD integration, and specialized testing scenarios.

## Core Principles

### Use User-Facing Locators

Always prefer locators that reflect how users interact with the page, not implementation details:

```typescript
// BEST: Role-based (most resilient)
page.getByRole('button', { name: 'Submit' })
page.getByRole('heading', { name: 'Welcome' })
page.getByRole('textbox', { name: 'Email' })

// GOOD: Label/placeholder-based
page.getByLabel('Email address')
page.getByPlaceholder('Enter your email')
page.getByText('Sign in')

// AVOID: Implementation-coupled
page.locator('#submit-btn')
page.locator('.btn-primary')
page.locator('[data-testid="submit"]')  // Use only as last resort
```

### Locator Priority Order

1. `getByRole()` — accessible role + name
2. `getByLabel()` — form field labels
3. `getByPlaceholder()` — input placeholders
4. `getByText()` — visible text content
5. `getByAltText()` — image alt text
6. `getByTitle()` — title attribute
7. `getByTestId()` — last resort for complex elements

### Web-First Assertions

Playwright auto-waits for assertions. Never use manual waits.

```typescript
// BAD: Manual wait
await page.waitForTimeout(2000);
expect(await page.textContent('.status')).toBe('Done');

// GOOD: Auto-waiting assertion
await expect(page.getByText('Done')).toBeVisible();

// GOOD: Wait for specific state
await expect(page.getByRole('button', { name: 'Save' })).toBeEnabled();
await expect(page.getByRole('alert')).toContainText('Saved successfully');
```

### Never Use `page.waitForTimeout()`

If you find yourself adding timeouts, the test is fragile. Use web-first assertions or wait for specific events:

```typescript
// Instead of waitForTimeout, wait for the actual condition
await page.waitForResponse(resp => resp.url().includes('/api/save') && resp.status() === 200);
await expect(page.getByText('Saved')).toBeVisible();
```

## Test Structure

### Page Object Model

Encapsulate page interactions in reusable classes:

```typescript
// models/login-page.ts
export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }

  async expectError(message: string) {
    await expect(this.page.getByRole('alert')).toContainText(message);
  }
}

// tests/login.spec.ts
test('shows error for invalid credentials', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('bad@email.com', 'wrongpassword');
  await loginPage.expectError('Invalid credentials');
});
```

### Fixtures for Reusable Setup

```typescript
// fixtures.ts
import { test as base } from '@playwright/test';
import { LoginPage } from './models/login-page';

type Fixtures = {
  loginPage: LoginPage;
  authenticatedPage: Page;
};

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(process.env.TEST_EMAIL!);
    await page.getByLabel('Password').fill(process.env.TEST_PASSWORD!);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByText('Dashboard')).toBeVisible();
    await use(page);
  },
});
```

### Test Isolation

Each test should be independent. Never depend on state from previous tests.

```typescript
// GOOD: Each test sets up its own state
test('user can create a project', async ({ authenticatedPage }) => {
  await authenticatedPage.getByRole('button', { name: 'New Project' }).click();
  await authenticatedPage.getByLabel('Project name').fill('Test Project');
  await authenticatedPage.getByRole('button', { name: 'Create' }).click();
  await expect(authenticatedPage.getByText('Test Project')).toBeVisible();
});
```

## Debugging

### Use Playwright Inspector

```bash
# Run with inspector
npx playwright test --debug

# Run specific test with UI
npx playwright test login.spec.ts --ui
```

### Trace Viewer for CI Failures

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    trace: 'on-first-retry', // Captures trace on failure
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
```

### Fixing Flaky Tests

Common causes and fixes:

| Symptom | Cause | Fix |
|---------|-------|-----|
| Passes locally, fails in CI | Timing/network speed | Use web-first assertions |
| Intermittent failures | Race condition | Wait for specific state, not timeouts |
| Different results each run | Shared test state | Isolate tests, use fresh data |
| Works in headed, fails headless | Viewport/animation differences | Set explicit viewport, disable animations |

## CI/CD Integration

### Parallel Execution

```typescript
// playwright.config.ts
export default defineConfig({
  workers: process.env.CI ? 4 : undefined,
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
});
```

### GitHub Actions Example

```yaml
- name: Run Playwright tests
  run: npx playwright test
  env:
    BASE_URL: ${{ secrets.STAGING_URL }}
- uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: playwright-report
    path: playwright-report/
```

## Specialized Testing

### Accessibility Testing

```typescript
import AxeBuilder from '@axe-core/playwright';

test('page has no accessibility violations', async ({ page }) => {
  await page.goto('/dashboard');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

### Mobile Testing

```typescript
import { devices } from '@playwright/test';

export default defineConfig({
  projects: [
    { name: 'Desktop Chrome', use: { ...devices['Desktop Chrome'] } },
    { name: 'Mobile Safari', use: { ...devices['iPhone 14'] } },
    { name: 'Tablet', use: { ...devices['iPad Pro 11'] } },
  ],
});
```

### Network Mocking

```typescript
test('handles API error gracefully', async ({ page }) => {
  await page.route('**/api/items', route =>
    route.fulfill({ status: 500, body: 'Server Error' })
  );
  await page.goto('/items');
  await expect(page.getByText('Failed to load items')).toBeVisible();
});
```

## Quick Reference Checklist

- [ ] All locators use user-facing selectors (roles, labels, text)
- [ ] No `waitForTimeout` — all waits are condition-based
- [ ] Page Object Model for reusable interactions
- [ ] Tests are independent (no shared state between tests)
- [ ] Traces/screenshots captured on failure
- [ ] CI runs tests in parallel with retries
- [ ] Accessibility checks included for key pages

For detailed patterns on each topic, see `references/`.
