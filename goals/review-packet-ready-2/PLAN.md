# review-packet-ready-2
1. Refuse a packet with no data_use before anything is created
   - `peer_review.py open` checks the packet's `data_use` block for the reviewer it would choose before it makes a review id, a review folder or any reviewer call
   - a missing or empty `data_use` prints `refused: data_use missing` on standard error, writes nothing under the review directory, and exits 2
   - a `data_use` that denies the chosen reviewer prints `refused: data_use_denied: <reason>` on standard error and exits 2, with nothing written
   - a packet whose `data_use` allows the reviewer opens exactly as it does today
   - every existing test whose fixture packet has no `data_use` block gains one and passes again, with its assertions unchanged
2. Refuse missing coverage and a ledger run behind the head
   - `open` and `round` refuse a packet that names a ledger run whose recorded commit isn't the head being sent, printing `refused: ledger run <id> is at <run sha>, head is <head sha>` with full SHAs on standard error, exit 2, nothing dispatched
   - `open` refuses a packet with no attached coverage report, printing `refused: coverage not attached` on standard error, exit 2, unless the packet already records `--accept-narrow-packet` or another existing override, which keeps working and is recorded as today
   - every refusal names the packet field to fix
   - every existing test whose fixture packet has no coverage report gains one, or `--accept-narrow-packet` where it tests a packet without coverage, and passes again with its assertions unchanged
3. Read every surfaced file from the head commit (MOXY-159)
   - the surface reads each changed file and each caller it adds with `git show <head>:<path>`, never from the working tree, so a checkout on another branch surfaces the head's bytes
   - a path missing at the head is surfaced as deleted, not read from disk
   - `tests/test_peer_review.py` opens a review from a checkout on another branch and asserts the head's bytes, and fails on the code before this item
4. Docs, version and the suites
   - `commands/gstack-peer-review.md` and `peer-review-contract.md` list the new refusals with their messages and exit code 2
   - gstack-execution moves a patch version in `plugin.json`, its marketplace entry and its README version history; the marketplace's top-level version is left for the release
   - `run_all_tests.py` names `test_peer_review.py` among the suites it ran and reports no failures
