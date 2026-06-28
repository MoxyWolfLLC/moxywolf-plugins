#!/usr/bin/env bash
# PreCompact hook: snapshot the transcript before compaction so nothing is
# unrecoverable, and ask the compactor to keep the load-bearing state verbatim.
# ponytail: snapshot-only. Curating the transcript into durable memory stays a
# model step (/session-end -> /obsidian-update); a shell hook can't do judgment.
python3 - <<'PY'
import json, os, sys, shutil, time
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
tp = data.get("transcript_path", "")
d = os.path.expanduser("~/.claude/precompact-snapshots")
os.makedirs(d, exist_ok=True)
if tp and os.path.exists(tp):
    sid = (data.get("session_id") or "session")[:8]
    shutil.copy2(tp, os.path.join(d, f"{sid}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"))
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreCompact",
  "additionalContext": "When compacting, preserve verbatim: open work / next steps, commit & push state (hashes + what is pushed), and any decisions or facts noted but not yet saved to a file or memory."}}))
PY
