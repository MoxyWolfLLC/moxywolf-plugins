# Lanes

Every batch item names its lane. The lane decides what kinds of actions are allowed and which sequence the person is on.

| Lane | Who | Goal | Allowed now | Sequence |
|---|---|---|---|---|
| A. Integration partners | GRC, SecOps and AI-governance tool builders (the STIGViewer integration campaign) | Co-build conversations | Engagement only: reaction, comment, repost, visit | Partner, once released |
| B. OpenControls prospects | Compliance and control-mapping buyers | Discovery calls | All kinds, after an engagement signal | Prospect |
| C. Discourse and authority | People writing about STIGs, control mapping, AI governance; authors Dorian cited | Reach and credibility | Reaction, comment, repost; connect only with a real reason | None by default |
| D. Inbound warmth | Profile viewers, post engagers, new followers, inbound invites | Turn warmth into conversations | Accept, ignore, reply, thank-you DM | Inbound |
| OWN | Dorian's own posts and the replies on them | Publish and golden-hour replies | Post, first comment, comment replies | None |

## Lane A is on hold

The partner campaign is held until Dorian releases it. While `lanes.A.mode` is `engagement-only` (the default), `batch_ledger.py add` refuses any connection request or DM in Lane A. To release it, Dorian sets `lanes.A.mode` to `full-outreach` through `/li-setup`. Nobody else changes that field, and the change is worth a gate-log row of its own.

## Picking the lane

- Has this person or their company come up in the partner list or the STIGViewer campaign? Lane A, even when the signal looks like a prospect signal.
- Do they buy or run compliance and control mapping? Lane B.
- Are they writing in the discourse without a buying role? Lane C.
- Did they come to Dorian first (viewed, reacted, followed, invited, messaged)? Lane D, until they reply, then the lane that fits who they are.

When a person fits two lanes, the stricter one wins (A over B, B over C).

## Keywords

Each lane's keywords live in the config (`lanes.<X>.keywords`) and feed the signal sweep's post search. Score results against the synergy-engine topic fingerprint when it exists (`synergy-engine` plugin, `/synergy-fingerprint`), so a keyword match on an off-topic post doesn't make the list.
