# cloud-review-survives
1. Add the read command
   - `session_record.py read <published folder>` checks the folder against its `hashes.sha256`, with no file added, missing or changed, and checks that its `publish-receipt.json` names the publication and the person who confirmed it
   - when both checks pass it prints the review's `review.md` and a header naming the session, the publication, the audience and who confirmed it, and exits 0, with no staging folder present
   - when either check fails, or the folder isn't a published folder, it prints `refused: <reason>` on standard error, exits 2, and prints none of the review on standard output
   - it writes nothing, so it works on a read-only copy
2. Say how a cloud session's review reaches the vault
   - `/session-review` and `/session-end` say that in a cloud session, after Dorian confirms publishing, the agent publishes into the session workspace, copies the published folder into the project's vault folder `11-Knowledge/session-records/` through the linked computer, and runs `read` on that copy there
   - they say what to report when no computer is linked: the review stays in the session and is lost when it ends
   - the handoff names the vault path of the copy
