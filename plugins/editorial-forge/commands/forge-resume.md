---
description: Resume an Editorial Forge project where you left off
argument-hint: [project-name]
---

Resume an existing Editorial Forge project.

If `$ARGUMENTS` is provided, search Google Drive for a folder matching that name with " – Editorial Forge" appended. If not provided, search Google Drive for all folders containing "– Editorial Forge" and present the list for the user to choose from.

Once the project folder is identified:

1. Read `00-manifest.json` to get current state.

2. Read `authorship-record.json` to get the decision count and recent activity.

3. Display the project status:
   - Project name and type
   - Current phase and step
   - Authors and voice profile status
   - Chapters/sections progress (X of Y complete)
   - Total editorial decisions logged
   - Last activity timestamp

4. Check `pending_question` in the manifest:
   - If a pending question exists: Re-present it with its full context. Include a brief summary of what was happening when the question was asked.
   - If no pending question: Identify the next action based on current phase and progress. Present it as a clear next step.

5. Ask the user if they're ready to continue, or if they want to see the full status first.

Always orient the user before diving into work. They may not remember where things stood.
