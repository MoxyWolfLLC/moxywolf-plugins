# Advanced Figma-to-Code Patterns

## Auto Layout Deep Mapping

### Spacing Modes

| Figma Setting | CSS/Tailwind |
|--------------|-------------|
| Auto layout: Packed | `flex` + `gap-{n}` |
| Auto layout: Space between | `flex justify-between` |
| Auto layout: Fixed width child | `w-{n}` or `flex-none` |
| Auto layout: Fill container child | `flex-1` |
| Auto layout: Hug contents | `w-fit` (default flex behavior) |
| Wrap | `flex-wrap` |

### Padding Mapping

| Figma | Tailwind |
|-------|---------|
| Uniform 16px | `p-4` |
| Horizontal 24, Vertical 16 | `px-6 py-4` |
| Top 32, Right 24, Bottom 16, Left 24 | `pt-8 px-6 pb-4` |
| Individual sides all different | `pt-{a} pr-{b} pb-{c} pl-{d}` |

### Alignment Matrix

| Figma Primary × Counter | Tailwind |
|------------------------|---------|
| Left, Top | `flex items-start justify-start` |
| Center, Center | `flex items-center justify-center` |
| Right, Bottom | `flex items-end justify-end` |
| Space Between, Center | `flex items-center justify-between` |
| Left, Stretch | `flex items-stretch` |

## Component Set → CVA Variant Mapping

When a Figma component has properties/variants, map them to CVA:

### Single Property Component

Figma: Button with `Type = Primary | Secondary | Ghost`

```tsx
const buttonVariants = cva("base-classes", {
  variants: {
    variant: {
      primary: "bg-primary text-primary-foreground",
      secondary: "bg-secondary text-secondary-foreground",
      ghost: "hover:bg-accent",
    },
  },
  defaultVariants: { variant: "primary" },
})
```

### Multi-Property Component

Figma: Button with `Type = Primary | Secondary` AND `Size = SM | MD | LG` AND `State = Default | Hover | Disabled`

```tsx
const buttonVariants = cva("base-classes", {
  variants: {
    variant: {
      primary: "bg-primary text-primary-foreground hover:bg-primary/90",
      secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    },
    size: {
      sm: "h-8 px-3 text-xs",
      md: "h-9 px-4 text-sm",
      lg: "h-10 px-8 text-base",
    },
  },
  defaultVariants: { variant: "primary", size: "md" },
})
```

Note: Figma "State" properties (Default, Hover, Pressed, Disabled, Focus) map to CSS pseudo-classes and HTML attributes, not CVA variants.

### Boolean Properties

Figma: Card with `Has Icon = true | false`, `Has Badge = true | false`

```tsx
interface CardProps {
  icon?: React.ReactNode    // Renders when Has Icon = true
  badge?: string            // Renders when Has Badge = true
  children: React.ReactNode
}

function FeatureCard({ icon, badge, children }: CardProps) {
  return (
    <Card>
      <CardHeader>
        {icon && <div className="mb-2">{icon}</div>}
        {badge && <Badge>{badge}</Badge>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
```

## Responsive Design from Single-Breakpoint Designs

Figma files typically show one breakpoint. Infer responsive behavior:

### Layout Collapse Rules

| Desktop Pattern | Mobile Adaptation |
|----------------|-------------------|
| 3-column grid | Single column, stacked |
| 2-column with sidebar | Sidebar → drawer/sheet |
| Horizontal nav tabs | Scrollable tabs or dropdown |
| Side-by-side cards | Stacked cards |
| Data table | Horizontal scroll or card view |
| Multi-column form | Single column |
| Fixed sidebar + content | Collapsible sidebar via Sheet |

### Breakpoint Strategy

```tsx
// Desktop-first Figma → mobile-first code
// Always start with mobile layout, add up

// Figma shows 3 columns at 1280px wide:
<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">

// Figma shows sidebar + content:
<div className="flex flex-col lg:flex-row">
  <aside className="hidden lg:block lg:w-64">...</aside>
  <main className="flex-1">...</main>
</div>

// On mobile, sidebar becomes a Sheet:
<Sheet>
  <SheetTrigger asChild>
    <Button variant="ghost" size="icon" className="lg:hidden">
      <Menu className="size-4" />
    </Button>
  </SheetTrigger>
  <SheetContent side="left">
    {/* Same nav content as sidebar */}
  </SheetContent>
</Sheet>
```

## Color Extraction

### From Figma Fills to Tailwind

| Figma Fill | Approach |
|-----------|---------|
| Solid color matching Tailwind palette | Use Tailwind class: `bg-blue-600` |
| Solid color close to palette | Snap to nearest: `bg-blue-700` |
| Brand color (custom hex) | CSS variable: `bg-[hsl(var(--brand))]` |
| Opacity fill | Tailwind opacity: `bg-blue-600/80` |
| Gradient | `bg-gradient-to-r from-blue-600 to-purple-600` |

### Color Variable Mapping from Figma

When Figma file uses design tokens/variables:

```
Figma Variable Collection → CSS Variables → Tailwind Config

colors/primary/500  →  --color-primary: 220 90% 56%  →  primary: "hsl(var(--color-primary))"
colors/gray/100     →  --color-gray-100: 220 14% 96% →  (use Tailwind gray directly)
spacing/md          →  --spacing-md: 1rem            →  (use Tailwind space-4)
radius/lg           →  --radius-lg: 0.75rem          →  (use rounded-xl)
```

## Figma Effects → Tailwind

### Shadows

| Figma Shadow | Tailwind |
|-------------|---------|
| X:0, Y:1, Blur:2, Spread:0, #000/5% | `shadow-sm` |
| X:0, Y:1, Blur:3, Spread:0, #000/10% + X:0, Y:1, Blur:2, Spread:-1 | `shadow` |
| X:0, Y:4, Blur:6, Spread:-1, #000/10% | `shadow-md` |
| X:0, Y:10, Blur:15, Spread:-3, #000/10% | `shadow-lg` |
| X:0, Y:20, Blur:25, Spread:-5, #000/10% | `shadow-xl` |
| X:0, Y:25, Blur:50, Spread:-12, #000/25% | `shadow-2xl` |
| Inner shadow | `shadow-inner` |

### Blur Effects

| Figma Effect | Tailwind |
|-------------|---------|
| Background blur 8px | `backdrop-blur-sm` |
| Background blur 12px | `backdrop-blur` |
| Background blur 16px | `backdrop-blur-md` |
| Layer blur | `blur-sm`, `blur`, `blur-md` |

## Image Handling

### Figma Image Fills → next/image

```tsx
// Figma frame with image fill, 800×400
<div className="relative aspect-[2/1] overflow-hidden rounded-lg">
  <Image
    src="/path/to/image.jpg"
    alt="Descriptive alt text"
    fill
    className="object-cover"
    sizes="(max-width: 768px) 100vw, 800px"
  />
</div>

// Figma avatar circle, 40×40
<Image
  src={user.avatar}
  alt={user.name}
  width={40}
  height={40}
  className="rounded-full"
/>
```

### Downloading Figma Assets

The `get_design_context` tool returns download URLs for images used in the design. Download them and place in `/public/images/` or use a CDN URL.

## Interactive Prototype Translation

Figma prototyping connections don't carry into code, but inform navigation:

| Figma Interaction | Code Implementation |
|------------------|-------------------|
| Navigate to frame | `<Link href="/page">` or `router.push()` |
| Open overlay | `<Dialog>` or `<Sheet>` |
| Swap component | State change via `useState` |
| Scroll to | `<a href="#section">` or `scrollIntoView()` |
| Smart animate | `transition-all duration-200` or Framer Motion |
| Hover change | CSS `:hover` pseudo-class |

## Design System Sync

For ongoing Figma → Code synchronization:

1. **Token extraction**: Run `get_variable_defs` periodically to check for token changes
2. **Component audit**: Compare Figma component properties with CVA variants
3. **Visual regression**: Screenshot both Figma and rendered code for comparison
4. **Code Connect**: Use `add_code_connect_map` to link Figma components to code files

### Code Connect Mapping

```tsx
// After implementing a component, register the mapping:
// This makes Figma show the code reference when designers inspect components

// Tool: add_code_connect_map
// nodeId: "123:456" (Figma component node)
// fileKey: "abc123"
// source: "src/components/ui/button.tsx"
// componentName: "Button"
// label: "React"
```
