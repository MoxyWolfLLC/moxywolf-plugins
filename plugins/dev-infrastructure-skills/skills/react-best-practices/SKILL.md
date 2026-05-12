---
name: react-best-practices
description: >
  This skill should be used when the user asks to "write a React component",
  "optimize React performance", "fix React re-renders", "reduce bundle size",
  "eliminate waterfalls", "improve React patterns", "review React code",
  or needs guidance on React hooks, server components, data fetching,
  rendering optimization, or component architecture best practices.
version: 0.1.0
---

# React Best Practices

Comprehensive React performance and architecture patterns organized by priority. Apply these rules when writing, reviewing, or optimizing React code.

## Priority Categories

Rules are organized into 8 categories by impact. Categories marked CRITICAL should always be checked.

1. **Eliminating Waterfalls** (CRITICAL) — Prevent sequential data fetching
2. **Bundle Size Optimization** (CRITICAL) — Minimize JavaScript shipped to client
3. **Server-Side Performance** (HIGH) — Optimize server rendering and caching
4. **Client-Side Data Fetching** (HIGH) — Efficient client data patterns
5. **Re-render Optimization** (MEDIUM) — Prevent unnecessary component updates
6. **Rendering Performance** (MEDIUM) — Optimize what gets rendered
7. **JavaScript Performance** (LOW) — Micro-optimizations for hot paths
8. **Advanced Patterns** (CONTEXT-DEPENDENT) — Specialized techniques

## 1. Eliminating Waterfalls (CRITICAL)

### Defer Await Until Needed

Start async operations immediately but defer `await` until data is actually needed. This converts sequential fetches into parallel ones.

```typescript
// BAD: Sequential — second fetch waits for first
async function Page() {
  const user = await getUser();
  const posts = await getPosts(user.id);
  return <Feed user={user} posts={posts} />;
}

// GOOD: Parallel — both start immediately
async function Page() {
  const userPromise = getUser();
  const postsPromise = getPosts();
  const user = await userPromise;
  const posts = await postsPromise;
  return <Feed user={user} posts={posts} />;
}
```

### Dependency-Based Parallelization

When fetches have dependencies, parallelize independent branches while respecting the dependency chain.

```typescript
// GOOD: Parallel branches with dependencies
async function Dashboard() {
  const [user, config] = await Promise.all([getUser(), getConfig()]);
  const [posts, settings] = await Promise.all([
    getPosts(user.id),
    getUserSettings(user.id),
  ]);
  return <DashboardView user={user} posts={posts} settings={settings} config={config} />;
}
```

### Strategic Suspense Boundaries

Place `<Suspense>` boundaries to unlock parallel streaming. Each boundary creates an independent loading unit.

```tsx
// GOOD: Independent loading for each section
function Page() {
  return (
    <div>
      <Suspense fallback={<HeaderSkeleton />}>
        <Header />
      </Suspense>
      <Suspense fallback={<FeedSkeleton />}>
        <Feed />
      </Suspense>
      <Suspense fallback={<SidebarSkeleton />}>
        <Sidebar />
      </Suspense>
    </div>
  );
}
```

## 2. Bundle Size Optimization (CRITICAL)

### Avoid Barrel File Imports

Import directly from source modules, not barrel files (`index.ts`). Barrel imports pull in entire libraries.

```typescript
// BAD: Imports entire library
import { Button } from '@/components';

// GOOD: Direct import
import { Button } from '@/components/ui/button';
```

For third-party libraries, use `optimizePackageImports` in next.config:
```js
experimental: {
  optimizePackageImports: ['lucide-react', '@heroicons/react', 'date-fns']
}
```

### Conditional Module Loading

Load heavy modules only when the runtime context requires them:

```typescript
// GOOD: Load only needed parser
async function parseDocument(type: string) {
  if (type === 'pdf') {
    const { parsePDF } = await import('./parsers/pdf');
    return parsePDF;
  }
  const { parseText } = await import('./parsers/text');
  return parseText;
}
```

### Defer Non-Critical Libraries

Use `next/dynamic` or lazy loading for below-the-fold or interaction-triggered components:

```tsx
const HeavyChart = dynamic(() => import('./HeavyChart'), {
  loading: () => <ChartSkeleton />,
  ssr: false,
});
```

## 3. Re-render Optimization (MEDIUM)

### Lift State Down, Not Up

Keep state as close to where it's used as possible. When parent state changes, all children re-render.

### Use `useMemo` and `useCallback` Strategically

Only memoize when: (a) expensive computation, (b) referential equality matters for child components, or (c) dependency of other hooks.

```typescript
// GOOD: Expensive filter operation
const filtered = useMemo(
  () => items.filter(complexPredicate).sort(expensiveSort),
  [items]
);

// BAD: Simple value — memoization overhead exceeds benefit
const label = useMemo(() => `Hello ${name}`, [name]);
```

### Composition Over Context for Frequent Updates

When context values change often, split into multiple contexts or use composition:

```tsx
// GOOD: Children passed as props don't re-render on parent state change
function Layout({ children }: { children: React.ReactNode }) {
  const [count, setCount] = useState(0);
  return (
    <div>
      <Counter count={count} setCount={setCount} />
      {children} {/* Does NOT re-render when count changes */}
    </div>
  );
}
```

## 4. Server Components & Data Patterns

### Default to Server Components

Components are Server Components by default. Only add `'use client'` when you need:
- `useState`, `useEffect`, or other hooks
- Browser APIs (`window`, `document`)
- Event handlers (`onClick`, `onChange`)
- Class components

### Fetch in Server Components, Not Client

```typescript
// GOOD: Server component — no client JS, no loading state needed
async function UserProfile({ id }: { id: string }) {
  const user = await db.users.findUnique({ where: { id } });
  return <ProfileCard user={user} />;
}
```

### Don't Pass Non-Serializable Props Across the Boundary

Server-to-client props must be JSON-serializable:
- `Date` → use `.toISOString()`
- `Map`/`Set` → convert to `Object.fromEntries()` / `Array.from()`
- Functions → use server actions instead

## Quick Reference Checklist

When writing or reviewing React code, verify:

- [ ] No sequential awaits that could be parallel
- [ ] Suspense boundaries around independent async sections
- [ ] No barrel file imports for large libraries
- [ ] Heavy components use dynamic imports
- [ ] State lives as close to usage as possible
- [ ] Server Components used by default; `'use client'` only when needed
- [ ] Non-serializable data converted before crossing server/client boundary
- [ ] `useMemo`/`useCallback` used only for genuinely expensive operations

For the complete 40+ rule reference with all code examples, see `references/`.
