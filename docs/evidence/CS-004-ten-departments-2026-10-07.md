# CS-004: three places outside this repository brought to ten departments, 2026-10-07

Dorian asked for every document to say ten departments, the Commitment calendar included (CS-004 criterion 10 as amended). Three things outside this repository said eight. This file records what changed in each, written by the agent that made the changes. It is the builder's record, not a reviewer's.

The bookkeeper's name is on the context card and nowhere in this repository, so the card's changed lines are described here and not quoted.

## 1. The Commitment calendar scheduled task (`trig_01CE1aPat8HBa3X5WHX242KU`)

Two sentences of the prompt changed. Nothing else did: the schedule, the connectors, the delivery and the rule that the calendar is a sensor that dispatches nobody are as they were.

Before:

```text
DEPARTMENTS: eight department heads now own parts of what this brief surfaces, and the brief's job is to say whose each item is.
```

```text
An owner is one of the eight departments or a route outside them (legal, sales, marketing, product, engineering), and it's always a short name.
```

After:

```text
DEPARTMENTS: ten department heads now own parts of what this brief surfaces, and the brief's job is to say whose each item is.
```

```text
An owner is one of the ten departments or a route outside them (legal, product, engineering), and it's always a short name. Sales and marketing are departments now, and the config names them `sales-department` and `marketing-department`.
```

Checked: after the update the task list was read back and the stored prompt compared with the intended text. They were equal, 12,261 characters each. The task was enabled before and after, on the same schedule (`0 14 * * 1-5`, UTC).

Not checked: a run. The next scheduled run is the morning of 2026-10-08, and nothing here fired one.

## 2. `briefings.config.json`, the `departments` block (vault, `_Shared Knowledge/Agents and Plugins/`)

Text replacement only. The file was not reserialized. A copy from before the change is beside it as `briefings.config.json.bak-2026-10-07`.

| Key | Before | After |
|---|---|---|
| `owners.social` | `marketing` | `marketing-department` |
| `owners.contentPipeline` | `marketing` | `marketing-department` |
| `owners.outreach` | `marketing` | `marketing-department` |
| `owners.events` | `marketing` | `marketing-department` |
| `owners.searchVisibility` | `marketing` | `marketing-department` |
| `owners.competitors` | `marketing` | `marketing-department` |
| `owners.pipelineCommitments` | `sales` | `sales-department` |
| `goals[1].owner` (`sales-deals-dated`) | `sales` | `sales-department` |
| `goals[2].owner` (`mktg-live-campaigns`) | `marketing` | `marketing-department` |

Two notes under `_sourced` were reworded to say that sales and marketing became departments on 2026-10-07 and that legal, product and engineering are the routes left outside the ten. Goal ids, measures, targets, statuses and order are unchanged.

Checked: the file parses as JSON after the change; no owner is `sales` or `marketing`; the six goals' owners, in order, are finance, sales-department, marketing-department, operations, security, it-operations; a diff against the backup shows 22 changed lines (11 before, 11 after) and nothing else.

## 3. The context card (vault, `_Shared Knowledge/Operating Norms/chief-of-staff-context.md`)

Two lines changed.

- **Who.** The line that listed "the eight department agents" now says there were eight, that Dorian added sales-department and marketing-department on 2026-10-07, which makes ten, and that the roster in the Chief of Staff's manual is the one home for their names and remits. It also says that until the release carrying the two new departments is installed, that roster lists eight and the roster wins.
- **Books.** One sentence added: a disagreement between departments that involves finance gets run by the outside bookkeeper before it's settled (Dorian, 2026-10-07), the Chief of Staff writes the question for him into its decision memo, and Dorian takes it to him. The standing rule on that line, that agents don't contact him, is unchanged.

Checked: a diff against the copy taken before the change shows 4 changed lines (2 before, 2 after).

## What this doesn't make true

Until CS-004 is merged and the two packages are installed, the installed Chief of Staff routes eight, and `sales-department` and `marketing-department` are names with no agent behind them. The calendar only prints the label, so it's unaffected. The context card says the roster wins, for that reason.

## Looked at and left alone

- `Taskade/MoxyWolf LLC/00 – Project Hub/chief-of-staff-log.md` mentions the eight. It's the decision log, a record of past runs, and isn't rewritten.
- In this repository, the remaining mentions of eight departments are history: the two `goals/headcount-departments*` goals, and CS-001's own record in `DESIGN.md`.
