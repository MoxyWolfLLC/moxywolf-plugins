---
description: Reverse-engineer a PRD from a GitHub repository
argument-hint: <github-url> [--quick]
---

Analyze the GitHub repository at $1 and reverse-engineer a Product Requirements Document (PRD) alongside a full health report.

## Steps

1. Parse the repo URL from `$ARGUMENTS`. Extract the owner and repo name. If `--quick` is present, set analysis depth to `quick`; otherwise use `deep`.

2. Read the skill file at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/SKILL.md` to load the full analysis workflow, report structure, and PRD generation guidelines.

3. Gather the repo data directly — same two paths as `/analyze-repo`:

   **Path A — Local clone (preferred for `deep` PRD reverse-engineering):**

   ```bash
   WORK=$(mktemp -d)
   cd "$WORK"
   gh repo clone "${OWNER}/${REPO}"
   cd "${REPO}"
   ```

   Then walk the working tree with `Glob` and `Read` to extract architectural patterns, data models, integrations, workflows, and naming conventions. PRDs need the broader picture — favor the local clone unless `--quick` is set.

   **Path B — REST API (only when `--quick` is set or cloning isn't possible):**

   - `gh api "/repos/${OWNER}/${REPO}"` for repo metadata
   - `gh api "/repos/${OWNER}/${REPO}/git/trees/${DEFAULT_BRANCH}?recursive=1"` for the file tree
   - `gh api "/repos/${OWNER}/${REPO}/contents/${PATH}"` for individual files
   - Native GitHub MCP `list_branches` and `list_repos` for context

   The PRD generation step in this command requires deep file reading (data models, API contracts, business logic). If using Path B in `--quick` mode, scope the PRD to architectural sections and explicitly mark the rest as "Requires stakeholder input" — don't pretend deep insight from shallow data.

4. Read the approved tech stack from `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/tech-stack.md`.

5. Read the PRD template from `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/prd-template.md`.

6. Read the PRD assessment rubric from `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/prd-assessment-template.md`.

7. Generate the health report following the same process as `/analyze-repo` (all sections including stack conformance).

8. Generate the PRD using the template structure. For each of the 17 sections:
   - Fill in details that the codebase provides evidence for (architecture, tech stack, integrations, data models, workflows)
   - Mark sections requiring business context (personas, KPIs, pricing, roadmap dates) as **"Requires stakeholder input"** with guidance on what to fill in
   - Include relevant code references where they support PRD claims

9. Assess the generated PRD using the assessment rubric. Produce a completeness scorecard showing which sections are fully populated, partially populated, or need stakeholder input.

10. Save two files:
    - `{repo-name}-health-report.md` — the full health report
    - `{repo-name}-prd.md` — the reverse-engineered PRD with assessment scorecard appended

Provide both files to the user.
