---
name: test-driven-development
description: >
  This skill should be used when the user asks to "write tests first",
  "do TDD", "test-driven development", "write unit tests", "add test coverage",
  "create a test suite", "follow red-green-refactor", or needs guidance on
  testing workflows, test structure, mocking strategies, assertion patterns,
  or building confidence in code through automated testing.
version: 0.1.0
---

# Test-Driven Development

The Iron Law of TDD: **NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

TDD is not "write code then add tests." It is a design discipline where tests drive the implementation. Every line of production code exists because a test required it.

## The Red-Green-Refactor Cycle

### 1. RED — Write a Failing Test

Write the smallest test that expresses a new behavior. Run it. It MUST fail. If it passes, either the test is wrong or the behavior already exists.

```typescript
// RED: Test for a function that doesn't exist yet
describe('calculateDiscount', () => {
  it('applies 10% discount for orders over $100', () => {
    expect(calculateDiscount(150)).toBe(135);
  });
});
```

### 2. GREEN — Write Minimum Code to Pass

Write the simplest, most direct code that makes the failing test pass. No more. No less. Do not anticipate future needs.

```typescript
// GREEN: Simplest code that passes
function calculateDiscount(amount: number): number {
  return amount * 0.9;
}
```

### 3. REFACTOR — Improve Without Changing Behavior

Clean up the code while keeping all tests green. Extract functions, rename variables, remove duplication. Tests are your safety net.

```typescript
// REFACTOR: Handle edge cases revealed by next tests
function calculateDiscount(amount: number): number {
  const DISCOUNT_THRESHOLD = 100;
  const DISCOUNT_RATE = 0.10;

  if (amount <= DISCOUNT_THRESHOLD) return amount;
  return amount * (1 - DISCOUNT_RATE);
}
```

## Key Principles

### Test Behavior, Not Implementation

Tests should describe WHAT the code does, not HOW it does it internally.

```typescript
// BAD: Tests implementation details
it('calls the internal _calculate method', () => {
  const spy = jest.spyOn(cart, '_calculate');
  cart.getTotal();
  expect(spy).toHaveBeenCalled();
});

// GOOD: Tests observable behavior
it('returns the sum of all item prices', () => {
  cart.addItem({ price: 10 });
  cart.addItem({ price: 20 });
  expect(cart.getTotal()).toBe(30);
});
```

### One Assertion Per Concept

Each test should verify one logical concept. Multiple assertions are fine if they all verify the same behavior.

```typescript
// GOOD: Multiple assertions, one concept (user creation)
it('creates a user with default settings', () => {
  const user = createUser({ name: 'Alice' });
  expect(user.name).toBe('Alice');
  expect(user.role).toBe('member');
  expect(user.active).toBe(true);
});
```

### Arrange-Act-Assert (AAA)

Every test follows three clear sections:

```typescript
it('calculates total with tax', () => {
  // Arrange
  const cart = new Cart();
  cart.addItem({ price: 100 });

  // Act
  const total = cart.getTotalWithTax(0.08);

  // Assert
  expect(total).toBe(108);
});
```

### Use Descriptive Test Names

Test names should read as specifications. Someone reading only test names should understand the system's behavior.

```typescript
// BAD
it('works correctly', () => {});
it('test 1', () => {});

// GOOD
it('rejects passwords shorter than 8 characters', () => {});
it('sends welcome email after successful registration', () => {});
it('returns 404 when item does not exist', () => {});
```

## Common Rationalizations (and Why They're Wrong)

| Rationalization | Reality |
|----------------|---------|
| "I'll add tests later" | Later never comes. Untested code accumulates. |
| "This is too simple to test" | Simple code gets complex. Tests document intent. |
| "Tests slow me down" | Tests accelerate you after the first 30 minutes. Debugging without tests is slower. |
| "I'll just test the important parts" | You can't know what's important until something breaks. |
| "The deadline is too tight" | Bugs found in production cost 10x more than tests written now. |

## Red Flags — You're Not Doing TDD If...

- You write production code before a test fails
- Your tests pass on the first run (they should fail first)
- You write all tests after the implementation
- You skip the refactor step
- You test private methods instead of public behavior
- You mock everything (tests become meaningless)
- You have tests but don't run them before committing

## Test Structure for Different Scales

### Unit Tests (Fast, Isolated)

Test a single function or class. Mock external dependencies.

```typescript
describe('PriceCalculator', () => {
  it('applies bulk discount at 10+ items', () => {
    const calc = new PriceCalculator();
    expect(calc.calculate({ quantity: 10, unitPrice: 50 })).toBe(450);
  });
});
```

### Integration Tests (Component Interactions)

Test how multiple units work together. Use real dependencies where practical.

```typescript
describe('OrderService', () => {
  it('creates order and updates inventory', async () => {
    const order = await orderService.place({ itemId: '1', quantity: 2 });
    expect(order.status).toBe('confirmed');
    const item = await inventoryService.getItem('1');
    expect(item.stock).toBe(8); // was 10
  });
});
```

### E2E Tests (Full System)

Test complete user workflows. Use Playwright or similar. See the `playwright-testing` skill for patterns.

## Verification Checklist

Before committing, verify:

- [ ] Every new function/method has at least one test
- [ ] Tests were written BEFORE the implementation
- [ ] All tests pass (red → green confirmed)
- [ ] Refactoring was done with tests as safety net
- [ ] Test names describe behaviors, not implementations
- [ ] No tests depend on execution order
- [ ] Mocks are minimal — prefer real objects where practical
