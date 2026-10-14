# model-router

Every call a session makes is classified by code against an ontology. Only the calls that carry a model choice ask Jev. Everything is written to a ledger so the ontology and the choices can be reviewed. Design: MR-003 in `DESIGN.md`.

**Version:** see `.claude-plugin/plugin.json`.

## The hard limit

A hook cannot change the model answering the current turn. The session sets that. A hook can watch every call, classify it, record it, and rewrite the input of a call before it runs. The only calls that carry a model choice are subagent launches (the Agent tool's `model` field: haiku, sonnet, opus) and scripts that make their own LLM calls (packet coverage, model selection, the cross-vendor reviewer). Routing lands on subagent launches. Script classes are recorded with the tier the table gives them and left alone, because each script chooses its own model. Every other call is classified and ledgered, not rerouted. Don't read this plugin as "every call gets cheaper".

## The ontology

`references/call-ontology.json`. One entry per call class:

| Field | Meaning |
|---|---|
| `class` | short slug, what the ledger and `score` count by |
| `tool` | the tool name the hook sees (Read, Grep, Bash, Agent, ...) |
| `match` | null, or `{input field: regex}`; every regex must match for the entry to apply |
| `carries_model` | true only for Agent classes and the LLM-backed script classes |
| `default_tier` | `floor`, `standard`, `light` or `none` |
| `ask` | true when Jev is consulted even though the class is known |

The first matching entry wins, in file order, so put specific matches (git) before the catch-all (shell). `tiers` maps each tier to a model name: floor to opus, standard to sonnet, light to haiku. A call that matches no entry is class `unclassified`: recorded, counted in the session summary, never rewritten, unless it is an Agent launch, which asks Jev. A review subagent is never moved below floor whatever Jev says.

To add a class: add the entry, run `python3 scripts/route.py --selftest` and `python3 scripts/test_route.py`, and move `version`.

## Two decision paths

**Table.** `carries_model` true and `ask` false: the tier is the entry's default, the model is written into the launch, the line says `decided_by: table`. No Jev call, under two seconds.

**Jev.** `ask` true, or an unclassified Agent launch: the hook sends the launch's description and prompt head to Jev (`typesafe-ai/jev` through the Vercel AI Gateway, credential from `AI_GATEWAY_API_KEY` or the file `GSTACK_AIGATEWAY_ENV` names, `JEV_ENDPOINT` for a stub) with the five MR-002 questions, and the MR-002 rule table decides at the MR-002 bars: `risky` at or above 0.70 gives floor first; `trust_boundary` or `cross_file` at or above 0.30 give floor; `docs_only` at or above 0.60 with `has_tests` below 0.50 gives light; otherwise standard. The constants are copied under the same names; nothing is imported from gstack-execution. The line carries the answers, the rule and the bars, `decided_by: jev`.

A launch that already names a `model` keeps it (MR-001.7, a person's choice wins); the line records the caller's model and what the table or Jev advised. If Jev is unreachable the call runs on the table default (unchanged if unclassified) and the line says `jev: unavailable`. The hook never blocks a call and never raises: a failure is a `hook_error` line and the call proceeds unchanged.

## The ledger

`$GSTACK_PEER_REVIEW_DIR/model-routing/<YYYYMMDD>-<session_id>.jsonl`, or `~/.gstack/model-routing/` when the variable is unset (the first line says which). One line per call: `ts`, `class`, `tool`, `routed`, and for a routed line `tier`, `model`, `decided_by`. SessionStart writes the opening line; in a cloud session, where the plugin's hooks register after SessionStart has fired, the first PreToolUse writes it instead (`source: lazy`). SessionEnd appends a summary: calls by class, routed, Jev consults, tier counts, unclassified. With the ontology missing or invalid (unreadable, a non-object entry, a missing field, a non-boolean flag, a tier outside the three, a match that is not a regex), SessionStart says so on stderr, routing is off for the session, and each call is recorded as `refused`. The off state lives in the session's ledger, so a table restored mid-session does not turn routing back on, and neither does a later SessionStart for the same session (a compact or a resume) or a date rollover; the next session reads the table fresh. `MODEL_ROUTER_FORCE_ERROR=1` forces an internal failure so the test can prove the `hook_error` line; nothing else reads it.

`python3 scripts/route.py score --dir <ledger dir>` prints, per class and per tier, calls, routed, Jev consults and unclassified (an unclassified Agent launch that Jev routed shows in its tier's row), plus files, lines, distinct sessions and unclassified in all. Zero is printed as zero.

## Departments and the after-action report (CS-007)

A launch of one of the ten department agents (`finance:finance`, `sales-department:sales-department`, ...) is class `department-subagent`: default `standard`, `ask` true so Jev sees the dispatch, and the security department is never moved below floor. The line carries `department` and `cos_run`. The run id is session state: `/cos` step 1 runs `route.py cos-run start <id>` as its own command, the hook sees that Bash call go by and records `cos_run_start` in the session's ledger, and every later launch in that session carries the id until a `cos-run end` command closes it. A shell export in one tool call never reaches the hook process of a later one, and a shared file in the project would mix two sessions, so the command is the carrier. `COS_RUN_ID` in the environment is an explicit override for runners that set it. The hook never invents a run id. Every Agent line that launches also carries `applied_model` (the model the launch actually used: the caller's explicit choice, else the routed one) and `floor_rule` (true when a floor rule or the security or review lock put it on the floor), written at launch so no reader infers them later. `claim_check.py --department X --cos-run R --model M` (in the chief-of-staff plugin) appends one line per check to `claim-checks.jsonl` in the same directory, tagged with its model and department at the moment it is written.

`python3 scripts/route.py aar --dir <ledger dir> --date YYYY-MM-DD` prints one day's report in markdown: what it read (files and lines; zero lines is said to be zero, never a clean day), a fixed note that harder tasks go to stronger models by design, calls by class, then by model (launches that actually ran on it by `applied_model`, department dispatches, the share sent there by a floor rule, claim-check failures over dispatches, checks passed over checks, blocking findings over reviews from the MR-001 model-selection ledger beside this directory, by `declared_tier` only), then by department (dispatches, models used, checks passed over checks, send-backs over dispatches, escalations over runs: an escalation is a second failed check for one department in one run), the run list, and one decision. Records are selected by their timestamps, so a session that crosses midnight is split by day. Every rate is printed over its own usage count; a count under 10 is marked too few to read and called a lead; nothing names a cause. A claim-check line without a model or department, and a model-selection line without a declared tier, are counted as untagged and never attributed. Script classes carry advice, not a launch, and are not model usage. The decision names the gate with the worst rate over at least 10 of its own observations (a department's send-backs over its dispatches, a routing default's failures over its dispatches, the ontology's unclassified share), or reads `Decision: none this day; the counts are below the bar`. `/cos` step 1 writes it to the project's `00 – Project Hub/after-action/<date>.md` and leads with it as a proposal; the report never changes routing by itself.

## Hooks

`hooks/hooks.json` declares `SessionStart`, `PreToolUse` and `SessionEnd`, each running `scripts/route.py` (Python 3, stdlib only) and ending `exit 0`. `scripts/test_route.py` runs the hooks as subprocesses with the hook JSON on stdin, the way the host calls them, against a stub Jev.
