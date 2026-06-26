# understand-anything (pointer)

[Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) (Egonex-AI, MIT) analyzes a codebase with a multi-agent pipeline and builds an interactive knowledge graph: every file, function, class, and dependency becomes a node you can search, tour, and explain. It adds diff-impact analysis, guided onboarding tours, business-domain mapping, and a browser dashboard.

## Why this is a pointer, not a vendored build

Unlike ponytail and the impeccable consolidation (pure markdown), Understand-Anything's analysis core is a TypeScript + **native tree-sitter** build (`@understand-anything/core` plus a stack of `tree-sitter-*` grammar packages). All eight skills call into that compiled core at runtime. Re-homing it into this markdown marketplace would either ship slash commands that fail without a build step, or drag a node-gyp/tree-sitter build and its maintenance into the repo. That's the same reason claude-mem's runtime isn't re-homed (DR-011). So this entry documents and points; it does not register the skills.

## Install it upstream (one line)

```
/plugin marketplace add Egonex-AI/Understand-Anything
/plugin install understand-anything
```

Then `/understand` to build the graph, `/understand-dashboard` to explore it, and `/understand-chat`, `/understand-diff`, `/understand-explain`, `/understand-onboard`, `/understand-domain`, `/understand-knowledge` for the rest. First run on a large repo is token-heavy; incremental runs only re-analyze changed files. The graph is JSON you can commit so teammates skip the pipeline.

## When to reach for it vs. what MoxyWolf already has

- **understand-anything** — onboarding and exploration: an interactive dashboard, guided tours, "how does the payment flow work?" chat over the graph. Best when a human needs to *learn* an unfamiliar codebase.
- **graphify** — Obsidian-format knowledge graphs that cross-link with vault notes; communities and god-nodes for architecture analysis.
- **github-repo-analyzer** — health, security-classified issue review, reverse-PRD; runs graphify as its step 0.

They overlap on "graph a codebase" but differ on output (interactive onboarding dashboard vs. vault-native graph vs. health/security report).

## Follow-up

A full native vendor (vendoring `packages/core` + a build/verify pass, dashboard included) is a deferred decision in DR-011. Revisit if the team wants `/understand` available without the upstream install.

## Attribution

Understand-Anything is MIT, Copyright Yuxiang Lin and Infinite Universe, Inc. Full license in `LICENSE`.
