# Goal run: swarm-agent-view

- Outcome: running
- Approved in PR #386 by review 6011205869 at f8ebecc5c39d, tree c6f09bd06050
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-sonnet-5-5
- Goal branch: goal/swarm-agent-view from 8e25fe081292
- Spend: $0 across {}; 0 counted calls

## Items

1. add `viewer-start` and `viewer-stop` to swarm.py - merged
2. document the viewer in the gstack-goal command text - merged
3. move the plugin version - merged

## Goal tests at the last merged head

- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_start_runs_pinned_agent_flow_locally` (outcome): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_start_without_a_mac_or_npx_says_unavailable_and_exits_zero` (outcome): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_stop_ends_the_viewer_and_is_safe_when_none_runs` (outcome): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_commands_never_change_run_state_files` (invariant): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_hooks_json_is_unchanged_and_no_unpinned_agent_flow_is_started` (invariant): passed

## Digests and escalations

1. 2026-11-22T08:59:46+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: that the start-time check holds on macOS (ps lstart) against a real npx process; tests use a fake npx
   Against the brief: 1 of 3 items merged; 5 of 5 goal tests passing; spend $0, 0 counted calls
2. 2026-11-22T09:11:18+00:00 digest
   Item 2 merged
   Close calls: none
   Least sure of: that the paragraph's wording matches what agent-flow-app 0.9.6 actually does on first start (taken from reading its code, not from a run)
   Against the brief: 2 of 3 items merged; 5 of 5 goal tests passing; spend $0, 0 counted calls
3. 2026-11-22T09:22:39+00:00 digest
   Item 3 merged
   Close calls: none
   Least sure of: that reading the plan's 'marketplace.json is not changed' as top-level-only is what Dorian intends; the repo's manifest test forces the plugin entry to move
   Against the brief: 3 of 3 items merged; 5 of 5 goal tests passing; spend $0, 0 counted calls

## Delivery

- final (PR #None into main)
  - merge: not merged
  - release record: not recorded
