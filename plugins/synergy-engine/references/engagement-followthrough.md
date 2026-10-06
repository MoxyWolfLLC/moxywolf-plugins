---
read_when: "synergy-run, after a comment posts and on every later tick that finds a reply; synergy-discover, when mining who engaged with an on-theme post."
status: canonical
---

# Engagement follow-through

A comment is the start of a conversation, not the end of a task. These rules cover what happens after ours posts. The ideas come from sergebulaev/linkedin-skills (MIT), re-expressed for this engine; no code was copied, and anything there that conflicts with our voice or send rules was left out.

## The warm-reply window

When the post's author replies to our comment, that reply is the warmest moment the target will ever give us. Answer it while it's warm.

| Time since the author replied | Read it as | Do |
|---|---|---|
| Under 2 hours | Hot | Reply on the next run. Put it at the top of the batch. |
| 2 to 24 hours | Warm | Reply on the next run. |
| 24 to 72 hours | Cooling | Reply only if there's something new to add. |
| Over 72 hours | Dormant | Don't reply in the thread. If the target isn't a connection, the connect note per cadence is the next touch. Never a DM: non-connections can't be free-messaged (`outreach-channels.md` Part 2). |

Log the author's reply as `Status = Replied`, with the reply time in Notes and the reply move in Next Action, so `/synergy-status` shows it as due.

## Threading

LinkedIn threads one level deep. A reply to a reply still attaches to the top-level comment. When answering someone inside a thread, open the reply box on the top-level comment and name the person you're answering in the first line. Replying anywhere else drops the answer out of the thread they'll see.

## The new-noun check

Every comment and every reply carries at least one noun or concept the post and thread don't already have. A figure, a named framework, a case, a tool. Agreement with nothing added reads as hovering, and it's the first thing a reader skips. If the draft can't pass this, don't post it.

## Mining who engaged

The people reacting to and commenting on an on-theme post are often better targets than its author: they've already raised a hand on the topic. When `/synergy-discover` finds a high-synergy post, it can pull its engagers with the Apify actors `harvestapi/linkedin-post-reactions` and `harvestapi/linkedin-post-comments`, then sort them into three tiers:

- **Peer**: same field and level as us. Comment-first, same as an author target.
- **Aspirational**: a bigger voice in the field. Comment on their own posts for a while before any connect.
- **Prospect**: matches the persona fit in the fingerprint. Comment-first, then the connect note.

Every tier goes through the same comment-first cycle and cadence. Wait 24 to 72 hours after their engagement before our first touch, so it doesn't read as surveillance. Dedupe them against the tracker like any other target, and log them with the post they engaged on in Notes.
