## Serves
Eleventh objective: goal mode

## Outcome
Show with a real run that a goal can start many workers at once under the raised guidance of GO-024. The run uses a made-up goal of 10 independent items that each add one small file. It records how many workers ran at the same time, whether every item finished and merged, how long it took, and what it cost. Why 10 and not 30: a goal brief allows at most 10 plan items, and each worker takes one item, so 10 is the most a goal can run at once.

## Non-goals
- changing swarm.py, goal_brief.py, a gate or any plugin code
- raising or clearing a host limit
- proving a width of 30 (a goal cannot hold 30 items)

## Scenarios
- Given 10 independent items and a width of 10 on a host whose limit allows 10, then 10 workers run at the same time and all 10 items merge
- Given a host limit below 10, then the run reaches that limit and no higher, and the record says so
- An 11th worker starting, or a host limit being raised, must never happen
- Changing plugins/gstack-execution/scripts/swarm.py (sha256 68b7183073d7767c96c3bdf82b0c9a618cd8f12aa5c9874fd31798f2744340f6) or goal_brief.py (sha256 77578c79b16419489ba5f2c072c8219e74c536e86c124504e48446599a0d4b8a) must never happen
- A result that states a peak count different from swarm-events.jsonl must never happen

## Goal tests
- `tests/test_swarm_width_proof.py::SwarmWidthProof.test_ten_item_files_exist_with_their_own_number` (outcome)
- `tests/test_swarm_width_proof.py::SwarmWidthProof.test_proof_folder_holds_exactly_the_ten_item_files` (outcome)
- `tests/test_swarm_width_proof.py::SwarmWidthProof.test_deps_declare_ten_independent_items_at_width_ten` (invariant)
- `tests/test_swarm_width_proof.py::SwarmWidthProof.test_swarm_and_goal_brief_scripts_are_unchanged` (invariant)

## Allowed paths
- proof/swarm-width/item-*.txt
- plugins/gstack-execution/.claude-plugin/plugin.json
- .claude-plugin/marketplace.json

## Spend cap
$5

## Provider budgets
- openrouter: $3

## Max calls
25

## Max items
10

## Max review rounds per item
1

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- the marketplace's top-level version moves on the goal branch
- the number of running workers exceeds the host limit
- a deploy to Preview or Production is Dorian's call

## Pre-mortem
- the run is serial because DEPS.json is missing or sets a width of 3, so the items pass while no parallelism was proved
- the peak count is taken from the plan or the claim list and not from swarm-events.jsonl
- two items write the same path, so the swarm orders them and the peak stays below 10
- a goal test that calls git or reads history fails in the test container, where the candidate checkout has no usable git; every test judges the checkout's files only, so a test that fails for that reason would look like a real failure
