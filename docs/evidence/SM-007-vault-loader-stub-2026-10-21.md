# SM-007 criterion 7: the vault loader-stub spec names the Project fallback

Edited 2026-10-21 by Claude in the MoxyWolf LLC Cowork session, on Dorian's choice ("Do the vault edit now").

File: `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/project-instructions-loader-stub.md`
`spec_version`: 6 → 7
sha256 (first 16) after the edit: `c058a283a0efc28a`

Line added in section 1 (Taskade-based loader stub), directly after "`/session-start` loads both automatically…", quoted verbatim:

> No Taskade mount (a scheduled run, a phone or web session, a Mac that's asleep), or a read that fails: read the same three files, plus `cowork-session-handoff.md`, from the attached claude.ai Project with `project_read` at the same relative path; they're mirrored there by `/session-end` and `/refresh-project-instructions` (SM-007). Disk wins when both are readable; never write a Project copy back to disk.

The per-project `/refresh-project-instructions` run that re-stamps each project's stub against spec_version 7 is not done here; it is one command per project and is recorded as a follow-up in DESIGN.md SM-007.
