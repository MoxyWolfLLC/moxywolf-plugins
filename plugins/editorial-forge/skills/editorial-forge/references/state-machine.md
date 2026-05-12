# State Machine & Resume Logic

How Editorial Forge persists state across sessions and resumes work after asymmetric Q&A delays.

## Project Manifest Schema

Located at `00-manifest.json` in the project root (Google Drive).

```json
{
  "project_name": "Project Name",
  "project_type": "book|strategy|single-piece",
  "created": "ISO-8601",
  "last_activity": "ISO-8601",
  "authors": [
    {
      "name": "Author Name",
      "voice_profile": "voice-profiles/author-name.md",
      "role": "primary_author|contributing_author|editor"
    }
  ],
  "environment": {
    "ai_model": "claude-opus-4-6",
    "ai_model_version": "version-string",
    "plugin": "editorial-forge",
    "plugin_version": "0.1.0"
  },
  "current_phase": "setup|intent|structure|voice|writing|verification|complete",
  "current_chapter": null,
  "current_step": null,
  "pending_question": null,
  "progress": {
    "intent": "not_started|in_progress|complete",
    "intent_questions_answered": 0,
    "structure": "not_started|in_progress|complete",
    "voice_profile": "not_started|in_progress|complete|imported",
    "throughline": "not_started|complete",
    "chapters_total": 0,
    "chapters_complete": 0,
    "chapters_in_progress": 0,
    "editorial_decisions_logged": 0,
    "verification": "not_started|complete"
  }
}
```

## Phase Transitions

```
setup → intent → structure → voice → writing → verification → complete
```

Each transition requires:
- All questions in the current phase answered
- Author confirmation to proceed
- Manifest updated with new phase

Phases cannot be skipped. However, within `writing`, chapters can be done in any order.

## Pending Question Schema

When a question is asked and the session may end before the answer arrives:

```json
{
  "pending_question": {
    "id": "unique-question-id",
    "phase": "intent|structure|voice|writing",
    "chapter": "ch-03-slug",
    "step": "dob_mapping|voice_qa|refinement",
    "question_number": 2,
    "total_questions": 5,
    "text": "The full question text as presented to the author",
    "context": "What we were doing, what we've already collected, what comes next after this answer",
    "asked_at": "ISO-8601"
  }
}
```

## Resume Logic

When the user says "pick up where we left off," "forge-resume," or references an existing project:

1. **Find the project**: Search Google Drive for `name contains '[Project Name] – Editorial Forge'`
2. **Read the manifest**: Fetch `00-manifest.json`
3. **Check for pending question**: If `pending_question` is not null:
   - Re-present the question with its context
   - Include a brief summary of progress so far
   - Example: "Last time we were working on Chapter 3's DOB mapping. I'd asked you about [question]. You've completed 2 of 12 chapters so far with 47 editorial decisions logged. Ready to pick this up?"
4. **If no pending question**: Identify the next action based on `current_phase` and `progress`
5. **Display status**: Always show a brief progress summary on resume

## Initialization Sequence (Phase 0)

When starting a new project:

1. Ask: "What are we building?" → Book / Strategy Document / Single Piece
2. Ask: "What's the project name?"
3. Ask: "Who are the authors?"
4. Ask: "Is there existing AI-generated content to start from? If so, where?"
5. Create the Google Drive folder structure based on project type:

### Book Template
```
[Project Name] – Editorial Forge/
├── 00-manifest.json
├── 01-intent/
├── 02-structure/
│   └── source-material/
├── 03-chapters/
├── voice-profiles/
└── authorship-record.json
```

### Strategy Document Template
```
[Project Name] – Editorial Forge/
├── 00-manifest.json
├── 01-intent/
├── 02-structure/
│   └── source-material/
├── 03-sections/
├── voice-profiles/
└── authorship-record.json
```

### Single Piece Template
```
[Project Name] – Editorial Forge/
├── 00-manifest.json
├── 01-intent/
├── 02-structure/
│   └── source-material/
├── 03-draft/
├── voice-profiles/
└── authorship-record.json
```

6. If source material exists, copy/ingest it into `02-structure/source-material/`
7. Initialize `authorship-record.json` with project metadata and empty decisions array
8. Initialize `00-manifest.json` with `current_phase: "intent"`
9. Immediately ask the first intent question (The Thesis)

## Status Display Format

When showing project status (via `/forge-status` or on resume):

```
📘 [Project Name] — Editorial Forge
Phase: [Current Phase] | Step: [Current Step]
Authors: [Names]
Progress: [X]/[Y] chapters complete | [N] editorial decisions logged
Voice: [Status]
Pending: [Question summary or "No pending questions"]
Next: [What happens next]
```

## Error Recovery

If the manifest or authorship record is missing or corrupted:
- Check if the folder structure exists — if so, rebuild manifest from folder contents
- Check for partial files — resume from last complete state
- Never silently skip a phase — always inform the author what was recovered and what may need to be re-done
- If truly unrecoverable, offer to start fresh with a new project folder (preserving the old one)
