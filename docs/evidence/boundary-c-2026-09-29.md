# B-c: what SM-004's hooks actually see (headless run)

**Date:** 2026-09-29 · **Claude Code:** 2.1.268 on Dorian's Mac · **Harness:** `~/bc-spike` (throwaway, outside every repo) · **Session:** `f8f6adec`, three `claude -p` turns: fixtures, `/compact`, `/bc-spike:session-review`.

The probe drops reasoning blocks before it reads a line and never counts them.

| # | Question | Answer from this run |
|---|---|---|
| 1 | Is the `/session-review` line in the file when `UserPromptExpansion` fires? | **No.** A `queue-operation` line naming the command is there (line 65). The `user` line carrying the command (line 67) is written after the hook fires. |
| 2 | How does `prompt_id` appear in the file? | As `promptId` on `user` lines only, the prompt line and its tool results. Assistant lines don't carry it, so a turn is "from its `promptId` user line to the next prompt's". |
| 3 | How do several text blocks become `last_assistant_message`? | It's the **last assistant line's text**, not the turn's. Here each assistant line held one text block, so the join rule inside one line is still unproven. **The final assistant line was not yet in the file when `Stop` fired**, in both turns. |
| 4 | Does compaction rewrite earlier lines? | **Append only.** 14 snapshots of the main file, including before and after `/compact`, are all byte prefixes of the final file. |
| 5 | Does `Stop` finish before the next expansion fires? | Yes here, but trivially: separate headless processes. The interactive run tests a queued prompt. |
| 6 | How does `StopFailure` affect the last turn? | Not observed. It needs an API error mid-turn. |
| 7 | Are sub-agent files and attachments readable at capture? | The sub-agent transcript is under `<session>/subagents/` and readable. The compaction agent's transcript path was named but **never written**. A 132 KB tool output was stored as `<session>/tool-results/*.txt`, readable. Attachments appear as `attachment` lines (14 kinds, including `file`). |
| 8 | Can a plugin hook write to owner-only staging? | Yes. 16 events written to `~/.moxywolf/session-staging/bc-spike/<session>` at `0700`, no hook errors. |

## What this changes in SM-004

- **The matcher.** `command_name` arrives namespaced: `bc-spike:session-review`. The literal matcher `session-review` did **not** fire; `.*session-review` did. Criterion 2 has to match `project-init:session-review`.
- **The capture boundary (criterion 2).** At expansion, the command's own user line isn't in the file yet, so "capture up to the lines that exist at expansion" already excludes the `/session-review` turn. The `queue-operation` line before it must be excluded too.
- **Finality (criterion 3).** `Stop` fires before the final assistant line lands. Hashing `last_assistant_message` at `Stop` is right, and the capture must poll for that line, which criterion 3's 2-second stability wait covers.
- **Evidence scope.** Sub-agent transcripts and large tool outputs live in a folder beside the session file, not in it. Capture has to include `<session>/subagents/` and `<session>/tool-results/`, or say it didn't.

Not yet covered: a real dragged-in attachment, a prompt queued while a turn runs, a multi-block assistant line, `StopFailure`, and Cowork (this was the Claude Code CLI). `~/bc-spike/RUN.md` covers the first three.

## Interactive run (Dorian, session `8791b012`, 26 hook events)

Same answers as the headless run, plus what only a live session could show:

- **A queued command waits for the `Stop` hook.** `/bc-spike:session-review`, typed during the lighthouse turn, sat as a `queue-operation` line (87). Its expansion fired 0.13 s after the turn's `Stop` hook finished, and that hook sleeps 3 s on purpose. Every `Stop` in the session finished before the next prompt hook started.
- **`last_assistant_message` is the last assistant line's text, not the turn's.** The lighthouse turn wrote three text lines; the hook got only the third. Every assistant line in both runs held one text block, so Claude Code appears to write one line per block. The join rule inside a line is moot until a multi-block line turns up.
- **Finality, confirmed seven times out of seven.** The final assistant line wasn't in the file when `Stop` fired, in every turn.
- **The dragged-in image is stored inline.** The user line (53) carries it as a base64 `image` block, all 99 bytes. A copy also sits under `~/.claude/image-cache/<session>/`. It's not a `file` attachment line.
- **Compaction, again, only appended.** 25 snapshots, all byte prefixes of the final file.
- **Most `SubagentStop` events have no transcript.** Five fired; only the Task sub-agent (`general-purpose`) wrote its file. Four with an empty `agent_type` name a path that was never created. Capture has to treat a missing sub-agent file as expected, not as loss.
- **A second `/session-review` sees the first.** At the second expansion, the first `/session-review` turn (lines 98 to 103) is already in the file. SM-004's boundary has to exclude earlier review turns, or record them as reviews.

Still not observed: `StopFailure` and Cowork.
