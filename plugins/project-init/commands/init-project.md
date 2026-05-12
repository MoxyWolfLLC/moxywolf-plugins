---
description: Set up a new Cowork project — confirm the three standard roots, gather the active Taskade and GitHub subfolders, generate tailored Project Instructions
---

Run the project-init skill to initialize a new Cowork project.

The skill assumes the three standard MoxyWolf roots are mounted in Cowork → Folders:

1. **MoxyWolf Vault**
2. **GitHub**
3. **Taskade**

It then:

1. Asks for the project name
2. Opens the **native Finder picker** so the user can select the active Taskade subfolder (no typing) — or marks the project as vault-only
3. Asks how many GitHub repos this project uses, then opens the **native Finder picker** once per repo so the user can select each repo subfolder under `GitHub/` (no typing). Asks for a one-line description per repo.
4. Reads the canonical template from `MoxyWolf Vault/_Templates/Cowork Project Instructions Template.md`
5. Substitutes placeholders (`[PROJECT_NAME]`, `[TASKADE_SUBFOLDER]`, `[REPO_SUBFOLDER]`) with the user's answers
6. Saves the filled-in Project Instructions to the project's `00 – Project Hub/` folder
7. Displays the result for the user to paste into Cowork's Project Instructions field
8. Reminds the user to mount any of the three standard roots that aren't already mounted

If the user passed arguments after `/init-project`, treat them as a project name hint but still confirm interactively. Otherwise invoke the project-init skill which collects all required information through AskUserQuestion.
