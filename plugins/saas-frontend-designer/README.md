# SaaS Frontend Designer

A Cowork plugin for designing and building production-ready front ends for SaaS products and marketing websites.

## Stack

- **Next.js 14+** (App Router, Server Components)
- **React 18+** with TypeScript
- **Tailwind CSS v3** (utility-first, mobile-first)
- **shadcn/ui** (Radix primitives + CVA variants)
- **Figma MCP** integration for design-to-code workflows

## Skills

| Skill | Purpose |
|-------|---------|
| **frontend-design** | Generate complete UI pages and components from descriptions — dashboards, landing pages, settings, data tables, onboarding flows |
| **baseline-ui** | Audit and fix visual polish issues — spacing, typography, colors, shadows, interactive states, loading/empty states |
| **accessibility-audit** | WCAG 2.1 AA compliance — semantic HTML, keyboard nav, focus management, contrast, ARIA patterns |
| **performance-optimization** | Core Web Vitals — image/font optimization, code splitting, CLS prevention, animation performance |
| **design-system** | Token architecture and component library — CSS variables, Tailwind config, CVA variants, dark mode |
| **figma-to-code** | Convert Figma designs to code via Figma MCP — extract context, map to stack, generate responsive implementation |

## Commands

| Command | Description |
|---------|-------------|
| `/design [description]` | Generate a UI page or component from a text description |
| `/polish [path]` | Run the full 4-phase polish pipeline (baseline → a11y → performance → summary) |
| `/a11y-audit [path]` | Run an accessibility audit with fixes |
| `/design-tokens [brand-color]` | Generate or update the design token system and Tailwind config |

## Usage Examples

**Generate a dashboard:**
> "Design a SaaS analytics dashboard with KPI cards, a line chart, and a recent activity table"

**Polish existing code:**
> `/polish app/dashboard/page.tsx`

**Convert a Figma design:**
> "Implement this Figma design: https://figma.com/design/abc123/MyApp?node-id=1-2"

**Set up design tokens:**
> `/design-tokens #4F46E5`

## Requirements

- Figma MCP connector (for figma-to-code skill only)
- No other external dependencies — all skills work with Claude's built-in tools

## Author

MoxyWolf LLC
