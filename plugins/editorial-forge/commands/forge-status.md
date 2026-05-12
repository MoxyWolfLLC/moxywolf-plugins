---
description: Show current status of an Editorial Forge project
argument-hint: [project-name]
---

Display the current status of an Editorial Forge project.

If `$ARGUMENTS` is provided, search Google Drive for that project. If not provided, search for all Editorial Forge projects and let the user choose, or show all if there are 3 or fewer.

For the selected project, read `00-manifest.json` and `authorship-record.json`, then display:

```
📘 [Project Name] — Editorial Forge
Type: [Book / Strategy Document / Single Piece]
Phase: [Current Phase] | Step: [Current Step]
Authors: [Names and roles]

Progress:
  Intent:     [complete / X of 5 questions answered]
  Structure:  [complete / in progress / not started]
  Throughline: [complete / not started]
  Voice:      [complete / imported / in progress / not started] for each author
  Chapters:   [X] of [Y] complete, [Z] in progress
  Decisions:  [N] editorial decisions logged

Pending: [Full pending question text, or "No pending questions"]
Last Activity: [timestamp and what was done]
Next Action: [Clear description of what happens next]
```

If the user asks for more detail on the authorship record, show the 10 most recent decisions with timestamps, types, and descriptions.
