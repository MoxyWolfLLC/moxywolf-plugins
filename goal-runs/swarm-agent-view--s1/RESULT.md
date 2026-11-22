# Goal run: swarm-agent-view--s1

- Outcome: running
- Added in PR #392 at 30c9b93a2414, tree a92c8ffd51ea; a successor (GO-011.9) approved by review 6011205869 on its root goal's PR #386 at f8ebecc5c39d
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-sonnet-5-5
- Goal branch: goal/swarm-agent-view--s1 from 6d48bce00c30
- Spend: $0 across {}; 0 counted calls

## Items

1. add `viewer-start` and `viewer-stop` to swarm.py - merged
2. document the viewer in the gstack-goal command text - merged
3. move the plugin version - merged

## Goal tests at the last merged head

- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_start_runs_pinned_agent_flow_locally` (outcome): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_start_without_a_mac_or_npx_says_unavailable_and_exits_zero` (outcome): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_stop_ends_the_viewer_and_is_safe_when_none_runs` (outcome): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_crashed_viewer_is_not_running_and_can_be_started_again` (outcome): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_commands_never_change_run_state_files` (invariant): passed
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_hooks_json_is_unchanged_and_no_unpinned_agent_flow_is_started` (invariant): passed

## Digests and escalations

1. 2026-11-22T17:17:31+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: that a crashed viewer is seen as ended on macOS (ps stat) as it is on Linux (/proc state); tests run in the Linux container only
   Against the brief: 1 of 3 items merged; 6 of 6 goal tests passing; spend $0, 0 counted calls
2. 2026-11-22T17:26:40+00:00 digest
   Item 2 merged
   Close calls: none
   Least sure of: that the paragraph's description of agent-flow's hook installation still matches agent-flow-app 0.9.6 on a real first start; taken from the approved brief, not run
   Against the brief: 2 of 3 items merged; 6 of 6 goal tests passing; spend $0, 0 counted calls
3. 2026-11-22T17:36:18+00:00 digest
   Item 3 merged
   Close calls: none
   Least sure of: nothing beyond the two version strings; the version gate and manifest consistency test are the checks
   Against the brief: 3 of 3 items merged; 6 of 6 goal tests passing; spend $0, 0 counted calls

## Delivery

- final (PR #None into main)
  - merge: not merged
  - release record: not recorded
