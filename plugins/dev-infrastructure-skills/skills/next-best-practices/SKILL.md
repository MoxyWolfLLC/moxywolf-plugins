---
name: next-best-practices
description: >
  This skill should be used when the user asks to "create a Next.js page",
  "set up App Router", "use server components", "implement server actions",
  "configure Next.js caching", "add middleware", "optimize Next.js performance",
  "fix Next.js routing", or needs guidance on Next.js file conventions,
  RSC boundaries, data fetching patterns, async patterns (Next.js 15+),
  or 'use client'/'use server'/'use cache' directives.
version: 0.1.0
---

# Next.js Best Practices

Patterns and conventions for Next.js App Router development, covering file conventions, React Server Component boundaries, data patterns, async APIs (Next.js 15+), and directives.

## File Conventions

### Project Structure

```
app/
├── layout.tsx          # Root layout (required)
├── page.tsx            # Home page
├── loading.tsx         # Loading UI (wraps page in Suspense)
├── error.tsx           # Error boundary
├── not-found.tsx       # 404 page
├── global-error.tsx    # Root error boundary
├── (group)/            # Route group (no URL segment)
│   └── page.tsx
├── [slug]/             # Dynamic segment
│   └── page.tsx
├── [...slug]/          # Catch-all segment
│   └── page.tsx
├── [[...slug]]/        # Optional catch-all
│   └── page.tsx
├── @modal/             # Parallel route (named slot)
│   └── page.tsx
└── (.)item/            # Intercepting route
    └── page.tsx
```

### Special Files

Each route segment can export these files. They render in a specific hierarchy:

1. `layout.tsx` — Shared UI wrapper (persists across navigation)
2. `template.tsx` — Like layout but re-mounts on navigation
3. `loading.tsx` — Suspense fallback for the segment
4. `error.tsx` — Error boundary for the segment
5. `page.tsx` — The actual route content
6. `not-found.tsx` — Shown when `notFound()` is called
7. `route.tsx` — API route handler (cannot coexist with `page.tsx`)

### Route Handlers

```typescript
// app/api/items/route.ts
export async function GET(request: Request) {
  const items = await db.items.findMany();
  return Response.json(items);
}

export async function POST(request: Request) {
  const body = await request.json();
  const item = await db.items.create({ data: body });
  return Response.json(item, { status: 201 });
}
```

## RSC Boundaries

### Detection Rules

These patterns indicate a component MUST be a Client Component (`'use client'`):

1. **Hooks**: `useState`, `useEffect`, `useReducer`, `useContext`, `useRef` (when mutated)
2. **Browser APIs**: `window`, `document`, `localStorage`, `navigator`
3. **Event handlers**: `onClick`, `onChange`, `onSubmit`, etc.
4. **Class components**: Any `extends React.Component`

### Async Client Components Are Invalid

```typescript
// INVALID — will error
'use client';
export default async function ClientPage() {
  const data = await fetch('/api/data');
  return <div>{data}</div>;
}

// VALID — use useEffect or React.use() instead
'use client';
export default function ClientPage() {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch('/api/data').then(r => r.json()).then(setData);
  }, []);
  return <div>{data}</div>;
}
```

### Non-Serializable Props

Props crossing the server → client boundary must be JSON-serializable:

| Type | Fix |
|------|-----|
| `Date` | `.toISOString()` |
| `Map` | `Object.fromEntries()` |
| `Set` | `Array.from()` |
| `Function` | Use server action |
| `Class instance` | Extract plain object |

**Exception**: Server actions (functions marked with `'use server'`) CAN be passed as props.

## Data Patterns

### Decision Tree

- **Reading data in Server Component** → Fetch directly (`async/await`)
- **Mutating data** → Server Actions (`'use server'`)
- **API for external clients** → Route Handlers (`route.ts`)
- **Client-side data** → `useEffect` + fetch, or SWR/React Query

### Waterfall Avoidance

```tsx
// BAD: Layout fetches → Page fetches → Component fetches (waterfall)
// GOOD: Each component fetches its own data, wrapped in Suspense
async function Page() {
  return (
    <>
      <Suspense fallback={<Skeleton />}>
        <UserProfile />  {/* Fetches user */}
      </Suspense>
      <Suspense fallback={<Skeleton />}>
        <RecentPosts />  {/* Fetches posts — parallel! */}
      </Suspense>
    </>
  );
}
```

## Async Patterns (Next.js 15+)

In Next.js 15+, several APIs became async and return Promises:

```typescript
// params and searchParams are now Promises
type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ q?: string }>;
};

export default async function Page({ params, searchParams }: Props) {
  const { slug } = await params;
  const { q } = await searchParams;
  return <Article slug={slug} query={q} />;
}
```

### Async APIs in Next.js 15+

| API | Change |
|-----|--------|
| `params` | `Promise<Params>` — must `await` |
| `searchParams` | `Promise<SearchParams>` — must `await` |
| `cookies()` | Returns `Promise` — must `await` |
| `headers()` | Returns `Promise` — must `await` |
| `draftMode()` | Returns `Promise` — must `await` |

For Client Components receiving async params, use `React.use()`:

```tsx
'use client';
import { use } from 'react';

export default function ClientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <div>Item: {id}</div>;
}
```

## Directives

### `'use client'`

Marks the entry point into client-side code. Place at the TOP of the file, before imports.

- Everything imported by a `'use client'` file becomes part of the client bundle
- Push `'use client'` as far down the component tree as possible
- Server Components can import Client Components, but not vice versa (for server-only logic)

### `'use server'`

Marks functions as Server Actions callable from client code.

```typescript
// Can be file-level (entire file is server actions)
'use server';

export async function createItem(formData: FormData) {
  const name = formData.get('name');
  await db.items.create({ data: { name } });
  revalidatePath('/items');
}
```

### `'use cache'` (Experimental)

Marks a function or component for caching. Must opt in via `next.config`:

```typescript
'use cache';

export async function getCachedData() {
  const data = await db.query();
  return data; // Result is cached and reused
}
```

For detailed reference on each topic, see `references/`.
