---
description: Set up a new Cowork project — confirm the roots it needs (Vault and GitHub; Taskade only for a personal project), gather the active Taskade and GitHub subfolders, generate tailored Project Instructions
---

Run the project-init skill to initialize a new Cowork project.

**Load the standing operating rule first.** Read the canonical verification
guidance at `gstack-execution/skills/gstack-execution/references/verification-checks.md`
from the resolved gstack-execution installation, or from
`plugins/gstack-execution/skills/gstack-execution/references/verification-checks.md`
in an available moxywolf-plugins checkout. Apply its "Standing operating rule:
verify before recommending commitment" throughout initialization. Installation
alone is not proof it was loaded; if neither source can be read, report
`Standing operating rule: not loaded` and do not claim it was applied. Do not
install or reconfigure plugins as part of this read.

When generating new Project Instructions, include a reference to this canonical
guidance and require it to be read at session start; do not duplicate its text.
Preserve the skill's existing-project guard and the canonical template structure.

The skill assumes these MoxyWolf roots are mounted in Cowork → Folders:

1. **MoxyWolf Vault**
2. **GitHub**
3. **Taskade** (personal Taskade projects only; org-shared and vault-only projects don't need it)

It then:

1. Asks for the project name
2. Asks whether the project is shared with the organization. **Org-shared projects live in `GitHub/Projects/<NAME>/`** (the `MoxyWolfLLC/Projects` repo, scaffolded from `Directory Template`) and never get stored in Taskade; the new folder is committed, pushed and pulled back. Personal projects get a Taskade subfolder picked with the **native Finder picker** (no typing); vault-only projects use `MoxyWolf Vault/Projects/<NAME>/`
3. Asks how many GitHub repos this project uses, then opens the **native Finder picker** once per repo so the user can select each repo subfolder under `GitHub/` (no typing). Asks for a one-line description per repo.
4. Asks which `#project/…` scope(s) the project's tasks carry on the team Jira board (MOXY) — and the exact Jira label(s) those issues carry on MOXY, stored as written (or `none`)
5. Reads the canonical template from `MoxyWolf Vault/_Templates/Cowork Project Instructions Template.md`
6. Substitutes placeholders (`[PROJECT_NAME]`, `[TASKADE_SUBFOLDER]`, `[REPO_SUBFOLDER]`, `[KANBAN_SLUG]`) with the user's answers
7. Saves the filled-in Project Instructions to the project's `00 – Project Hub/` folder
8. Displays the result for the user to paste into Cowork's Project Instructions field
9. Reminds the user to mount any root this project needs that isn't already mounted

If the user passed arguments after `/init-project`, treat them as a project name hint but still confirm interactively. Otherwise invoke the project-init skill which collects all required information through AskUserQuestion.
