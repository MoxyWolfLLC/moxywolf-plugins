# Clarify campaign staging reference

How `campaign-creator` stages social posts in Clarify, and the CSV fallback when the owner doesn't want to stage in Clarify.

## Tools

Clarify's MCP exposes campaigns directly:

- `create-or-update-campaign` — create a new campaign or update an existing one (name, dates, and the posts/messages it contains). This is the primary staging call.
- `get-campaigns` — list campaigns or fetch one by ID with full details, to confirm what's queued.

Always read the live shape with `get-schema` (campaign/message entity) before writing, so you set the fields the workspace actually expects rather than assuming names.

## Staging flow

1. **Create the campaign.** `create-or-update-campaign` with the campaign name and start/end dates from the approved calendar.
2. **Add each social post** as a scheduled item under the campaign:
   - channel (map the calendar channel to the owner's connected social account)
   - scheduled datetime — ISO 8601; confirm it's in the future before writing
   - body — the approved caption from Stage 3
   - attachment — the claude.ai/design visual chosen in Stage 2
   - status — scheduled, never sent/published
3. **Confirm.** `get-campaigns` to read the queue back; surface the list and link the owner to the campaign view in Clarify.

## Approval discipline

- Stage only. Never trigger an immediate send — the owner controls go-live from inside Clarify.
- Confirm every scheduled datetime is in the future; a past datetime can fire immediately on some setups.

## CSV fallback (no Clarify staging)

If the owner doesn't use Clarify for social scheduling, export a CSV instead of calling the campaign tools:

```
date,channel,scheduled_time,caption,image_path
2026-06-02,instagram,2026-06-02T09:00:00,"finally, a dress…",designs/jun02-linen.png
```

The owner imports this into whatever scheduler they use (Buffer, Later, native platform schedulers). Hand off the CSV plus the design files together.
