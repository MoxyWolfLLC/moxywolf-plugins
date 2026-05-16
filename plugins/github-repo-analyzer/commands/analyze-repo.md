---
description: Analyze a GitHub repo for health, quality, and stack conformance
argument-hint: <github-url> [--quick]
---

Analyze the GitHub repository at $1 and produce a structured health report.

## Steps

1. Parse the repo URL from `$ARGUMENTS`. Extract the owner and repo name. If `--quick` is present, set analysis depth to `quick`; otherwise use `deep`.

2. Read the skill file at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/SKILL.md` to load the full analysis workflow and report structure.

3. Gather the repo data directly. Pick one of two paths:

   **Path A — Local clone (preferred for `deep` analysis):**

   ```bash
   WORK=$(mktemp -d)
   cd "$WORK"
   gh repo clone "${OWNER}/${REPO}"
   cd "${REPO}"
   ```

   Then walk the working tree with `Glob` and `Read` against the cloned path to inspect package manifests, configs, code samples, and docs.

   **Path B — REST API (good for `quick` analysis or when cloning isn't possible):**

   - Native GitHub MCP `list_branches` for branch inventory.
   - `gh api "/repos/${OWNER}/${REPO}"` for repo metadata.
   - `gh api "/repos/${OWNER}/${REPO}/git/trees/${DEFAULT_BRANCH}?recursive=1"` for the full file tree.
   - `gh api "/repos/${OWNER}/${REPO}/contents/${PATH}"` for individual file content (returns base64; decode with `jq -r .content | base64 -d`).
   - `gh api "/repos/${OWNER}/${REPO}/contributors"` for contributor patterns.

   Use `quick` mode when `--quick` is set: only inspect root-level files (package.json, README, top-level configs) and skip recursive tree walks.

4. Read the approved tech stack from `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/tech-stack.md`.

5. Compare detected technologies against the approved stack. For each layer (Frontend, Backend, Database, Hosting, etc.), mark technologies as:
   - **Match** — technology is on the approved list
   - **Deviation** — technology serves a similar purpose but differs from the approved choice
   - **Missing** — expected technology from the stack is absent
   - **Addition** — technology not in the approved stack (flag for review)

6. Compile the full health report as Markdown covering all sections defined in the skill (Repository Overview, Architecture, Tech Stack Inventory, Stack Conformance, Code Quality, Dependency Health, Contributor Health, Documentation, Security Posture, Tech Debt, Recommendations).

7. Save the report as a `.md` file named `{repo-name}-health-report.md` and provide it to the user.
