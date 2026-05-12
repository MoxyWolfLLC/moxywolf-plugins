---
name: frontend-design
description: >
  This skill should be used when the user says "build a UI", "create a page",
  "design a screen", "generate a component", "build a landing page",
  "create a dashboard", "implement this design", "build a SaaS UI",
  "create a pricing page", "build a settings page", "design a hero section",
  "create a signup form", "build an admin panel", "make a marketing page",
  or any request to generate front-end code for a SaaS product or website.
version: 1.0.0
---

# Frontend Design — SaaS UI Generation

Generate production-ready Next.js + React + Tailwind + shadcn/ui interfaces for SaaS applications and marketing sites. Every output must be deployable code, not wireframes or mockups.

## Stack

- **Framework**: Next.js 14+ (App Router, Server Components by default)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS v3+ (utility-first, mobile-first breakpoints)
- **Components**: shadcn/ui (Radix primitives, CVA variants)
- **Icons**: lucide-react
- **Fonts**: next/font with Inter (body) and Geist Mono (code)
- **Forms**: react-hook-form + zod validation
- **State**: Server Components for data, `"use client"` only for interactivity

## Design Direction Process

Before writing any code, establish design direction by answering these five questions:

1. **What type of page?** SaaS dashboard, marketing landing, settings/admin, onboarding flow, or data-heavy table view
2. **Who is the user?** Technical buyer, end user, admin, visitor, or mixed
3. **What density?** Spacious (marketing), balanced (app), compact (data-heavy)
4. **What mood?** Professional/corporate, modern/minimal, bold/energetic, warm/friendly
5. **What's the primary action?** Every page has ONE thing you most want the user to do

> **UX Spec Shortcut**: If a completed UX spec exists for this screen (see `references/ux-spec-template.md`), these five questions are already answered. Extract the page type from Section 2.X.1 (Purpose), the user from 2.X.2 (User Motivations), the density and mood from the component breakdown in 2.X.3, and the primary action from the first row of 2.X.4 (Action Consequences). The spec also provides Action Consequences → feedback pattern mapping, State Conditions → required states, and responsive/a11y requirements that go beyond what these five questions capture.

## Page Type Blueprints

### SaaS Dashboard

```
┌─────────────────────────────────────────────┐
│ [Logo] [Nav items...]        [User avatar ▾] │  ← Top bar (h-14, border-b)
├──────────┬──────────────────────────────────┤
│ Sidebar  │  Page Title          [+ Action]  │  ← 64px sidebar, flex-1 main
│ • Nav 1  │  ┌─────┐ ┌─────┐ ┌─────┐       │
│ • Nav 2  │  │ KPI │ │ KPI │ │ KPI │        │  ← Metric cards (grid-cols-3)
│ • Nav 3  │  └─────┘ └─────┘ └─────┘       │
│          │  ┌──────────────────────────┐    │
│ Section  │  │ Chart / Table / Content  │    │  ← Primary content area
│ • Nav 4  │  │                          │    │
│ • Nav 5  │  └──────────────────────────┘    │
└──────────┴──────────────────────────────────┘
```

Layout code:
```tsx
<div className="flex h-screen overflow-hidden">
  <aside className="hidden md:flex md:w-64 md:flex-col border-r bg-gray-50/50">
    <div className="flex h-14 items-center border-b px-4">
      {/* Logo */}
    </div>
    <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
      {/* Nav items */}
    </nav>
  </aside>
  <div className="flex flex-1 flex-col overflow-hidden">
    <header className="flex h-14 items-center justify-between border-b px-6">
      {/* Breadcrumb + actions */}
    </header>
    <main className="flex-1 overflow-y-auto p-6">
      {/* Page content */}
    </main>
  </div>
</div>
```

### Marketing Landing Page

```
┌─────────────────────────────────────────────┐
│ [Logo]   [Features] [Pricing] [Login] [CTA] │  ← Sticky nav
├─────────────────────────────────────────────┤
│           Hero Section (py-24)               │  ← Headline + subhead + CTA
│    H1: Value proposition (max 8 words)       │
│    p: Supporting detail (max 2 lines)        │
│    [Primary CTA]  [Secondary CTA]            │
├─────────────────────────────────────────────┤
│          Social proof / logos bar            │  ← Trust signals
├─────────────────────────────────────────────┤
│          Feature grid (3-col)                │  ← Benefits, not features
├─────────────────────────────────────────────┤
│          Pricing section                     │  ← 2-3 tiers, highlight popular
├─────────────────────────────────────────────┤
│          Testimonials                        │  ← Real quotes with names/roles
├─────────────────────────────────────────────┤
│          Final CTA section                   │  ← Repeat primary conversion
├─────────────────────────────────────────────┤
│          Footer                              │  ← Links, legal, socials
└─────────────────────────────────────────────┘
```

Section rhythm: alternate `bg-white` and `bg-gray-50` sections. Each section: `py-16 md:py-24`. Max content width: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`.

### Settings / Admin Page

Sidebar or tab navigation with form-heavy content. Group related settings. Use `Card` containers for each group. Save button sticky at bottom or top of form area.

```tsx
<div className="space-y-6">
  <div>
    <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
    <p className="mt-1 text-sm text-gray-500">Manage your account preferences.</p>
  </div>
  <Tabs defaultValue="general">
    <TabsList>
      <TabsTrigger value="general">General</TabsTrigger>
      <TabsTrigger value="billing">Billing</TabsTrigger>
      <TabsTrigger value="team">Team</TabsTrigger>
    </TabsList>
    <TabsContent value="general" className="mt-6">
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Update your personal information.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Form fields */}
        </CardContent>
        <CardFooter className="flex justify-end">
          <Button>Save changes</Button>
        </CardFooter>
      </Card>
    </TabsContent>
  </Tabs>
</div>
```

## Component Patterns

### Server vs Client Decision Tree

```
Does the component need:
  → useState, useEffect, event handlers? → "use client"
  → Browser APIs (localStorage, window)? → "use client"
  → Only renders data passed as props?   → Server Component (default)
  → Fetches data from DB/API?            → Server Component with async
```

### shadcn/ui Component Selection

| Need | Component | Notes |
|------|-----------|-------|
| Primary action | `Button` variant="default" | One per view section |
| Secondary action | `Button` variant="outline" or "ghost" | |
| Data display | `Table` | With `DataTable` pattern for sorting/filtering |
| Content container | `Card` | Header + Content + Footer slots |
| Modal dialog | `Dialog` | Controlled with state |
| Side panel | `Sheet` | Mobile nav, detail views, filters |
| Dropdown menu | `DropdownMenu` | User menu, action menus |
| Selection | `Select` | Single choice from list |
| Multi-select | `Command` (combobox pattern) | Searchable multi-select |
| Notifications | `Sonner` (toast) | Success/error feedback |
| Form validation | `Form` + `Input` + zod | Inline error messages |
| Status indicator | `Badge` | Semantic colors for state |
| Loading placeholder | `Skeleton` | Match content shape |
| Tabs | `Tabs` | 2-7 views of same context |

### Form Pattern (Standard)

```tsx
"use client"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const formSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email"),
})

type FormValues = z.infer<typeof formSchema>

export function ExampleForm() {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: "", email: "" },
  })

  async function onSubmit(data: FormValues) {
    // Handle submission
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField control={form.control} name="name" render={({ field }) => (
          <FormItem>
            <FormLabel>Name</FormLabel>
            <FormControl><Input placeholder="Your name" {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <FormField control={form.control} name="email" render={({ field }) => (
          <FormItem>
            <FormLabel>Email</FormLabel>
            <FormControl><Input type="email" placeholder="you@example.com" {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving..." : "Save"}
        </Button>
      </form>
    </Form>
  )
}
```

## Styling Rules

### Color System

Use a minimal palette: 1 brand color, neutral grays, and semantic colors.

```
Brand:    blue-600 (default) / configurable via design-system skill
Neutral:  gray-50 through gray-900
Success:  green-600 / green-50
Warning:  yellow-600 / yellow-50
Error:    red-600 / red-50
Info:     blue-600 / blue-50
```

### Spacing Scale

Use Tailwind's 4px grid exclusively: 1 (4px), 2 (8px), 3 (12px), 4 (16px), 5 (20px), 6 (24px), 8 (32px), 10 (40px), 12 (48px), 16 (64px), 20 (80px), 24 (96px).

Never use arbitrary values like `p-[13px]`. Snap to the grid.

### Typography

```
Page title:    text-2xl font-bold text-gray-900
Section head:  text-xl font-semibold text-gray-800
Subsection:    text-base font-semibold text-gray-800
Body:          text-sm text-gray-600 leading-relaxed
Caption:       text-xs text-gray-500
```

### Border Radius

Consistent per element type: buttons `rounded-md`, cards `rounded-lg`, inputs `rounded-md`, badges `rounded-full`, modals `rounded-xl`.

## Responsive Strategy

Mobile-first. Design for 375px first, then progressively enhance.

| Breakpoint | Width | Typical use |
|-----------|-------|-------------|
| default | 0-639px | Single column, stacked layout |
| `sm:` | 640px+ | 2-column grids, larger touch targets |
| `md:` | 768px+ | Show sidebar, increase padding |
| `lg:` | 1024px+ | Full desktop layout, multi-column |
| `xl:` | 1280px+ | Max-width containers, wider spacing |

### Mobile Navigation Pattern

```tsx
// Desktop: sidebar. Mobile: bottom tab bar or hamburger Sheet
<Sheet>
  <SheetTrigger asChild>
    <Button variant="ghost" size="icon" className="md:hidden">
      <Menu className="h-5 w-5" />
    </Button>
  </SheetTrigger>
  <SheetContent side="left" className="w-64">
    {/* Same nav items as sidebar */}
  </SheetContent>
</Sheet>
```

## Three Required States

Every data-dependent view MUST have:

1. **Loading**: Skeleton placeholders matching content shape
2. **Empty**: Explanation + illustration + single CTA to populate
3. **Error**: What went wrong + how to fix it + retry action

```tsx
// Loading
<div className="space-y-3">
  {Array.from({ length: 3 }).map((_, i) => (
    <Skeleton key={i} className="h-16 w-full" />
  ))}
</div>

// Empty
<div className="flex flex-col items-center justify-center py-12 text-center">
  <FileText className="h-10 w-10 text-gray-300 mb-4" />
  <h3 className="text-base font-semibold text-gray-900">No documents yet</h3>
  <p className="mt-1 text-sm text-gray-500 max-w-sm">
    Upload your first document to get started.
  </p>
  <Button className="mt-4">
    <Plus className="mr-2 h-4 w-4" /> Upload document
  </Button>
</div>
```

## Output Checklist

Before delivering any generated UI code, verify:

- [ ] TypeScript types for all props (no `any`)
- [ ] Server Component by default; `"use client"` only when needed
- [ ] Mobile-first responsive (works at 375px)
- [ ] All interactive elements keyboard-accessible
- [ ] Loading, empty, and error states present
- [ ] Single primary CTA per view section
- [ ] Spacing on 4px grid (no arbitrary values)
- [ ] Color contrast meets WCAG AA (4.5:1 body, 3:1 large)
- [ ] `aria-label` on icon-only buttons
- [ ] `alt` text on all images

### UX Spec Verification (when spec provided)

If a UX spec was used as input, additionally verify:

- [ ] Every action in the Action Consequences table (2.X.4) has a corresponding feedback implementation (AlertDialog, Sonner toast, FormMessage, or undo toast)
- [ ] Every condition in the State Conditions table (2.X.5) has a rendered UI state beyond the standard three
- [ ] Every icon/symbol in the Legend (Section 6) is mapped to a `Badge` variant with semantic color and `aria-label`
- [ ] Additional System States (Section 5) are implemented as reusable error components
- [ ] Responsive specs from Section 7 are reflected in breakpoint class usage
- [ ] Cross-screen navigation from Section 3 is reflected in sidebar/tab/breadcrumb structure

## Additional Resources

Consult `references/page-templates.md` for complete SaaS page templates including pricing pages, onboarding flows, data tables, and user profile screens.
Consult `references/ux-spec-template.md` for the UX specification template. When a completed spec exists, it overrides the Design Direction Process and provides structured input for component selection, feedback patterns, state handling, and responsive behavior.
