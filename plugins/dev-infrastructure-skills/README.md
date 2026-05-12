# Dev Infrastructure Skills

Framework-specific development best practices for MoxyWolf's engineering stack. Fills the knowledge gaps that workflow orchestrators need to produce better code.

## Skills Included

| Skill | Triggers On | Source |
|-------|------------|--------|
| **React Best Practices** | "write a React component", "optimize React performance", "fix re-renders", "reduce bundle size" | vercel-labs/agent-skills |
| **Next.js Best Practices** | "create a Next.js page", "set up App Router", "use server components", "server actions" | vercel-labs/next-skills |
| **Supabase & Postgres** | "write a Supabase query", "set up RLS policies", "create a migration", "optimize Postgres" | supabase/agent-skills |
| **Test-Driven Development** | "write tests first", "do TDD", "red-green-refactor", "add test coverage" | obra/superpowers |
| **Playwright Testing** | "write E2E tests", "set up Playwright", "fix flaky tests", "test user flows" | currents-dev/playwright-best-practices-skill |

## How These Work Together

These skills complement the existing dev orchestrators (`dev-create-orchestrator`, `dev-review-orchestrator`) by providing the domain knowledge those workflows reference. When an orchestrator says "follow React best practices," these skills supply the actual patterns.

## Version

0.1.0 — Initial release with 5 core skills sourced from the skills.sh ecosystem.
