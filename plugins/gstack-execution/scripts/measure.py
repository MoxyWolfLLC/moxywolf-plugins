#!/usr/bin/env python3
"""XE-012: every gstack run records what it cost, against predictions stated before the data.

  measure.py record <review-id> --vault <dir> [--transcript <jsonl>] [--since ISO] [--until ISO]
  measure.py report --vault <dir> [--transcript <jsonl>]
  measure.py --selftest

`record` writes one Obsidian note per run into <dir> (the vault's measurements/gstack-runs
folder), every number a frontmatter property. `release` calls it when GSTACK_MEASURE_DIR is set.
`report` reads every note, groups by vocabulary version (each version is a break point), and
scores the four predictions DESIGN.md states under XE-012.

Rules this file holds to:
- A number that could not be measured is null with a reason, never 0 (EV-001).
- `correct` and `defect_traced` belong to the named human. `record` writes them as `pending`
  once and never overwrites them afterwards.
- The transcript logs one assistant message as several entries repeating the same usage, so usage
  is counted once per message id. Counting entries overstated the first measurement by ~1.9x.

ponytail: stdlib only, frontmatter values written as JSON (valid YAML flow scalars) so reading
them back needs no YAML parser. Upgrade path: a real YAML library if humans hand-edit these
notes into shapes this reader cannot parse.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr  # noqa: E402

HUMAN_OWNED = ("correct", "defect_traced")
MIN_CORRECT_RUNS = 10          # a version with fewer correct runs is insufficient data (criterion 6)
MIN_TRACED_DEFECTS = 5         # P4 is first testable at this many traced defects
PASSING = {"no_blocking_findings", "fixes_verified"}
UNSEEN = ["commands the reviewer ran and ad-hoc consultations (EV-008 criteria 1 and 3)",
          "per-dependency reads (EV-006 criterion 1)", "human time"]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------- builder cost from the session transcript (criterion 2) ----------

def default_transcript():
    """GSTACK_TRANSCRIPT, else the most recently written session transcript on this host."""
    if os.environ.get("GSTACK_TRANSCRIPT"):
        return Path(os.environ["GSTACK_TRANSCRIPT"])
    cands = sorted(Path.home().glob(".claude/projects/*/*.jsonl"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def transcript_usage(path, since, until):
    """({tokens...}, None) or (None, reason). Counts each assistant message id once."""
    if not path or not Path(path).is_file():
        return None, f"transcript not readable: {path}"
    lo, hi = _ts(since), _ts(until)
    usage, tools, models = {}, {}, set()
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        m = d.get("message") or {}
        if d.get("type") != "assistant" or not isinstance(m.get("usage"), dict) or not d.get("timestamp"):
            continue
        if not lo <= _ts(d["timestamp"]) <= hi:
            continue
        mid = m.get("id") or d.get("uuid")
        usage[mid] = m["usage"]
        content = m.get("content") if isinstance(m.get("content"), list) else []
        tools.setdefault(mid, set()).update(c.get("id") for c in content if isinstance(c, dict) and c.get("type") == "tool_use")
        if m.get("model"):
            models.add(m["model"])
    if not usage:
        return None, f"no assistant messages in the window {since} .. {until}"
    s = lambda k: sum(int(u.get(k) or 0) for u in usage.values())
    out = {"builder_input_tokens": s("input_tokens"), "builder_output_tokens": s("output_tokens"),
           "builder_cache_write_tokens": s("cache_creation_input_tokens"),
           "builder_cache_read_tokens": s("cache_read_input_tokens"),
           "builder_turns": len(usage), "builder_tool_calls": sum(len(t - {None}) for t in tools.values()),
           "builder_models": sorted(models)}
    out["builder_total_tokens"] = sum(out[k] for k in ("builder_input_tokens", "builder_output_tokens",
                                                       "builder_cache_write_tokens", "builder_cache_read_tokens"))
    return out, None


# ---------- the run record (criteria 1, 3) ----------

def _git(repo, *a):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def run_window(d, packet):
    """From the run's first commit to release (or now, when not released yet).

    The packet's base moves: a fix-verification round rewrites it to the previous head, so the
    packet alone would date the run from its last fix. Round 1 keeps the original base. Found by
    recording this item's own run, which the first version dated from its final commit."""
    first_round = pr.load(d, "round-1.json") or {}
    starts = []
    for r in first_round.get("repos") or packet["repos"]:
        first = _git(r["path"], "log", "--reverse", "--format=%cI", f"{r['base']}..{r['head']}").splitlines()
        if first:
            starts.append(_ts(first[0]))
    rel = pr.load(d, "release.json") or {}
    until = rel.get("requested_at") or now_iso()
    since = min(starts).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if starts else None
    return since, until


def _vocab_terms():
    """Terms a finding can be 'about': snake_case ids and the labels of the contract's nouns.
    Single common words (done, review) are left out; matching them would count every finding."""
    out = set()
    for c in pr.VOCAB["concepts"]:
        if "_" in c["id"]:
            out.add(c["id"].lower())
        if c["group"] == "term":
            out.add(c["skos:prefLabel"].lower())
    return out


def repeat_findings(rounds):
    """A repeat finding is a blocking finding raised again in a later round about the same criterion."""
    seen, repeats, vocab_repeats = {}, 0, 0
    terms = _vocab_terms()
    for n, rec in enumerate(rounds, 1):
        for f in rec.get("findings") or []:
            if not isinstance(f, dict) or f.get("severity") != "blocking":
                continue
            key = (f.get("criterion") or "").strip()
            if key in seen and seen[key] < n:
                repeats += 1
                text = " ".join(str(f.get(k, "")) for k in ("what", "evidence", "criterion")).lower()
                if any(t in text for t in terms):
                    vocab_repeats += 1
            seen.setdefault(key, n)
    return repeats, vocab_repeats


def build_record(review_id, transcript=None, since=None, until=None):
    d = pr.rdir(review_id)
    state, packet = pr.load(d, "state.json"), pr.load(d, "packet.json")
    rounds = [pr.load(d, f"round-{n}.json") or {} for n in range(1, state.get("rounds_used", 0) + 1)]
    w_since, w_until = run_window(d, packet)
    since, until = since or w_since, until or w_until
    last = rounds[-1] if rounds else {}
    ex = last.get("examined") or {}
    rec = {"type": "gstack-run", "review_id": review_id, "recorded_at": now_iso(),
           "items": packet.get("items") or [], "repo": [Path(r["path"]).name for r in packet["repos"]],
           "head": [r["head"] for r in packet["repos"]],
           "vocabulary_version": packet.get("vocabulary_version") or pr.VOCAB_VERSION,
           "reviewer": state.get("reviewer"), "reviewer_model": last.get("model"),
           "rounds": state.get("rounds_used"), "outcome": state.get("outcome"),
           "files_examined": ex.get("examined_count"), "files_offered": ex.get("offered_count"),
           "looked_beyond_diff": ex.get("looked_beyond_the_diff"),
           "thin_review": (ex.get("looked_beyond_the_diff") is False) if ex else None,
           "touches_vocabulary": any("vocabulary.json" in _git(r["path"], "diff", "--name-only", r["base"], r["head"])
                                     for r in packet["repos"]),
           "coverage_scorer_input_tokens": (packet.get("coverage") or {}).get("input_tokens"),
           "window_start": since, "window_end": until}
    rec["repeat_findings"], rec["repeat_findings_vocab"] = repeat_findings(rounds)
    # criterion 3: reviewer usage per round, as reported; not_reported stays not_reported
    per_round = [r.get("reviewer_usage", "not_reported") for r in rounds]
    totals = [u.get("total") for u in per_round if isinstance(u, dict) and u.get("total") is not None]
    rec["reviewer_tokens_per_round"] = per_round
    rec["reviewer_tokens"] = sum(totals) if totals and len(totals) == len(per_round) else None
    if rec["reviewer_tokens"] is None:
        rec["reviewer_tokens_reason"] = "not reported by the reviewer CLI for every round" if per_round else "no rounds ran"
    # criterion 2: builder cost over the window
    path = Path(transcript) if transcript else default_transcript()
    rec["transcript_path"] = str(path) if path else None
    if since is None:
        usage, why = None, "no commits between base and head, so the window has no start"
    else:
        usage, why = transcript_usage(path, since, until)
    for k in ("builder_input_tokens", "builder_output_tokens", "builder_cache_write_tokens",
              "builder_cache_read_tokens", "builder_total_tokens", "builder_turns", "builder_tool_calls"):
        rec[k] = usage[k] if usage else None
    rec["builder_models"] = usage["builder_models"] if usage else []
    if not usage:
        rec["builder_tokens_reason"] = why
    rec["correct"] = "pending"
    rec["defect_traced"] = "pending"
    return rec


# ---------- the Obsidian note (criteria 4, 5) ----------

def note_text(rec, body=""):
    lines = ["---"] + [f"{k}: {json.dumps(v)}" for k, v in rec.items()] + ["---", ""]
    return "\n".join(lines) + body


def read_note(path):
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        k, _, v = line.partition(": ")
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v.strip().strip('"')   # a hand edit like `correct: true` without quotes still reads
    return out


BASE_FILE = """filters:
  and:
    - type == "gstack-run"
views:
  - type: table
    name: Runs by vocabulary version
    groupBy:
      property: vocabulary_version
      direction: ASC
    order:
      - file.name
      - correct
      - outcome
      - rounds
      - thin_review
      - builder_total_tokens
      - builder_cache_read_tokens
      - builder_output_tokens
      - reviewer_tokens
"""


def write_note(vault, rec):
    vault = Path(vault)
    vault.mkdir(parents=True, exist_ok=True)
    base = vault / "gstack-runs.base"
    if not base.exists():
        base.write_text(BASE_FILE)
    path = vault / f"{rec['recorded_at'][:10]}-{rec['review_id']}.md"
    existing = next(iter(sorted(vault.glob(f"*-{rec['review_id']}.md"))), None)
    if existing:                                  # human-owned fields survive a re-record
        old = read_note(existing)
        for k in HUMAN_OWNED:
            if k in old:
                rec[k] = old[k]
        path = existing
    body = (f"# gstack run {rec['review_id']}\n\n"
            f"Items: {', '.join(rec['items']) or 'none named'}. Outcome `{rec['outcome']}` in {rec['rounds']} round(s).\n\n"
            "Set `correct` to true or false once you have judged the result, and `defect_traced` to true if a defect is later "
            "traced to this run. Nothing else writes those two fields.\n")
    path.write_text(note_text(rec, body))
    # Criterion 1 is one record per RUN, and a run can hold several reviews: a review that ends
    # review_unavailable or goes stale is followed by a fresh one over the same commits. Their
    # windows overlap, so summing both notes counts the builder's tokens twice. Found recording
    # XE-012's own run, whose two notes summed to 46.7M tokens over one 30-minute window.
    for other in vault.glob("*.md"):
        if other == path or other.name.endswith("-report.md"):
            continue
        o = read_note(other)
        if (o.get("type") == "gstack-run" and o.get("items") == rec["items"]
                and o.get("window_start") == rec["window_start"] and not o.get("superseded_by")):
            o["superseded_by"] = rec["review_id"]
            text = other.read_text(encoding="utf-8")
            other.write_text(note_text(o, text.split("\n---\n", 1)[1] if "\n---\n" in text else ""))
    return path


# ---------- the report (criteria 6, 7, 8, 9) ----------

def _vkey(v):
    return tuple(int(x) if x.isdigit() else x for x in re.split(r"[.\-]", str(v)))


def _is_true(v):
    return v is True or str(v).lower() == "true"


def score(runs):
    """Per-version stats and the four predictions. Each verdict is supported, refuted or insufficient data."""
    by = {}
    for r in runs:
        by.setdefault(str(r.get("vocabulary_version")), []).append(r)
    versions = sorted(by, key=_vkey)
    stats = {}
    for v in versions:
        rs = by[v]
        known = [r for r in rs if isinstance(r.get("builder_total_tokens"), int)]
        correct = [r for r in rs if _is_true(r.get("correct"))]
        correct_b = [r for r in correct if isinstance(r.get("builder_total_tokens"), int)]
        correct_r = [r for r in correct if isinstance(r.get("reviewer_tokens"), int)]
        correct_net = [r for r in correct_b if not r.get("touches_vocabulary")]
        stats[v] = {"runs": len(rs), "correct": len(correct),
                    "pending": sum(1 for r in rs if str(r.get("correct")) == "pending"),
                    "builder_tokens": sum(r["builder_total_tokens"] for r in known),
                    "runs_with_tokens": len(known),
                    # Criterion 5: cost per correct run counts only runs marked true, numerator included.
                    # All runs' tokens stay visible as builder_tokens, so the cost of wrong runs is not hidden.
                    # F2 (review 20260919-214027): divide by the correct runs that HAVE a count; a
                    # correct run with no token data must not deflate the average toward zero.
                    "builder_tokens_per_correct": (sum(r["builder_total_tokens"] for r in correct_b) / len(correct_b)) if correct_b else None,
                    "correct_without_builder_tokens": len(correct) - len(correct_b),
                    "reviewer_tokens": sum(r["reviewer_tokens"] for r in rs if isinstance(r.get("reviewer_tokens"), int)),
                    "reviewer_tokens_per_correct": (sum(r["reviewer_tokens"] for r in correct_r) / len(correct_r)) if correct_r else None,
                    "correct_without_reviewer_tokens": len(correct) - len(correct_r),
                    "cache_read_share": (sum(r.get("builder_cache_read_tokens") or 0 for r in known) / sum(r["builder_total_tokens"] for r in known))
                                        if known and sum(r["builder_total_tokens"] for r in known) else None,
                    "maintenance_tokens": sum(r["builder_total_tokens"] for r in correct_b if r.get("touches_vocabulary")),
                    # P1 is net of upkeep (Dorian, 2026-09-19): correct runs that changed vocabulary.json
                    # leave both the numerator and the denominator, and their tokens are reported apart.
                    "builder_tokens_per_correct_net": (sum(r["builder_total_tokens"] for r in correct_net) / len(correct_net)) if correct_net else None,
                    "rounds_per_review": (sum(r.get("rounds") or 0 for r in rs) / len(rs)) if rs else None,
                    "repeat_findings": sum(r.get("repeat_findings") or 0 for r in rs),
                    "thin_review_rate": (sum(1 for r in rs if r.get("thin_review") is True) / len(rs)) if rs else None,
                    "models": sorted({m for r in rs for m in (r.get("builder_models") or [])} | {r.get("reviewer_model") for r in rs if r.get("reviewer_model")})}
    preds = {}
    # Criterion 6: a version with fewer than 10 correct runs is insufficient data for ANY prediction,
    # so every prediction is scored only over runs in qualifying versions.
    q = [v for v in versions if stats[v]["correct"] >= MIN_CORRECT_RUNS]
    qruns = [r for r in runs if str(r.get("vocabulary_version")) in q]
    short = f"no version has {MIN_CORRECT_RUNS}+ correct runs yet"
    # P1: first two qualifying versions, compared net of vocabulary upkeep (Dorian's reading of
    # "net of", 2026-09-19): runs that changed vocabulary.json are left out and reported apart.
    if len(q) < 2:
        preds["P1"] = ("insufficient data", f"{len(q)} version(s) have {MIN_CORRECT_RUNS}+ correct runs; 2 needed")
    else:
        a, b = q[0], q[1]
        ca, cb = stats[a]["builder_tokens_per_correct_net"], stats[b]["builder_tokens_per_correct_net"]
        note = "" if stats[a]["models"] == stats[b]["models"] else " The comparison crosses a model change."
        if ca is None or cb is None:
            preds["P1"] = ("insufficient data", "a qualifying version has no correct run outside vocabulary upkeep")
        else:
            preds["P1"] = ("supported" if cb < ca else "refuted",
                           f"{a}: {ca:,.0f} builder tokens per correct run; {b}: {cb:,.0f}, net of "
                           f"{stats[a]['maintenance_tokens']:,} and {stats[b]['maintenance_tokens']:,} tokens of vocabulary upkeep, reported apart.{note}")
    # P2: cache reads are >= 90% of builder tokens in >= 9 of 10 runs
    known = [r for r in qruns if isinstance(r.get("builder_total_tokens"), int) and r["builder_total_tokens"] > 0]
    if not q or not known:
        preds["P2"] = ("insufficient data", short if not q else "no run in a qualifying version has token counts")
    else:
        hi = sum(1 for r in known if r["builder_cache_read_tokens"] / r["builder_total_tokens"] >= 0.9)
        preds["P2"] = ("supported" if hi / len(known) >= 0.9 else "refuted", f"{hi} of {len(known)} runs at 90%+ cache reads")
    # P3: repeat findings about a vocabulary-defined term in at most 1 review in 10
    reviewed = [r for r in qruns if (r.get("rounds") or 0) > 0]
    if not q or not reviewed:
        preds["P3"] = ("insufficient data", short if not q else "no reviewed run in a qualifying version")
    else:
        hit = sum(1 for r in reviewed if (r.get("repeat_findings_vocab") or 0) > 0)
        preds["P3"] = ("supported" if hit / len(reviewed) <= 0.1 else "refuted", f"{hit} of {len(reviewed)} reviews repeated a finding about a defined term")
    # P4: thin reviews over-represented among passing runs later traced to a defect
    passing = [r for r in qruns if r.get("outcome") in PASSING and r.get("thin_review") is not None]
    traced = [r for r in passing if _is_true(r.get("defect_traced"))]
    if not q or len(traced) < MIN_TRACED_DEFECTS:
        preds["P4"] = ("insufficient data", short if not q else f"{len(traced)} traced defect(s); {MIN_TRACED_DEFECTS} needed")
    else:
        share_all = sum(r["thin_review"] for r in passing) / len(passing)
        share_def = sum(r["thin_review"] for r in traced) / len(traced)
        preds["P4"] = ("supported" if share_def > share_all else "refuted",
                       f"thin share {share_def:.0%} among traced defects vs {share_all:.0%} of passing runs")
    return versions, stats, preds


def report_text(runs, own_cost):
    versions, stats, preds = score(runs)
    out = [f"# gstack measurement report {now_iso()[:10]}", "",
           f"{len(runs)} run note(s) read. Each vocabulary version is a break point.", ""]
    if not runs:
        out += ["No run has been recorded, so every prediction is insufficient data. This report examined nothing "
                "and says so rather than presenting empty tables as a result.", ""]
    for v in versions:
        s = stats[v]
        per = f"{s['builder_tokens_per_correct']:,.0f}" if s["builder_tokens_per_correct"] is not None else "n/a (no correct runs)"
        out += [f"## Vocabulary {v}", "",
                f"- runs {s['runs']} (correct {s['correct']}, pending {s['pending']}); {s['runs_with_tokens']} with builder token counts",
                f"- builder tokens {s['builder_tokens']:,}; per correct run {per}"
                + (f" ({s['correct_without_builder_tokens']} correct run(s) have no count and are left out)" if s["correct_without_builder_tokens"] else ""),
                f"- cache-read share of builder tokens {s['cache_read_share']:.1%}" if s["cache_read_share"] is not None else "- cache-read share: n/a (no token counts)",
                f"- vocabulary upkeep (correct runs that changed vocabulary.json) {s['maintenance_tokens']:,} builder tokens, left out of P1's per-correct-run figure"
                + (f"; net per correct run {s['builder_tokens_per_correct_net']:,.0f}" if s["builder_tokens_per_correct_net"] is not None else ""),
                f"- reviewer tokens {s['reviewer_tokens']:,} (reported rounds only); per correct run "
                + (f"{s['reviewer_tokens_per_correct']:,.0f}" if s["reviewer_tokens_per_correct"] is not None else "n/a"),
                f"- rounds per review {s['rounds_per_review']:.2f}; repeat findings {s['repeat_findings']}; thin-review rate {s['thin_review_rate']:.0%}",
                f"- models: {', '.join(s['models']) or 'none recorded'}", ""]
    if len({tuple(stats[v]['models']) for v in versions}) > 1:
        out += ["Models differ across versions; any cross-version comparison above crosses a model change.", ""]
    out += ["## Predictions (stated 2026-09-19, before any data)", ""]
    out += [f"- **{k}**: {verdict}. {why}" for k, (verdict, why) in preds.items()]
    out += ["", "## What this cannot see", ""] + [f"- {u}" for u in UNSEEN]
    out += [f"- this report's own cost: {own_cost}", ""]
    return "\n".join(out)


def cmd_report(vault, transcript=None):
    vault = Path(vault)
    runs = [read_note(p) for p in sorted(vault.glob("*.md")) if not p.name.endswith("-report.md")]
    runs = [r for r in runs if r.get("type") == "gstack-run" and not r.get("superseded_by")]
    # F2 (review 20260919-213145): the newest transcript on a shared host may be someone else's
    # session, so the report's own cost is measured only from a transcript named explicitly.
    named = transcript or os.environ.get("GSTACK_TRANSCRIPT")
    usage, why = (transcript_usage(Path(named), "1970-01-01T00:00:00Z", now_iso()) if named
                  else (None, "no transcript named; pass --transcript or set GSTACK_TRANSCRIPT"))
    own = (f"{usage['builder_total_tokens']:,} tokens in the session that produced it ({usage['builder_turns']} turns)"
           if usage else f"not measured ({why})")
    out = vault / f"{now_iso()[:10]}-gstack-measurement-report.md"
    vault.mkdir(parents=True, exist_ok=True)
    out.write_text(report_text(runs, own))
    return out, len(runs)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    if argv[0] == "--selftest":
        return selftest()
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None
    vault = opt("--vault") or os.environ.get("GSTACK_MEASURE_DIR")
    if not vault:
        sys.exit("--vault or GSTACK_MEASURE_DIR is required: the vault folder the run notes live in")
    if argv[0] == "record":
        rec = build_record(argv[1], opt("--transcript"), opt("--since"), opt("--until"))
        p = write_note(vault, rec)
        print(f"recorded {p}")
        if rec.get("builder_tokens_reason"):
            print(f"builder tokens not measured: {rec['builder_tokens_reason']}")
        return 0
    if argv[0] == "report":
        p, n = cmd_report(vault, opt("--transcript"))
        print(f"report {p} over {n} run note(s)")
        return 0
    sys.exit(f"unknown command {argv[0]}")


def selftest():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        tr = t / "s.jsonl"
        u = {"input_tokens": 1, "output_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000}
        rows = [{"type": "assistant", "timestamp": "2026-09-19T10:00:00Z", "message": {"id": "m1", "model": "x", "usage": u, "content": [{"type": "text"}]}},
                {"type": "assistant", "timestamp": "2026-09-19T10:00:01Z", "message": {"id": "m1", "model": "x", "usage": u, "content": [{"type": "tool_use", "id": "t1"}]}},
                {"type": "assistant", "timestamp": "2026-09-19T12:00:00Z", "message": {"id": "m2", "model": "x", "usage": u, "content": []}}]
        tr.write_text("\n".join(json.dumps(r) for r in rows))
        got, why = transcript_usage(tr, "2026-09-19T09:00:00Z", "2026-09-19T11:00:00Z")
        assert got["builder_turns"] == 1 and got["builder_tool_calls"] == 1, got      # one message, not two entries
        assert got["builder_cache_read_tokens"] == 1000 and got["builder_total_tokens"] == 1111, got
        assert transcript_usage(t / "gone.jsonl", "2026-09-19T09:00:00Z", "2026-09-19T11:00:00Z")[0] is None
        assert transcript_usage(tr, "2026-09-18T00:00:00Z", "2026-09-18T01:00:00Z")[0] is None   # empty window is not zero
        rec = {"type": "gstack-run", "review_id": "r1", "recorded_at": "2026-09-19T12:00:00Z", "items": ["XE-012"],
               "outcome": "fixes_verified", "rounds": 2, "correct": "pending", "defect_traced": "pending", "builder_total_tokens": None}
        p = write_note(t / "v", dict(rec))
        assert read_note(p)["builder_total_tokens"] is None and (t / "v" / "gstack-runs.base").exists()
        p.write_text(p.read_text().replace('correct: "pending"', "correct: true"))
        write_note(t / "v", dict(rec))                                          # a re-record keeps the human's verdict
        assert read_note(p)["correct"] is True
        _, _, preds = score([])
        assert all(v == "insufficient data" for v, _ in preds.values())
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
