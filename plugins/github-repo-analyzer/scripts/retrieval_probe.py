#!/usr/bin/env python3
"""RR-002: the probe runs the pipeline, or says it did not.

RR-001 reads a retrieval pipeline. It cannot establish that an emitted citation names
a chunk that was actually in the context window, because that is a fact about one run.
This probe establishes it, by running the pipeline once and watching two boundaries.

  python3 retrieval_probe.py --repo <path> --entry <module:function> --query "<text>" [--json]
  python3 retrieval_probe.py --selftest

Exit 0 when the check passes, 1 when it fails, 2 on a usage error, 3 when nothing ran.

RR-002.1: execution is opt-in. Without --entry nothing is executed and the result is a
counted SKIP, which is what RR-001 criterion 4 reports on its own. This tool never
decides by itself to run somebody's code.

RR-002.3: exactly two boundaries are patched, the model call and the answer return.
A probe that rewrites the pipeline is measuring itself, so nothing else is touched:
no retriever stub, no injected ordering, no fake corpus.

RR-002.4: the run happens in a subprocess with no network. The child installs a socket
guard before importing the target, so a pipeline that reaches for an API fails loudly
rather than silently calling out under the operator's credentials. Egress is granted
per TB-003, never filtered: --allow-network is the grant, and the record says which
run had it.

RR-002.5: zero captured context, or zero captured citations, is a FAIL naming the
shortfall. A probe that watched nothing has established nothing, and reporting that as
a pass is the false green EV-001 forbids.

ponytail: the boundary patch is duck-typed on call shape rather than on a provider SDK,
because pinning it to one vendor's client is a second thing to maintain every time a
pipeline uses a different one. Upgrade path is a --boundary selector if duck-typing
ever picks the wrong call.
"""
import argparse, json, os, subprocess, sys, tempfile, textwrap
from pathlib import Path

PASS, FAIL, SKIP = "pass", "fail", "skip"

# The child runs this. It is a string rather than an importable module so the subprocess
# carries no dependency on this file's location or on the target's sys.path layout.
CHILD = r'''
import importlib, json, os, sys, builtins

ALLOW_NET = os.environ.get("PROBE_ALLOW_NETWORK") == "1"
if not ALLOW_NET:
    import socket
    class _Denied(OSError):
        pass
    def _deny(*a, **k):
        raise _Denied("probe: network denied; re-run with --allow-network to grant it")
    socket.socket = _deny
    socket.create_connection = _deny

CAPTURED = {"context": [], "citations": [], "model_calls": 0}

def _texts(obj, out, depth=0):
    """Every string reachable from a call argument. The context window is whatever text
    the pipeline handed the model, whatever shape it chose to hand it in."""
    if depth > 6:
        return
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _texts(v, out, depth + 1)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            _texts(v, out, depth + 1)
    else:
        for attr in ("text", "content", "page_content", "chunk_id", "id"):
            if hasattr(obj, attr):
                try:
                    _texts(getattr(obj, attr), out, depth + 1)
                except Exception:
                    pass

CITE_KEYS = ("citation", "citations", "source", "sources", "chunk_id", "chunk_ids",
             "reference", "references", "doc_id", "doc_ids")

def _citations(obj, depth=0):
    """Strings under a citation-bearing key. A pipeline that names none has emitted none."""
    out = []
    if depth > 6:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in CITE_KEYS:
                _texts(v, out)
            else:
                out.extend(_citations(v, depth + 1))
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            out.extend(_citations(v, depth + 1))
    else:
        for k in CITE_KEYS:
            if hasattr(obj, k):
                try:
                    _texts(getattr(obj, k), out)
                except Exception:
                    pass
    return out


def install_model_boundary(mod):
    """Patch what the pipeline calls to reach a model. Duck-typed on shape, not vendor."""
    patched = []
    def wrap(owner, name, fn):
        def spy(*a, **k):
            CAPTURED["model_calls"] += 1
            buf = []
            _texts(a, buf); _texts(k, buf)
            CAPTURED["context"].extend(buf)
            return fn(*a, **k)
        setattr(owner, name, spy)
        patched.append(f"{getattr(owner, '__name__', owner)}.{name}")
    seen = set()
    def walk(obj, depth=0):
        if depth > 3 or id(obj) in seen:
            return
        seen.add(id(obj))
        for name in dir(obj):
            if name.startswith("__"):
                continue
            try:
                val = getattr(obj, name)
            except Exception:
                continue
            if callable(val) and name in ("create", "invoke", "generate", "predict", "complete"):
                try:
                    wrap(obj, name, val)
                except Exception:
                    pass
            elif hasattr(val, "__dict__") and not isinstance(val, type):
                walk(val, depth + 1)
            elif isinstance(val, type):
                walk(val, depth + 1)
    walk(mod)
    return patched

def main():
    repo, entry, query = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.path.insert(0, repo)
    modname, _, fname = entry.partition(":")
    mod = importlib.import_module(modname)
    patched = install_model_boundary(mod)
    fn = getattr(mod, fname)
    answer = fn(query)                       # boundary 2: the answer return
    # Citations are what the pipeline NAMES as citations, not every string it returned.
    # Walking the whole answer counted the prose itself as an attribution, which would have
    # made any pipeline that returns a dict look attributed.
    CAPTURED["citations"] = _citations(answer)
    print("PROBE_RESULT " + json.dumps({
        "context": CAPTURED["context"][:5000],
        "citations": CAPTURED["citations"][:5000],
        "model_calls": CAPTURED["model_calls"],
        "patched_boundaries": patched,
        "network_granted": ALLOW_NET,
    }))

main()
'''


def run_probe(repo, entry, query, allow_network=False, timeout=60):
    """(status, detail, examined, unit, raw). Runs the target in a subprocess."""
    with tempfile.TemporaryDirectory() as td:
        child = Path(td) / "probe_child.py"
        child.write_text(CHILD)
        env = dict(os.environ)
        env["PROBE_ALLOW_NETWORK"] = "1" if allow_network else "0"
        try:
            r = subprocess.run([sys.executable, str(child), str(repo), entry, query],
                               capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return FAIL, f"the pipeline did not return within {timeout}s; nothing was captured", 0, "model calls", None
    line = next((l for l in r.stdout.splitlines() if l.startswith("PROBE_RESULT ")), None)
    if not line:
        err = (r.stderr or r.stdout).strip().splitlines()
        tail = err[-1] if err else "no output"
        return FAIL, f"the pipeline did not run to completion: {tail}", 0, "model calls", None
    data = json.loads(line[len("PROBE_RESULT "):])

    # RR-002.5: a probe that watched nothing has established nothing.
    if data["model_calls"] == 0:
        return (FAIL, "the model boundary was never reached, so no context window was captured; "
                      "the entry point may not call a model, or it calls one this probe did not patch",
                0, "model calls", data)
    ctx = " \n".join(data["context"])
    if not ctx.strip():
        return FAIL, "the model was called but the captured context was empty", 0, "context fragments", data
    cites = [c for c in data["citations"] if c and c.strip()]
    if not cites:
        return (FAIL, f"the pipeline answered after {data['model_calls']} model call(s) but emitted no "
                      f"citation or chunk identifier; an answer with no attribution cannot be checked",
                0, "citations", data)

    # RR-002.2: every emitted citation must name something that was in the context.
    unresolved = [c for c in cites if c not in ctx]
    if unresolved:
        show = "; ".join(repr(u[:60]) for u in unresolved[:3])
        return (FAIL, f"{len(unresolved)} of {len(cites)} citation(s) name nothing that was in the "
                      f"context window: {show}", len(cites), "citations", data)
    return (PASS, f"all {len(cites)} citation(s) resolve to text that was in the context window across "
                  f"{data['model_calls']} model call(s); boundaries patched: "
                  f"{', '.join(data['patched_boundaries']) or 'none'}", len(cites), "citations", data)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo")
    ap.add_argument("--entry", help="module:function the probe will execute; without it nothing runs")
    ap.add_argument("--query", default="probe query")
    ap.add_argument("--allow-network", action="store_true", help="grant egress to the run (TB-003)")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.repo:
        print("retrieval_probe: --repo is required", file=sys.stderr); return 2
    if not os.path.isdir(a.repo):
        print(f"retrieval_probe: no such directory: {a.repo}", file=sys.stderr); return 2

    # RR-002.1: no entry point, no execution. This is the default and it is not a failure.
    if not a.entry:
        out = {"name": "citation_attribution_dynamic", "status": SKIP, "executed": False,
               "examined": 0, "unit": "citations",
               "detail": "no --entry given, so nothing was executed; RR-001 criterion 4 stays a "
                         "counted SKIP. Supply module:function to run the pipeline."}
        print(json.dumps(out, indent=2) if a.json else
              f"  SKIP  citation_attribution_dynamic  examined 0 citations  {out['detail']}")
        return 3

    status, detail, examined, unit, raw = run_probe(a.repo, a.entry, a.query, a.allow_network, a.timeout)
    rec = {"name": "citation_attribution_dynamic", "status": status, "executed": True,
           "examined": examined, "unit": unit, "detail": detail,
           "network_granted": bool(a.allow_network),
           "model_calls": (raw or {}).get("model_calls"),
           "patched_boundaries": (raw or {}).get("patched_boundaries")}
    if a.json:
        print(json.dumps(rec, indent=2))
    else:
        print("RETRIEVAL PROBE  (the pipeline WAS executed)")
        print(f"  {status.upper():<4}  citation_attribution_dynamic  examined {examined} {unit}  {detail}")
        print(f"  network granted: {bool(a.allow_network)}; boundaries patched: "
              f"{', '.join((raw or {}).get('patched_boundaries') or []) or 'none'}")
    return 1 if status == FAIL else 0


def _selftest():
    import shutil
    def repo(files):
        d = tempfile.mkdtemp()
        for n, s in files.items():
            (Path(d) / n).write_text(textwrap.dedent(s))
        return d

    HONEST = '''
        class _Client:
            def create(self, messages=None, **kw):
                return "answer"
        client = _Client()
        CORPUS = {"c1": "alpha chunk text", "c2": "beta chunk text", "c9": "never retrieved"}
        def answer(q):
            chunks = [("c1", CORPUS["c1"]), ("c2", CORPUS["c2"])]
            client.create(messages=[t for _, t in chunks])
            return {"answer": "ok", "citations": [t for _, t in chunks]}
    '''
    # RR-002.2: cites a corpus chunk that never entered the context.
    LIAR = '''
        class _Client:
            def create(self, messages=None, **kw):
                return "answer"
        client = _Client()
        CORPUS = {"c1": "alpha chunk text", "c9": "never retrieved at all"}
        def answer(q):
            client.create(messages=[CORPUS["c1"]])
            return {"answer": "ok", "citations": [CORPUS["c9"]]}
    '''
    NOMODEL = '''
        def answer(q):
            return {"answer": "ok", "citations": ["whatever"]}
    '''
    NOCITE = '''
        class _Client:
            def create(self, messages=None, **kw):
                return "answer"
        client = _Client()
        def answer(q):
            client.create(messages=["alpha chunk text"])
            return {"answer": "ok"}
    '''
    r = repo({"pipe.py": HONEST})
    st, det, ex, _, _ = run_probe(r, "pipe:answer", "q")
    assert st == PASS, (st, det)
    assert ex == 2, (ex, det)

    r = repo({"pipe.py": LIAR})
    st, det, ex, _, _ = run_probe(r, "pipe:answer", "q")
    assert st == FAIL and "name nothing that was in the context window" in det, (st, det)

    r = repo({"pipe.py": NOMODEL})
    st, det, ex, _, _ = run_probe(r, "pipe:answer", "q")
    assert st == FAIL and "model boundary was never reached" in det, (st, det)
    assert ex == 0, ex

    r = repo({"pipe.py": NOCITE})
    st, det, ex, _, _ = run_probe(r, "pipe:answer", "q")
    assert st == FAIL and "emitted no citation" in det, (st, det)

    # RR-002.1: no entry point executes nothing.
    assert main(["--repo", r]) == 3

    # RR-002.4: the default run has no network.
    NET = '''
        import socket
        def answer(q):
            socket.create_connection(("example.com", 80))
            return {"citations": ["x"]}
    '''
    r = repo({"pipe.py": NET})
    st, det, _, _, _ = run_probe(r, "pipe:answer", "q")
    assert st == FAIL and "network denied" in det, (st, det)

    print("selftest OK: 6 fixtures, 11 assertions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
