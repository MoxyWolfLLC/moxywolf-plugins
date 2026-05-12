---
description: Generate a SaaS UI page or component from a description
allowed-tools: Read, Write, Edit, Bash(npx:*), Glob, Grep
argument-hint: [page-type-or-description]
---

Generate a production-ready Next.js + React + Tailwind + shadcn/ui interface based on the user's description: $ARGUMENTS

Follow the frontend-design skill for all patterns, decisions, and output standards.

**Process:**

1. **UX Spec Gate** — Before any code generation, check for a completed UX spec:
   - Search the working directory for a UX spec document matching this screen/component (filename pattern: `ux-spec-*.md`, `ux-doc-*.md`, or any markdown file containing "UX Documentation for")
   - **If a UX spec exists**: Read it and extract design decisions from the "Design gate" annotations:
     - 2.X.1 Purpose → page type blueprint selection
     - 2.X.2 User Motivations → primary CTA and secondary action placement
     - 2.X.3 Key Components → shadcn/ui component mapping
     - 2.X.4 Action Consequences → feedback pattern selection (AlertDialog, Sonner, FormMessage)
     - 2.X.5 State Conditions → required states beyond the standard three (loading, empty, error)
     - Section 5 Additional System States → reusable error components
     - Section 6 Icon & Tag Legend → Badge variants with semantic colors
     - Section 7 Responsive → breakpoint overrides and screen-specific a11y requirements
   - **If no UX spec exists**: Ask the user whether to:
     - (a) Fill out a quick UX spec now (walk through Purpose, User Motivations, Key Components, Action Consequences, and State Conditions for this screen)
     - (b) Proceed without a spec (use the standard Design Direction Process from the frontend-design skill)
   - If proceeding without a spec, document the design decisions made during generation in a `_ux-spec-[screen-name].md` file alongside the output as a post-hoc record
2. Determine page type: SaaS dashboard, marketing landing, settings/admin, onboarding, or data table
3. Establish design direction (density, mood, primary action)
4. Select the appropriate page blueprint from the frontend-design skill
5. Generate complete TypeScript component(s) with:
   - Server Components by default, "use client" only when needed
   - Mobile-first responsive layout
   - shadcn/ui components for all standard UI elements
   - Proper form handling with react-hook-form + zod if forms are involved
   - All three states: loading, empty, populated
   - Accessible markup (semantic HTML, aria labels, keyboard navigation)
   - **If UX spec provided**: All Action Consequences implemented with correct feedback patterns, all State Conditions handled, all Icon/Tag Legend items mapped to Badge variants
6. Include all necessary imports and type definitions

Write the output files to the user's working directory. If multiple components are needed, create a logical file structure.

After generating, run a quick self-audit against the frontend-design skill's output checklist. **If a UX spec was provided**, additionally verify:
- [ ] Every action in the Action Consequences table has a corresponding UI feedback implementation
- [ ] Every condition in the State Conditions table has a corresponding rendered state
- [ ] Every icon/symbol in the Legend has an accessible Badge variant
- [ ] Responsive specs from Section 7 are reflected in breakpoint usage
- [ ] Cross-screen navigation from Section 3 is reflected in nav structure
