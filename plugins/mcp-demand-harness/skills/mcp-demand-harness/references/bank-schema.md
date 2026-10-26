# Bank schema (bank_version 1)

`scripts/demandlib.py` is the source of truth. This page explains it; if the two disagree, the code wins and this page is wrong.

## Top level

| Field | Meaning |
|---|---|
| `bank_version` | Always `1` |
| `product` | Profile product id, for example `stigviewer` |
| `personas[]` | `id` (kebab-case), `name`, `source` (where the persona is defined), `needs` |
| `questions[]` | See below |

## Question

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `Q-0001` style. Never reused |
| `text` | yes | The question as the user would type it, up to 2000 characters |
| `turns[]` | no | Follow-up turns for multi-turn cases |
| `persona` | yes | A declared persona id |
| `intent` | no | Short label |
| `mode` | yes | `discovery` (no tools named) or `strict` (checked) |
| `kind` | yes | `live` (product should answer), `composed` (needs several tools), `boundary` (product must decline or qualify), `gap` (product may not hold it yet) |
| `surfaces[]` | yes | `mcp`, `rest`, or both |
| `priority` | no | 1 (core), 2, or 3 |
| `status` | no | `active` or `parked` |
| `review_status` | no | `accepted` (default) or `draft`. Drafts never export, except with `--include-drafts` for staging review |
| `why` | strict only | What a failure would mean for the user |
| `requires_input[]` | no | Customer inputs the question needs, such as a scan file. Blocks export until a child supplies them |
| `evidence` | yes | See below |
| `expect` | strict needs one | See below |
| `payload` | no | A direct tool call: `tool`, `args`, `must_contain`, `must_not_match`, `absence_acceptable` |
| `rest` | no | Direct REST calls: `calls[]` (`method` GET or POST, `path`, `query`, `body`), plus `must_contain`, `must_not_match`, `absence_acceptable`. Paths must match a route in the capability map. PUT, PATCH and DELETE are rejected |
| `demand` | no | Counters from usage imports: how often near-duplicates were seen |
| `history[]` | no | Who approved what and when. Written by `accept`, `apply` and `approve-release` |

## Evidence

| Field | Meaning |
|---|---|
| `class` | `observed`, `reported`, `hypothesis`, or `generated` |
| `source` | Repo-relative path, table name, or document reference |
| `source_line`, `source_date` | Where and when, if known |
| `parent` | Required for `generated`. The parent must exist and must not be generated itself |
| `authored_by` | Required for drafts, for example `claude (draft)` |
| `redacted` | Must be `true` for `observed` |
| `release_approved_by`, `release_approved_on` | Required on `observed` before any export |
| `note` | Free text, such as which inputs are synthetic |

## Expect

| Field | Meaning |
|---|---|
| `first_tool_any_of[]` | The first tool called must be one of these |
| `must_call[]`, `must_not_call[]` | Tools that must or must not appear anywhere in the run |
| `must_contain[]` | Case-insensitive substrings the answer must contain |
| `must_not_match[]` | Regexes the answer must not match. A string, or `{pattern, case_sensitive}`. The validator rejects constructs that mean different things in Python and JavaScript |
| `max_tool_calls` | Upper bound on tool calls |
| `must_refuse` | The answer must decline. Needs a `rubric` that says what a correct refusal looks like |
| `absence_acceptable` | A typed "the product does not hold this" answer passes the content checks |
| `rubric` | LLM-judge criteria |

## Limits

- Generated questions per persona can be at most 3 times that persona's non-generated questions (`--ratio`).
- Discovery questions may not set `first_tool_any_of`, `must_call` or `must_not_call`.
