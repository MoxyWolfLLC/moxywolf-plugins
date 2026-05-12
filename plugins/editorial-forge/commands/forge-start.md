---
description: Initialize a new Editorial Forge authoring project
---

Start a new Editorial Forge project. Ask the following setup questions one at a time using AskUserQuestion:

1. "What are we building?" — Options: Book (multi-chapter), Strategy Document (structured sections), Single Piece (article, whitepaper, guide)

2. "What's the project name?" — Free text. This becomes the Google Drive folder name as "[Project Name] – Editorial Forge"

3. "Who are the authors?" — Names and roles (primary author, contributing author, editor). There must be at least one primary author.

4. "Is there existing AI-generated or co-created content to start from? If so, where can I find it?" — Could be Google Drive links, file paths, or "I'll add it later"

After collecting answers:

1. Create the Google Drive project folder using the appropriate template from `references/state-machine.md` based on project type.

2. Initialize `00-manifest.json` with project metadata, authors, current phase set to "intent", and empty progress fields.

3. Initialize `authorship-record.json` with project metadata, environment block (capture current AI model, version, plugin version, all active tools), and empty decisions array.

4. If source material was provided, ingest it into `02-structure/source-material/`.

5. Check if any named author already has a voice profile from a previous project. If found, note it for Phase 3.

6. Immediately begin Phase 1 (Intent Mapping) by asking the first intent question: "What does this work argue? Not what it covers — what it *argues*. Complete this sentence: 'After reading this, the reader will believe _____.'"

7. Log a `project_initialized` decision in the authorship record.

Display the project status summary after initialization is complete.
