---
name: performance-optimization
description: >
  This skill should be used when the user says "optimize performance", "fix animation jank",
  "reduce bundle size", "improve page speed", "fix layout shift", "optimize images",
  "reduce loading time", "fix motion performance", "prefers-reduced-motion",
  "lazy load components", "code splitting", "Core Web Vitals",
  "LCP optimization", "CLS fix", "reduce JavaScript bundle",
  or any request to improve the loading speed, rendering performance, or animation quality of a web interface.
version: 1.0.0
---

# Performance Optimization — Speed & Motion

Optimize Next.js + React interfaces for Core Web Vitals, smooth animations, and fast loading. Focus on measurable impact.

## Core Web Vitals Targets

| Metric | Target | What it measures |
|--------|--------|-----------------|
| LCP (Largest Contentful Paint) | < 2.5s | Time until main content visible |
| FID/INP (Interaction to Next Paint) | < 200ms | Time between user input and visual response |
| CLS (Cumulative Layout Shift) | < 0.1 | Visual stability during load |

## Image Optimization

Images are the #1 cause of slow LCP. Always use `next/image`.

```tsx
import Image from "next/image"

// ✅ Optimized with next/image
<Image
  src="/hero-dashboard.png"
  alt="Dashboard overview"
  width={1200}
  height={675}
  priority                    // Add for above-the-fold images (hero, logo)
  className="rounded-lg"
  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1200px"
/>

// ❌ Never use raw img for content images
<img src="/hero.png" />
```

**Rules**:
- `priority` on hero images and above-the-fold content (prevents lazy load)
- Always set `width` and `height` to prevent CLS
- Use `sizes` prop for responsive images to serve correct size
- Use `placeholder="blur"` with `blurDataURL` for local images
- SVG icons and logos: use inline SVG or lucide-react, not `next/image`

## Font Optimization

```tsx
// app/layout.tsx — always use next/font
import { Inter } from "next/font/google"

const inter = Inter({
  subsets: ["latin"],
  display: "swap",        // Prevents invisible text during load
  variable: "--font-inter",
})

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans">{children}</body>
    </html>
  )
}
```

**Rules**:
- Always use `next/font` — self-hosts fonts, eliminates external requests
- Set `display: "swap"` to prevent FOIT (Flash of Invisible Text)
- Use `variable` for Tailwind integration
- Limit to 2 font families maximum (body + mono)

## Code Splitting & Dynamic Imports

Reduce initial JavaScript bundle by lazy-loading heavy components.

```tsx
import dynamic from "next/dynamic"

// Heavy chart library — only load when needed
const Chart = dynamic(() => import("@/components/Chart"), {
  ssr: false,
  loading: () => <Skeleton className="h-64 w-full" />,
})

// Rich text editor — client-only
const Editor = dynamic(() => import("@/components/Editor"), {
  ssr: false,
  loading: () => <Skeleton className="h-48 w-full" />,
})
```

**When to dynamic import**:
- Chart libraries (recharts, chart.js)
- Rich text editors
- Code editors / syntax highlighters
- Map components
- PDF viewers
- Any component > 50KB that isn't above-the-fold

## Layout Shift Prevention (CLS)

**Common causes and fixes**:

```tsx
// ❌ Image without dimensions — causes CLS
<img src="/photo.jpg" />

// ✅ Explicit dimensions
<Image src="/photo.jpg" width={400} height={300} alt="..." />

// ❌ Dynamic content pushing layout
{data && <div>Content loaded!</div>}

// ✅ Reserve space with skeleton
{data ? <DataDisplay data={data} /> : <Skeleton className="h-48" />}

// ❌ Font loading causes text resize
<link href="fonts.googleapis.com/..." />

// ✅ next/font with swap
const font = Inter({ display: "swap", subsets: ["latin"] })
```

**Rules**:
- All images: explicit `width` and `height`
- All async content: skeleton placeholder matching final size
- Fonts: `next/font` with `display: "swap"`
- Ads/embeds: reserve space with `min-height`
- Never inject content above existing content after load

## Animation Performance

### CSS Transitions (Preferred)

Use CSS transitions for simple state changes. Only animate `transform` and `opacity` — they're GPU-accelerated and don't trigger reflow.

```tsx
// ✅ GPU-accelerated transitions
className="transition-transform duration-200 hover:scale-105"
className="transition-opacity duration-150 ease-in-out"

// ❌ Triggers reflow — janky
className="transition-all duration-200 hover:w-96"      // width causes reflow
className="transition-all duration-200 hover:mt-4"       // margin causes reflow
className="transition-all duration-200 hover:h-screen"   // height causes reflow
```

**What to animate**: `transform` (translate, scale, rotate), `opacity`, `filter`, `backdrop-filter`
**What never to animate**: `width`, `height`, `top`, `left`, `margin`, `padding`, `font-size`

### Motion Preferences

Always respect `prefers-reduced-motion`.

```tsx
// Global: add to tailwind.config.ts
module.exports = {
  theme: {
    extend: {
      transitionDuration: {
        DEFAULT: '150ms',
      },
    },
  },
}

// Component level
className="motion-safe:transition-transform motion-safe:hover:scale-105"

// CSS: disable non-essential motion
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Rules**:
- Decorative animations: wrap in `motion-safe:` or `prefers-reduced-motion` media query
- Functional transitions (loading spinners, progress bars): keep but simplify
- Page transitions: crossfade instead of slide for reduced-motion users
- Never use animation for critical information delivery

### Animation Duration Guide

| Type | Duration | Easing |
|------|----------|--------|
| Hover state | 150ms | ease-in-out |
| Dropdown open | 200ms | ease-out |
| Modal open | 200ms | ease-out |
| Modal close | 150ms | ease-in |
| Page transition | 300ms | ease-in-out |
| Loading pulse | 1.5s | ease-in-out (infinite) |

## Server Component Optimization

Maximize Server Components to reduce client JavaScript.

```tsx
// ✅ Server Component (no "use client") — data fetching at the edge
export default async function DashboardPage() {
  const stats = await getStats()  // Runs on server, zero client JS
  return (
    <div>
      <StatsGrid stats={stats} />      {/* Server component */}
      <InteractiveChart data={stats} /> {/* Client component — only this ships JS */}
    </div>
  )
}

// ✅ Streaming with Suspense
import { Suspense } from "react"

export default function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<Skeleton className="h-32" />}>
        <StatsGrid />  {/* Streams in when data is ready */}
      </Suspense>
      <Suspense fallback={<Skeleton className="h-64" />}>
        <ActivityFeed />
      </Suspense>
    </div>
  )
}
```

## Route-Level Performance Files

Every route segment should include:

```
app/dashboard/
├── page.tsx          # The page
├── loading.tsx       # Streaming fallback (instant shell)
├── error.tsx         # Error boundary
└── not-found.tsx     # 404 for this segment
```

```tsx
// loading.tsx — shows immediately while page.tsx streams
export default function DashboardLoading() {
  return (
    <div className="p-6 space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
      <Skeleton className="h-64" />
    </div>
  )
}
```

## Performance Audit Checklist

- [ ] All images use `next/image` with explicit dimensions
- [ ] Hero image has `priority` prop
- [ ] Fonts loaded via `next/font` with `display: "swap"`
- [ ] Heavy components dynamically imported with loading fallback
- [ ] No layout shift: skeletons match final content size
- [ ] Animations use `transform`/`opacity` only
- [ ] `prefers-reduced-motion` respected for decorative motion
- [ ] Server Components used for data fetching (no unnecessary `"use client"`)
- [ ] `loading.tsx` in every route segment
- [ ] `Suspense` boundaries around async content
