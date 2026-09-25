#!/usr/bin/env python3
"""Route a Council query with Jev, TypeSafe AI's System One model.

The smart-router asks four questions of every incoming query: what kind of query
is it, which protocol suits it, is it compound, and would independent models
materially change the answer. Those are exactly the shapes Jev returns: two
choices and two booleans, each with a calibrated probability, in one call at
roughly 100ms.

Why this exists. The router's own confidence bands (>0.8 follow, 0.5-0.8 follow
but flag, else explore) were written against keyword matching, where "confidence"
was a number somebody picked. Jev is trained for calibrated decisions, so a 0.9
means right about nine times in ten. The thresholds start meaning what the skill
already claimed they meant.

Never fabricates. No key or no answer raises JevUnavailable and the caller falls
back to the heuristic table, which is the behaviour that was there before.

ponytail: one file, stdlib + curl. The key resolver mirrors openrouter_key.py's
chain rather than inventing a second convention (DR-010).
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://ai-gateway.vercel.sh/v1/evaluate")
MODEL = os.environ.get("JEV_MODEL", "typesafe-ai/jev")
VAULT_REL = "_Shared Knowledge/Agents and Plugins/aigateway.env"

CATEGORIES = {
    "architecture_decision": "Comparing designs, tradeoffs, migrations, or patterns.",
    "compliance_security": "Compliance, security, risk, audit, or regulatory frameworks.",
    "code_implementation": "Writing, fixing, testing, or deploying specific code.",
    "strategy_business": "Strategy, market, pricing, positioning, or roadmap.",
    "creative_writing": "Drafting prose, posts, articles, headlines, or narrative.",
    "factual_lookup": "A definition, syntax, or how-something-works question.",
    "other": "None of the above fits.",
}


class JevUnavailable(RuntimeError):
    """No usable key, or the gateway did not answer. Caller falls back."""


def _parse_env_file(path: Path) -> dict:
    env = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k.startswith("export "):
            k = k[len("export "):].strip()
        v = v.strip()
        if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        env[k] = v
    return env


def load_gateway_key(*, return_source: bool = False):
    """AI_GATEWAY_API_KEY, resolved the way DR-010 resolves the OpenRouter key."""
    direct = os.environ.get("AI_GATEWAY_API_KEY")
    if direct:
        return (direct, "AI_GATEWAY_API_KEY env var") if return_source else direct

    candidates, tried = [], []
    explicit = os.environ.get("AIGATEWAY_KEY_FILE")
    if explicit:
        candidates.append(("AIGATEWAY_KEY_FILE env var", Path(explicit)))
    vault = os.environ.get("MOXYWOLF_VAULT")
    if vault:
        candidates.append(("MOXYWOLF_VAULT env var", Path(vault) / VAULT_REL))
    patterns = [
        ("Cowork bash sandbox mount", f"/sessions/*/mnt/MoxyWolf Vault/{VAULT_REL}"),
        ("macOS Google Drive shared drive", str(
            Path.home() / "Library" / "CloudStorage" / "GoogleDrive-*" / "Shared drives"
            / "MoxyWolf Shared Files" / "MoxyWolf Vault" / VAULT_REL)),
    ]
    for label, pattern in patterns:
        for m in sorted(glob.glob(pattern)):
            candidates.append((label, Path(m)))

    for label, path in candidates:
        tried.append(f"  - {label}: {path}")
        if not path.is_file():
            continue
        key = _parse_env_file(path).get("AI_GATEWAY_API_KEY")
        if key:
            src = f"{label} ({path})"
            return (key, src) if return_source else key
        tried.append("    (file exists but sets no AI_GATEWAY_API_KEY)")

    raise JevUnavailable(
        "AI_GATEWAY_API_KEY not found.\n\nSearched:\n"
        "  - AI_GATEWAY_API_KEY env var (unset)\n"
        + ("\n".join(tried) if tried else "  (no candidate paths)")
        + f"\n\nFix: add AI_GATEWAY_API_KEY=vck_... to\n  MoxyWolf Vault/{VAULT_REL}"
    )


def _request_body(state, questions: dict) -> str:
    return json.dumps({"model": MODEL, "state": state, "questions": questions})


def _ask(key: str, state, questions: dict) -> dict:
    """POST one evaluate call.

    curl rather than urllib: a python.org build with no CA bundle installed
    fails cert verification on every HTTPS call, and curl uses the system trust
    store. Measured on the Release Owner's Mac, where urllib could not reach the
    gateway at all.

    The auth header goes through --config on stdin and the body through a 0600
    temp file, so the key never appears in argv where `ps` would show it.
    """
    body = _request_body(state, questions)
    fd, bodyfile = tempfile.mkstemp(prefix="jev.", suffix=".json")
    try:
        os.write(fd, body.encode())
        os.close(fd)
        cfg = (f'header = "Authorization: Bearer {key}"\n'
               'header = "Content-Type: application/json"\n')
        p = subprocess.run(
            ["curl", "-sS", "--config", "-", "-X", "POST", "--max-time", "30",
             "-d", "@" + bodyfile, ENDPOINT],
            input=cfg, capture_output=True, text=True)
    finally:
        os.unlink(bodyfile)
    if p.returncode != 0:
        raise JevUnavailable(f"curl failed rc={p.returncode}: {p.stderr[:200]}")
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise JevUnavailable(f"unparseable gateway response: {p.stdout[:200]}")
    if "answers" not in out:
        raise JevUnavailable(f"gateway error: {json.dumps(out)[:300]}")
    return out


def route(query: str, budget=None, *, key=None):
    """Ask Jev the four routing questions in one call.

    Returns the feature/decision dict the smart-router's Step 1 and Step 3
    produce, with `routing_source: "jev"` and calibrated probabilities in place
    of hand-picked confidences.
    """
    key = key or load_gateway_key()
    state = {"query": query}
    if budget is not None:
        state["budget_usd"] = budget

    questions = {
        "category": {
            "type": "choice",
            "instructions": "What kind of question is this? Judge the query itself, not its topic area.",
            "criteria": CATEGORIES,
        },
        "protocol": {
            "type": "choice",
            "instructions": ("Which deliberation protocol suits this query? Reasoning and "
                             "judgement questions take voting; questions with one correct "
                             "answer that models should agree on take consensus."),
            "criteria": {
                "voting": "Open reasoning where independent positions should be weighed against each other.",
                "consensus": "A knowable answer where agreement between models is the signal.",
            },
        },
        "compound": {
            "type": "boolean",
            "instructions": "Does the query ask two or more distinct questions rather than one?",
            "criteria": {
                "true": "Two or more separable questions are being asked at once.",
                "false": "One question, however long or detailed.",
            },
        },
        "deliberate": {
            "type": "boolean",
            "instructions": ("Would asking several independent frontier models and comparing "
                             "their answers materially change the answer this query gets, "
                             "compared with asking one good model?"),
            "criteria": {
                "true": ("Judgement, tradeoffs, contested ground, high stakes, or an answer "
                         "that competent models would disagree about."),
                "false": ("A single competent model would give substantially the same answer, "
                          "so extra models would cost time and money for nothing."),
            },
        },
    }

    out = _ask(key, state, questions)
    a = out["answers"]

    def pick(name):
        node = a.get(name, {})
        return node.get("choice") or node.get("value"), node.get("probabilities") or {}

    category, cat_probs = pick("category")
    protocol, proto_probs = pick("protocol")
    p_delib = a.get("deliberate", {}).get("probability")
    p_compound = a.get("compound", {}).get("probability")
    if p_delib is None or category is None:
        raise JevUnavailable("gateway answered without the fields the router needs")

    # Calibrated distance from the 0.5 boundary. An answer at 0.5 is a coin flip
    # and must read as one, which is what sends it to the exploration branch.
    confidence = round(abs(p_delib - 0.5) * 2, 3)

    # The router's three bands, from smart-router Step 4b, applied to a calibrated
    # probability instead of a hand-picked one. The bottom band is why this is not a
    # bare threshold: below 0.5 confidence the skill deliberates ON PURPOSE, because
    # an uncertain route that deliberates produces the outcome the learned router
    # trains on, while an uncertain route that shortcuts produces nothing and may be
    # wrong. Conservative by design, per the Step 3 table's catchall.
    if confidence < 0.5:
        decision, exploration = "deliberate", True
    else:
        decision, exploration = ("deliberate" if p_delib >= 0.5 else "single_model"), False

    return {
        "decision": decision,
        "confidence": confidence,
        "uncertain": 0.5 <= confidence <= 0.8,
        "exploration": exploration,
        "category": category,
        "estimated_protocol": protocol,
        "complexity_signals": {"is_compound": bool(p_compound and p_compound >= 0.5)},
        "routing_source": "jev",
        "model": out.get("model", MODEL),
        "probabilities": {
            "deliberate": p_delib,
            "compound": p_compound,
            "category": cat_probs,
            "protocol": proto_probs,
        },
        "usage": out.get("usage", {}),
    }


CHECKS = [
    ("What is the syntax for a Python list comprehension?", "single_model", "factual_lookup"),
    ("Should we move the lexicon store from Postgres to a graph database, and what "
     "would we lose? Walk me through the tradeoffs.", "deliberate", None),
    ("Fix the off-by-one in this loop: for i in range(len(xs)-1)", "single_model", None),
]


# Canned gateway answers, one per CHECKS entry and in the same order, plus the
# band the confidence should land in. The offline selftest routes each CHECKS
# query through them, so the table the live check uses is the one checked here.
CANNED = [
    ({"category": {"choice": "factual_lookup"}, "protocol": {"choice": "consensus"},
      "compound": {"probability": 0.05}, "deliberate": {"probability": 0.04}}, "follow"),
    ({"category": {"choice": "architecture_decision"}, "protocol": {"choice": "voting"},
      "compound": {"probability": 0.9}, "deliberate": {"probability": 0.97}}, "follow"),
    ({"category": {"choice": "code_implementation"}, "protocol": {"choice": "consensus"},
      "compound": {"probability": 0.1}, "deliberate": {"probability": 0.12}}, "flag"),
]


def _band(r):
    return "explore" if r["exploration"] else ("flag" if r["uncertain"] else "follow")


def selftest_offline():
    """Everything route() does except the HTTP call: request, parsing, routing.

    _ask is swapped for a stub, so this loads no key and makes no network call.
    It is the check run_all_tests.py runs, on every machine (XE-026).
    """
    global _ask
    sent, results = [], []
    reply = {}

    def stub(key, state, questions):
        sent.append((state, questions))
        return reply

    def check(name, ok):
        results.append(ok)
        print("  %-4s %s" % ("ok" if ok else "FAIL", name))

    real, _ask = _ask, stub
    try:
        # The request.
        reply = {"answers": CANNED[0][0]}
        route("q", budget=0.05, key="stub")
        state, qs = sent[-1]
        check("state carries query and budget", state == {"query": "q", "budget_usd": 0.05})
        route("q", key="stub")
        check("no budget, no budget_usd", sent[-1][0] == {"query": "q"})
        types = {k: v.get("type") for k, v in qs.items()}
        check("four questions, typed", types == {"category": "choice", "protocol": "choice",
                                                  "compound": "boolean", "deliberate": "boolean"})
        check("category criteria are CATEGORIES", qs["category"]["criteria"] == CATEGORIES)
        check("every question has instructions and criteria",
              all(v.get("instructions") and v.get("criteria") for v in qs.values()))
        check("boolean criteria are true/false",
              all(set(qs[k]["criteria"]) == {"true", "false"} for k in ("compound", "deliberate")))
        check("request body names the model",
              json.loads(_request_body(state, qs))["model"] == MODEL)

        # Parsing and routing, for each CHECKS query.
        for (query, want_decision, want_category), (answers, want_band) in zip(CHECKS, CANNED):
            reply = {"answers": answers}
            r = route(query, key="stub")
            check("%s -> %s/%s" % (query[:36], want_decision, want_band),
                  r["decision"] == want_decision and _band(r) == want_band
                  and r["category"] == (want_category or answers["category"]["choice"])
                  and r["estimated_protocol"] == answers["protocol"]["choice"]
                  and r["complexity_signals"]["is_compound"]
                  == (answers["compound"]["probability"] >= 0.5)
                  and r["model"] == MODEL and r["routing_source"] == "jev")

        # A coin flip deliberates on purpose, flagged as exploration.
        reply = {"answers": dict(CANNED[0][0], deliberate={"probability": 0.6})}
        r = route("q", key="stub")
        check("p=0.6 explores", r["decision"] == "deliberate" and _band(r) == "explore")

        # An answer missing a field the router needs is unavailable, not a guess.
        for missing in ("deliberate", "category"):
            reply = {"answers": {k: v for k, v in CANNED[0][0].items() if k != missing}}
            try:
                route("q", key="stub")
                check("no %s raises JevUnavailable" % missing, False)
            except JevUnavailable:
                check("no %s raises JevUnavailable" % missing, True)
    finally:
        _ask = real

    bad = results.count(False)
    print("\n%d/%d offline cases" % (len(results) - bad, len(results)))
    return 1 if bad or not results else 0


def selftest_live():
    """The live check: Jev must separate a lookup from a real tradeoff question.

    Exit 3 with no key (skipped, nothing examined), 2 if the gateway fails.
    """
    try:
        key, src = load_gateway_key(return_source=True)
    except JevUnavailable as e:
        print("SKIPPED: no gateway key, nothing examined\n%s" % e)
        return 3
    print("key from:", src)
    bad = 0
    for query, want_decision, want_category in CHECKS:
        try:
            r = route(query, key=key)
        except JevUnavailable as e:
            print("gateway failed: %s" % e)
            return 2
        ok = r["decision"] == want_decision and (want_category is None
                                                 or r["category"] == want_category)
        bad += 0 if ok else 1
        print("  %-4s %-13s conf %-5s %-22s  %s"
              % ("ok" if ok else "FAIL", r["decision"], r["confidence"],
                 r["category"], query[:44]))
        if not ok:
            print("       wanted %s / %s" % (want_decision, want_category))
    print("\n%d/%d" % (len(CHECKS) - bad, len(CHECKS)))
    return 1 if bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip().split("\n")[0])
        print("\nusage: jev_route.py <query> [--budget USD]\n       jev_route.py --selftest [--live]"
              "\n       jev_route.py --where")
        sys.exit(0)
    if args[0] == "--selftest":
        sys.exit(selftest_live() if "--live" in args[1:] else selftest_offline())
    if args[0] == "--where":
        try:
            _, src = load_gateway_key(return_source=True)
            print(src)
            sys.exit(0)
        except JevUnavailable as e:
            print(e, file=sys.stderr)
            sys.exit(1)
    budget = None
    if "--budget" in args:
        i = args.index("--budget")
        budget = float(args[i + 1])
        args = args[:i] + args[i + 2:]
    try:
        print(json.dumps(route(" ".join(args), budget=budget), indent=2))
    except JevUnavailable as e:
        print(json.dumps({"routing_source": "jev_unavailable", "why": str(e)}, indent=2))
        sys.exit(2)
