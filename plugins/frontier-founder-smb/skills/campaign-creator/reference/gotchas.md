# Gotchas — campaign-creator

Common failure modes for campaign execution. Good / Bad format.

---

## 1. Generating designs before the calendar is approved

**Bad:** Jumping straight to making post visuals from the brief. The owner then shifts dates and channels, and half the designs are for posts that no longer exist.

**Good:** Lock the calendar at Checkpoint 1 first. Restate the social/email split out loud before generating a single design.

---

## 2. Designing email rows

**Bad:** Making a visual for an email row because it's "content too." Email in FFSMB is plain text the owner sends from their own tool — a design attached to an email row is wasted work and confuses the handoff.

**Good:** Re-check the `Path` column before each design. Email rows get copy only.

---

## 3. Unreadable text over a busy photo

**Bad:** Putting the headline directly on a detailed product photo so the text disappears into the image. Looks fine at full size, illegible in a feed thumbnail.

**Good:** When the design has headline text, keep it on a clean area, a solid band, or a scrim over the photo. Check legibility at thumbnail size before presenting.

---

## 4. Wrong aspect ratio for the channel

**Bad:** One square design reused across Instagram feed, Stories, and an X post. Stories crop the sides; X letterboxes it.

**Good:** Generate per the channel's native ratio — Instagram feed 1:1 or 4:5, Stories 9:16, X/LinkedIn 16:9, Facebook 1:1. If one post spans channels, make the per-channel crops.

---

## 5. Staging a post with a past send time

**Bad:** Copying a scheduled datetime from the brief that has already passed. On some setups the post fires immediately on stage.

**Good:** Confirm every scheduled datetime is in the future before calling `create-or-update-campaign`. If a brief date is in the past, ask the owner for the new date.

---

## 6. Sending instead of staging

**Bad:** Publishing the campaign live at the end of the run.

**Good:** Stage only. The final checkpoint hands control to the owner, who goes live from inside Clarify. Never send without an explicit owner instruction — and even then, the owner does it in Clarify, not this skill.
