---
description: Set up a new Cowork project — confirm the roots it needs (Vault and GitHub; Taskade only for a personal project), gather the active Taskade and GitHub subfolders, generate tailored Project Instructions
---

Run the project-init skill to initialize a new Cowork project.

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
