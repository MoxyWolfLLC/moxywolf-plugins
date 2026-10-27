#!/bin/sh
# Candidate-to-head comparison for goal item 1 (review F2). Prints, for each runtime file, the sha256 of the
# frozen candidate d389119's copy, of the retained copy under this folder, and of the file at HEAD, then the
# unified diff d389119..HEAD for the subset. Exit 0 only when the retained copies match d389119 byte for byte.
set -e
cd "$(git rev-parse --show-toplevel)"
P=plugins/gstack-execution; D=docs/evidence/gstack-delivery; rc=0
for f in scripts/graph_context.py scripts/test_graph_context.py scripts/task_graph.py scripts/test_task_graph.py skills/gstack-execution/references/task-graph-contract.md README.md commands/gstack-build.md .claude-plugin/plugin.json; do
  n=$(basename "$f")
  c=$(git show "d389119:$P/$f" | shasum -a 256 | cut -c1-64)
  r=$(shasum -a 256 "$D/candidate-d389119-$n.d389119" | cut -c1-64)
  h=$(git show "HEAD:$P/$f" | shasum -a 256 | cut -c1-64)
  [ "$c" = "$r" ] || rc=1
  printf '%s\n  d389119  %s\n  retained %s\n  HEAD     %s  %s\n' "$f" "$c" "$r" "$h" "$([ "$c" = "$h" ] && echo identical || echo DIFFERS)"
done
echo "--- git diff --stat d389119 HEAD -- runtime subset"
git diff --stat d389119 HEAD -- $P/scripts/graph_context.py $P/scripts/test_graph_context.py $P/scripts/task_graph.py $P/scripts/test_task_graph.py $P/skills/gstack-execution/references/task-graph-contract.md $P/README.md $P/commands/gstack-build.md $P/.claude-plugin/plugin.json
echo "--- git diff d389119 HEAD -- task_graph.py"
git diff d389119 HEAD -- $P/scripts/task_graph.py
echo "--- added tests in test_task_graph.py"
git diff d389119 HEAD -- $P/scripts/test_task_graph.py | grep '^+    def test_'
exit $rc
