---
description: SM-004. Capture this session with code, review what the code wrote, and propose; never promote. Publishing is a separate, confirmed step.
---

Review this session from its captured record, not from memory.

Everything runs through `scripts/session_record.py` in this plugin. Your own reasoning is never captured: the script drops it before it reads a line.

1. **Capture.** The `UserPromptExpansion` hook already recorded this session's identity and where the file ended when you typed this. Run
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_record.py" capture --from-hook <session_id>`
   with the session ID from your environment. Report the completeness it prints, in its own words ("source capture complete through line N", or `partial` with each reason). If this session was already captured, it verifies that frozen capture and prints `"reused": true` with the line it ends at: say plainly that this review covers the session only up to that line, then carry on; a capture is never replaced. If it refuses, say why and stop.
2. **Build the review prompt.** `session_record.py review-prompt --capture <capture dir>`. It prints the prompt, and `prompt_sha256=<hash>` on stderr; keep the hash. If it says the session file was picked by guess, ask the person to confirm it before going on. The captured text arrives inside TB-002's untrusted enclosure, with its rule.
3. **Review.** Follow that prompt. Read only the manifest, `evidence.jsonl` and `record.md` it carries. Write `review.md`, `decisions.jsonl`, `proposals.jsonl` and `observed.jsonl` into a new draft folder in staging. Cite events as `ev:<event_id>`. Set no verification status: code does that.
4. **Finalize.** `session_record.py review-finalize --capture <dir> --draft <draft> --prompt-sha256 <hash> --tool claude --model <model> --family anthropic` (add `--repo OWNER/NAME=PATH` for each local clone a commit might be in). It checks every section has content and each cites an event or says there's nothing to report, validates every citation and proposal field, adds the one-line no-promotion rule, resolves every identifier you observed, and freezes the review. A validation failure is reported, not fixed silently.
5. **Report.** Summarize `review.md` in a few lines, list the proposals for Dorian, and say where the review sits in staging. Say plainly that nothing was promoted and nothing was published.

**Publishing** is only on the person's word, after they've seen the exact files: `publish-prepare --capture <dir> --review <review dir> --audience <who>` needs a valid review of that capture and shows the files, the audience, any binary exceptions, the scanner and the approval digest that binds them all; `publish --confirm <approval digest> --confirmed-by <login> --dest <Taskade folder>` needs gitleaks, refuses on any finding, and never writes into a Git repository.

**In a cloud session** (goal cloud-review-survives) staging lives in the session's container, which is deleted when the session ends, and this review goes with it. To keep it, publish it, still only on the person's word: `publish-prepare`, show them the files, then `publish --confirm <digest> --confirmed-by <login> --dest <a folder in the session workspace>`. Then copy the published folder, whole and unchanged, into the project's vault folder `11-Knowledge/session-records/` through the linked computer (for example as one tar file written there and unpacked in place), and run `python3 <the plugin's scripts>/session_record.py read <that copy>` on the linked computer. Report the header `read` printed and the copy's vault path; a refusal is reported as it stands, and the copy isn't kept as the record. When no computer is linked, say plainly that the review stays in this session and is lost when it ends. Don't copy it anywhere else.

The person records their own judgment of the review with `session_record.py examine`. Publishing never does it for them.
