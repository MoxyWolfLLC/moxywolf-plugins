# The approval batch

One message a day, at the configured approval time (10:15 Pacific by default). It holds every outward action planned for the day. Dorian answers it once. Nothing outward happens without his decision on that exact item.

## Building it

```
python3 "$P/scripts/batch_ledger.py" new --ledger-dir "$LEDGER_DIR" --config "$CFG"
python3 "$P/scripts/batch_ledger.py" add --ledger "$L" --kind comment --lane C \
  --args '{"entity_urn": "urn:li:activity:7390000000000000000", "text": "..."}' \
  --target '{"name": "Jane Roe", "identifier": "janeroe", "url": "https://www.linkedin.com/feed/update/urn:li:activity:7390000000000000000/"}' \
  --reason "On fingerprint: STIG drift post, 40 comments, author runs a GRC tool" \
  --sources "https://www.linkedin.com/feed/update/urn:li:activity:7390000000000000000/" --config "$CFG"
python3 "$P/scripts/budget_check.py" --live --config "$CFG" --ledger "$L" --json > budget.json
python3 "$P/scripts/batch_ledger.py" render --ledger "$L" --budget budget.json
python3 "$P/scripts/batch_ledger.py" present --ledger "$L"
```

`P` is the plugin root (`${CLAUDE_PLUGIN_ROOT}`), `CFG` the config, `L` today's ledger file. One ledger per day; `new` refuses a second.

`add` refuses: an unknown kind or parameter, a Lane A connect or DM while Lane A is held, a suppressed person, another account, an em dash, an unfilled `{{placeholder}}`, a connection note over 200 characters or with a link, a comment over 1,200 characters, a post over 2,900. It warns (the warning shows in the batch) on craft ranges, hashtags in comments, links in a post body, and booking links in a DM.

If `budget_check.py` reports over budget, cut the lowest-ranked items before presenting with `batch_ledger.py drop --items <n,...> --why "<reason>"`. Never present a batch the day can't carry.

## What Dorian sees

`render` produces this shape. Sections appear only when they have items.

```
# LinkedIn batch 2026-11-10 for Dorian Cougias

7 items waiting. Reply `approve all`, or per item `approve 3`, `edit 4: <new text>`, `strike 5`. Nothing goes out without your decision.

| Bucket | Plan left | Ceiling left |
|---|---|---|
| comment_posts | 5 | 5 |
| send_connection_requests | 4 | 4 |

## Engagement (10:30)

**001. reaction** (Lane C) Jane Roe <https://www.linkedin.com/feed/update/urn:li:activity:.../>
Why: On fingerprint: STIG drift post, 40 comments
Reaction: insightful

**002. comment** (Lane C) Jane Roe <https://www.linkedin.com/feed/update/urn:li:activity:.../>
Why: On fingerprint: STIG drift post, 40 comments, author runs a GRC tool
Text (214 chars):
> ...
Sources: https://www.linkedin.com/feed/update/urn:li:activity:.../

## Publish (12:00)
## Network and outreach (13:00)
## Inbox hand-backs (15:00)
```

## Dorian's answers

| He says | Record it as |
|---|---|
| `approve all` | `decide --items all --decision approve` |
| `approve 1,2,5` | `decide --items 1,2,5 --decision approve` |
| `edit 4: <new text>` | `decide --items 4 --decision edit --text "<new text>"` |
| `strike 3` | `decide --items 3 --decision strike` |
| anything unclear | ask him; don't guess a decision |

Every `decide` names `--approver "Dorian Cougias" --initials DC`. The ledger refuses any other approver, a vague one ("me", "the team", "Amos"), or a decision on a batch that wasn't presented. Response time is measured from `present` to `decide`, so record the decision when he gives it, not later.

An edit re-runs the text checks. An edited item executes with the edited text, and the ledger keeps the original.

## Rules that keep the gate real

- One batch, one decision per item. The operator never decides for Dorian, and no one approves on his behalf.
- An approval is for today only. Tomorrow's run won't execute yesterday's items.
- A change to an approved item's arguments, for any reason, voids the approval (the hash check in `verify_for_execution`).
- Urgent same-day items (a golden-hour reply, an inbound that can't wait) go into today's ledger as new items and get their own quick decision. They don't ride on an earlier "approve all".
- After the decisions, write the gate log (`batch_ledger.py gate-log`), one row per decided item, struck items included.

## Watching the override rate

`batch_ledger.py stats --ledger-dir "$LEDGER_DIR"` reports, over the last 30 days, how often Dorian edits or strikes, and his median time to decide. It flags `RUBBER-STAMP?` when he overrides under 10% of 5 or more items, and `TOO-FAST?` when the median time to decide a batch works out to under 20 seconds per item in it (a 10-item batch decided in under 200 seconds). The fleet's `override_report.py` applies its own 20-second median per decision to the gate-log rows. The weekly report shows both. A flag isn't a failure; it's a prompt to look at whether the drafts are good or the gate has gone soft.
