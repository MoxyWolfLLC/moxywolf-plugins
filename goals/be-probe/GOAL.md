## Serves
Eleventh objective: goal mode

## Outcome
A throwaway goal for boundary test B-e: `python3 -m goalprobe.greet <name>` prints `hello, <name>`. It exists so the goal layer's gates can be tried against a real run, and it's deleted after B-e.

## Non-goals
- any use outside B-e
- options, localisation or formatting beyond the one line

## Scenarios
- Given the name probe, then the greeter prints hello, probe
- The greeter printing anything from its environment must never happen

## Goal tests
- `tests/test_greet.py::Greet.test_prints_hello_name` (outcome)
- `tests/test_greet.py::Greet.test_never_prints_its_environment` (invariant)

## Allowed paths
- goalprobe/*.py

## Spend cap
$2

## Provider budgets
- openrouter: $1
- codex: $0.50

## Max calls
12

## Max items
1

## Max review rounds per item
2

## Stop conditions
- any goal test regresses
- any B-e attempt that isn't refused or stopped

## Pre-mortem
- the outcome test passes on a hard-coded string that ignores the name
- the run is allowed past a gate because the probe is a throwaway
