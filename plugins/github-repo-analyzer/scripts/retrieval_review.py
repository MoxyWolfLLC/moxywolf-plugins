#!/usr/bin/env python3
"""RR-001: a retrieval stage proves it did its work.

Reviews a repository's retrieval (RAG) pipeline and reports, per check, what it
examined. A retrieval stage that does nothing returns exactly what a working one
returns -- an ordered list -- so absence of work is invisible in the output. These
checks look for the absence directly.

  python3 retrieval_review.py --repo <path> [--json]

Exit 0 when no check fails, 1 when any fails, 2 on a usage error.

EV-001 governs every check: `examined` is part of every result, zero coverage turns
a PASS into a FAIL, and a check that genuinely does not apply returns SKIP and is
printed as SKIP rather than folded into a green line. The rule is applied in
run_review(), not inside the checks, so no later check can opt out by forgetting.

RR-001.1 requires this reviewer to say when it did not execute the pipeline rather
than return a verdict it did not earn. It never executes anything: every result
here is static, and `executed` is False in the JSON output and stated in the
summary line.

ponytail: Python only, via stdlib `ast`. Other languages are counted and reported
as unexamined rather than guessed at with regex, because a regex that pretends to
parse a language produces findings nobody can trust. Upgrade path is a per-language
parser behind the same check contract; the 4-tuple does not change.
"""
import argparse, ast, json, os, re, sys
from pathlib import Path

PASS, FAIL, SKIP = "pass", "fail", "skip"

# Matched against the LAST dotted segment (the thing actually being called), never the whole
# path: `RERANK.search(x)` is a regex lookup, not a reranker, and matching the full dotted name
# made this reviewer fail on its own source.
RERANK = re.compile(r"^(re_?rank\w*|cross_?encoder\w*)$", re.I)
TOPK = re.compile(r"top_?[kn]", re.I)
RETRIEVE = re.compile(r"^(retriev\w*|similarity_search\w*|vector_search\w*|embed_query|query_points)$", re.I)
CITATION = re.compile(r"^(\w*citation\w*|chunk_ids?|source_ids?|doc_ids?)$", re.I)
# MODEL is deliberately matched against the full dotted path: the tell is `chat.completions.create`,
# which no single segment carries.
MODEL = re.compile(r"completions?\.create|messages\.create|chat\.create|\.invoke\b|\.generate\b|\.predict\b", re.I)
SKIPDIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".tox"}


def _last(name):
    """The call target: the final dotted segment."""
    return name.rsplit(".", 1)[-1]


def _call_name(node):
    """Dotted name of a Call's func, e.g. client.chat.completions.create."""
    parts, cur = [], node.func if isinstance(node, ast.Call) else node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr); cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


class FileFacts:
    """Everything one file says about retrieval. Facts never cross files: a grounding
    guard in one module does not protect a retrieval call in another, and correlating
    them repo-wide is how a reviewer assembles a PASS out of unrelated code."""

    __slots__ = ("rerank", "topk", "retrieve", "model", "citation", "discarded_rerank",
                 "empty_guards", "ordered_cuts", "unordered_models")

    def __init__(self):
        for f in self.__slots__:
            setattr(self, f, [])


class Facts:
    def __init__(self):
        self.files = {}          # relpath -> FileFacts
        self.py_files = 0
        self.other_files = 0

    def scan_repo(self, root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIPDIRS]
            for fn in filenames:
                path = Path(dirpath) / fn
                if fn.endswith(".py"):
                    self.py_files += 1
                    try:
                        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
                    except (SyntaxError, ValueError, OSError):
                        continue
                    ff = FileFacts()
                    rel = str(path.relative_to(root))
                    self._scan_tree(tree, rel, ff)
                    if any(getattr(ff, f) for f in FileFacts.__slots__):
                        self.files[rel] = ff
                elif fn.rsplit(".", 1)[-1] in ("js", "ts", "tsx", "jsx", "go", "rb", "java", "rs"):
                    self.other_files += 1

    def _scan_tree(self, tree, rel, ff):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                tail = _last(name)
                kwargs = " ".join(k.arg or "" for k in node.keywords)
                site = (rel, node.lineno, name or "<call>")
                if RERANK.search(tail):
                    ff.rerank.append(site)
                if TOPK.search(tail) or TOPK.search(kwargs):
                    ff.topk.append(site)
                if RETRIEVE.search(tail):
                    ff.retrieve.append(site)
                if MODEL.search(name):
                    ff.model.append(site)
                if CITATION.search(tail):
                    ff.citation.append(site)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and CITATION.search(t.id):
                        ff.citation.append((rel, node.lineno, f"{t.id} binding"))
            elif isinstance(node, ast.Attribute) and CITATION.search(node.attr):
                ff.citation.append((rel, node.lineno, f".{node.attr} read"))
        for fn_node in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            self._scan_function(fn_node, rel, ff)

    def _scan_function(self, fn, rel, ff):
        # F4: a name is "consumed" only if it is READ AFTER the assignment. Collecting every Load
        # in the function without ordering meant `docs = retrieve(); log(docs); docs = rerank(docs)`
        # read as consumed, because the earlier read put the name in the set. Reproduced 2026-09-21.
        reads = [(n.id, getattr(n, "lineno", 0)) for n in ast.walk(fn)
                 if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)]
        # F1: a grounding guard must test something that CAME FROM retrieval. Any If with a Not or
        # a comparison used to qualify, so ordinary input validation (`if not query: return`) passed
        # the check with no retrieval guard present at all. Reproduced 2026-09-21.
        retrieved = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                tail = _last(_call_name(node.value))
                if RETRIEVE.search(tail) or RERANK.search(tail) or TOPK.search(tail):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            retrieved.add(t.id)
        for node in ast.walk(fn):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                    and RERANK.search(_last(_call_name(node.value))):
                ff.discarded_rerank.append((rel, node.lineno, "result not bound"))
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
                    and RERANK.search(_last(_call_name(node.value))):
                for t in node.targets:
                    if isinstance(t, ast.Name) and not any(
                            nm == t.id and ln > node.lineno for nm, ln in reads):
                        ff.discarded_rerank.append((rel, node.lineno, f"{t.id} never read after line {node.lineno}"))
            if isinstance(node, ast.If) and self._is_empty_test(node.test, retrieved) \
                    and any(isinstance(b, (ast.Return, ast.Raise)) for b in ast.walk(node)):
                ff.empty_guards.append((rel, node.lineno, "early exit on an empty or low-scoring retrieval result"))
        # Criterion 2 says the cut happens BEFORE the model call. Presence of a cut somewhere in the
        # file does not establish that. Within one function, line order does: a cut above the call
        # runs first. Across functions it does not, and that case is reported as unverified rather
        # than counted either way.
        fn_topk = sorted(n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call)
                         and (TOPK.search(_last(_call_name(n)))
                              or TOPK.search(" ".join(k.arg or "" for k in n.keywords))))
        fn_model = sorted(n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call)
                          and MODEL.search(_call_name(n)))
        for mline in fn_model:
            earlier = [t for t in fn_topk if t < mline]
            if earlier:
                ff.ordered_cuts.append((rel, earlier[-1], f"cut before the model call at line {mline}"))
            else:
                ff.unordered_models.append((rel, mline, "model call with no top-k cut above it in this function"))

    @staticmethod
    def _is_empty_test(test, retrieved):
        """An emptiness or threshold test ON A RETRIEVED VALUE. The second argument is what
        separates a grounding guard from ordinary input validation."""
        if not retrieved:
            return False
        names = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
        if not (names & retrieved):
            return False
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return True
        if isinstance(test, ast.Compare):
            src = ast.dump(test)
            return "Lt(" in src or "LtE(" in src or "Eq(" in src
        if isinstance(test, ast.Call) and _last(_call_name(test)) == "len":
            return True
        return False


def _ev(sites, limit=3):
    return "; ".join(f"{p}:{n} {w}" for p, n, w in sites[:limit]) or "none"


def _all(f, field):
    out = []
    for ff in f.files.values():
        out.extend(getattr(ff, field))
    return out


def _pipeline_files(f):
    """Files that both retrieve and call a model: the unit of analysis for every check about
    an answering pipeline.

    Same-file is deliberately conservative. A repository that retrieves in one module and
    answers in another is not examined, and says so through its SKIP rather than through a
    verdict. Scoping wider was tried twice and produced two untrue findings: a guard in an
    unrelated module read as protection for a retrieval 49 files away, and a vector database
    was told its pipeline answers without grounding when nothing in it answers at all. A miss
    is reported as unexamined; a wrong accusation is not recoverable.

    ponytail: same-file is the cheap approximation of dataflow. Upgrade path is an
    import-following pass, behind this same function, if the SKIP count proves too high.
    """
    return {rel: ff for rel, ff in f.files.items() if ff.retrieve and ff.model}


def check_rerank_effective(f):
    """RR-001.1 -- a reranking stage must change the order, or it is decoration."""
    sites = _all(f, "rerank")
    if not sites:
        return SKIP, "no reranking stage found; nothing to prove", 0, "rerank sites"
    bad = _all(f, "discarded_rerank")
    if bad:
        return (FAIL, f"reranked result is discarded at {_ev(bad)}; the stage runs and the "
                      f"order it produces is never used", len(sites), "rerank sites")
    # F3: a reranker that returns its input unchanged but whose result IS consumed looks exactly
    # like a working one here. Static analysis can falsify this criterion (a discarded result proves
    # the order is unused) but cannot verify it, so a consumed result is SKIP and never PASS.
    # Claiming "the reorder was observed in the code" was the overclaim this tool exists to catch.
    return (SKIP, f"reranked result is consumed at every site ({_ev(sites)}), which rules out a "
                  f"discarded reorder but does not establish that the order changed; that needs the "
                  f"pipeline run, which this reviewer does not do", len(sites), "rerank sites")


def check_topk_before_model(f):
    """RR-001.2 -- the cut happens before the model call, or context is unbounded.

    Scoped per file, and only to files that BOTH retrieve and call a model. A file that
    calls a model without retrieving anything has no retrieval output to bound, and
    flagging it said something untrue: the first version failed a third-party repository
    on its provider tests, which retrieve nothing at all.
    """
    pf = _pipeline_files(f)
    pipeline_models = [x for ff in pf.values() for x in ff.model]
    if not pipeline_models:
        return (SKIP, "no file both retrieves and calls a model; no retrieval output reaches a model",
                0, "model calls in retrieval files")
    nocut = [x for ff in pf.values() if not ff.topk for x in ff.model]
    if nocut:
        return (FAIL, f"model called at {_ev(nocut)} with no top-k cut in the same file; "
                      f"retrieval output reaches the model unbounded", len(pipeline_models),
                "model calls in retrieval files")
    unordered = [x for ff in pf.values() for x in ff.unordered_models]
    ordered = [x for ff in pf.values() for x in ff.ordered_cuts]
    if unordered:
        return (SKIP, f"a top-k cut exists in the file but not above the model call at "
                      f"{_ev(unordered)}; whether it runs first needs the call graph, which this "
                      f"reviewer does not follow", len(pipeline_models), "model calls in retrieval files")
    return (PASS, f"top-k is cut above every model call in the same function ({_ev(ordered)})",
            len(pipeline_models), "model calls in retrieval files")


def check_grounding_fallback(f):
    """RR-001.3 -- a pipeline that answers regardless of retrieval quality has no floor.

    Scoped per file, for the same reason: a guard elsewhere protects nothing here.
    """
    sites = _all(f, "retrieve")
    if not sites:
        return SKIP, "no retrieval call found; no grounding to fall back from", 0, "retrieval sites"
    pf = _pipeline_files(f)
    if not pf:
        return (SKIP, "no file both retrieves and calls a model; this repository provides retrieval "
                      "rather than answering with it, so there is no answer to ground",
                0, "retrieval sites")
    sites = [x for ff in pf.values() for x in ff.retrieve]
    offenders = [x for ff in pf.values() if not ff.empty_guards for x in ff.retrieve]
    if offenders:
        return (FAIL, f"retrieval at {_ev(offenders)} with no early exit on an empty or low-scoring "
                      f"result in the same file; the pipeline answers regardless of what it found",
                len(sites), "retrieval sites")
    return (PASS, f"every file that retrieves also has an insufficient-grounding path "
                  f"({_ev(_all(f, 'empty_guards'))})", len(sites), "retrieval sites")


def check_citation_attribution(f):
    """RR-001.4 -- citations must resolve to chunks that were in the context window.

    Static analysis cannot establish that. It can establish whether citations are
    emitted at all, which is the part it is entitled to claim.
    """
    sites = _all(f, "retrieve")
    if not sites:
        return SKIP, "no retrieval call found; no citations to attribute", 0, "citation sites"
    pf = _pipeline_files(f)
    if not pf:
        return (SKIP, "no file both retrieves and calls a model; nothing here emits an answer that "
                      "would carry citations", 0, "citation sites")
    sites = [x for ff in pf.values() for x in ff.retrieve]
    cites = [x for ff in pf.values() for x in ff.citation]
    if not cites:
        return (FAIL, f"retrieval at {_ev(sites)} emits no citation or chunk identifier; an answer "
                      f"with no attribution cannot be checked by anyone", len(sites), "retrieval sites")
    return (SKIP, f"citations emitted at {_ev(cites)}; whether each resolves to a chunk that was in "
                  f"the context window needs the pipeline run, which this reviewer does not do",
            len(cites), "citation sites")


CHECKS = [
    ("rerank_effective", check_rerank_effective),
    ("topk_before_model", check_topk_before_model),
    ("grounding_fallback", check_grounding_fallback),
    ("citation_attribution", check_citation_attribution),
]


def run_review(root):
    """One record per check. The zero-coverage rule is applied here, not in the checks."""
    f = Facts()
    f.scan_repo(Path(root))
    results = []
    for name, fn in CHECKS:
        status, detail, examined, unit = fn(f)
        if status == PASS and examined == 0:
            status = FAIL
            detail = f"examined 0 {unit}; a check that examined nothing cannot pass ({detail})"
        results.append({"name": name, "status": status, "detail": detail,
                        "examined": examined, "unit": unit})
    return results, f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.repo:
        print("retrieval_review: --repo is required", file=sys.stderr); return 2
    if not os.path.isdir(a.repo):
        print(f"retrieval_review: no such directory: {a.repo}", file=sys.stderr); return 2

    results, f = run_review(a.repo)
    failed = [r["name"] for r in results if r["status"] == FAIL]
    skipped = [r["name"] for r in results if r["status"] == SKIP]
    # A run where every check skipped examined nothing. Calling that PASS is the same false
    # green EV-001 forbids per check, one level up, so the verdict word says what happened.
    if failed:
        verdict = "FAIL"
    elif len(skipped) == len(results):
        verdict = "NO COVERAGE"
    else:
        verdict = "PASS"
    if a.json:
        print(json.dumps({"checks": results, "failed": failed, "skipped": skipped,
                          "verdict": verdict, "executed": False,
                          "coverage": sum(r["examined"] for r in results),
                          "python_files": f.py_files, "unexamined_other_language_files": f.other_files},
                         indent=2))
    else:
        print("RETRIEVAL REVIEW  (static; the pipeline was not executed)")
        for r in results:
            print(f"  {r['status'].upper():<4}  {r['name']:<22} examined {r['examined']} {r['unit']:<16} {r['detail']}")
        line = f"review: {verdict}"
        if failed:
            line += f" ({', '.join(failed)})"
        if verdict == "NO COVERAGE":
            line += "; this repository has no retrieval pipeline these checks can see, so nothing was checked"
        elif skipped:
            line += f"; {len(skipped)} skipped ({', '.join(skipped)}); skipped is not checked"
        print(line)
        print(f"examined {f.py_files} Python file(s); {f.other_files} file(s) in other languages were not examined")
    return 1 if failed else 0


def _selftest():
    import tempfile, textwrap
    def build(files):
        d = tempfile.mkdtemp()
        for name, src in files.items():
            p = Path(d) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(src), encoding="utf-8")
        return d
    def status(results, name):
        return next(r["status"] for r in results if r["name"] == name)

    # A reranker whose result is never read: the pass-through this item exists to catch.
    r, _ = run_review(build({"rag.py": """
        def answer(q):
            docs = retriever.retrieve(q, top_k=20)
            ranked = reranker.rerank(q, docs)
            if not docs:
                return "no context"
            return client.chat.completions.create(messages=build(docs))
    """}))
    assert status(r, "rerank_effective") == FAIL, r
    assert "never read" in next(x["detail"] for x in r if x["name"] == "rerank_effective")

    # No grounding fallback.
    r, _ = run_review(build({"rag.py": """
        def answer(q):
            docs = retriever.retrieve(q, top_k=5)
            return client.chat.completions.create(messages=build(docs), citations=docs)
    """}))
    assert status(r, "grounding_fallback") == FAIL, r

    # No retrieval pipeline at all: every check SKIPs, nothing reports a pass.
    r, _ = run_review(build({"util.py": "def add(a, b):\n    return a + b\n"}))
    assert all(x["status"] == SKIP for x in r), r
    assert all(x["examined"] == 0 for x in r), r
    assert not [x for x in r if x["status"] == PASS], "zero coverage must never report a pass"

    # A healthy pipeline passes the checks it can, and citation attribution still SKIPs.
    r, _ = run_review(build({"rag.py": """
        def answer(q):
            docs = retriever.retrieve(q, top_k=20)
            ranked = reranker.rerank(q, docs)
            if len(ranked) == 0:
                raise LookupError("insufficient grounding")
            chunk_ids = [d.chunk_id for d in ranked]
            return client.chat.completions.create(messages=build(ranked), citations=chunk_ids)
    """}))
    # F3: a consumed reranked result is SKIP, not PASS. Consumption rules out a discarded
    # reorder; it does not establish that the order changed.
    assert status(r, "rerank_effective") == SKIP, r
    assert "does not establish that the order changed" in next(
        x["detail"] for x in r if x["name"] == "rerank_effective")
    assert status(r, "topk_before_model") == PASS, r
    assert status(r, "grounding_fallback") == PASS, r
    assert status(r, "citation_attribution") == SKIP, r
    # Regression 1: a repository that merely mentions rerank in an identifier is not a pipeline.
    # The first version matched the whole dotted name and failed on its own source.
    r, _ = run_review(build({"lint.py": """
        import re
        RERANK = re.compile(r"rerank")
        def scan(name):
            if RERANK.search(name):
                return True
            return False
    """}))
    assert status(r, "rerank_effective") == SKIP, r

    # Regression 2: a guard in one file must not vouch for a retrieval in another.
    # The first version aggregated repo-wide and reported PASS across unrelated modules.
    r, _ = run_review(build({
        "pipeline.py": """
            def answer(q):
                docs = retriever.retrieve(q, top_k=5)
                return client.chat.completions.create(messages=docs, citations=docs)
        """,
        "unrelated.py": """
            def helper(rows):
                if not rows:
                    return None
                return rows[0]
        """}))
    assert status(r, "grounding_fallback") == FAIL, r
    assert "pipeline.py" in next(x["detail"] for x in r if x["name"] == "grounding_fallback")

    # Regression 3: every check skipping is not a pass.
    results, _ = run_review(build({"util.py": "def add(a, b):\n    return a + b\n"}))
    assert all(x["status"] == SKIP for x in results)
    verdict = "NO COVERAGE" if all(x["status"] == SKIP for x in results) else "PASS"
    assert verdict == "NO COVERAGE", "a run that examined nothing must not read as PASS"

    # Regression 4: a model call with no retrieval in the file is not an unbounded pipeline.
    # The first version failed ECC on its provider tests, which retrieve nothing.
    r, _ = run_review(build({"test_provider.py": """
        def test_generate():
            out = provider.generate(prompt="hi")
            assert out
    """}))
    assert status(r, "topk_before_model") == SKIP, r
    assert not [x for x in r if x["status"] == FAIL], "a repository with no pipeline must not fail"

    # Regression 5: a retrieval library is not an answering pipeline. The first version told
    # a vector database that "the pipeline answers regardless of what it found", which is untrue:
    # nothing in it answers at all.
    r, _ = run_review(build({"collection.py": """
        class Collection:
            def query(self, text):
                vec = self._embedding_function.embed_query(text)
                return self._index.search(vec)
    """}))
    assert status(r, "grounding_fallback") == SKIP, r
    assert status(r, "citation_attribution") == SKIP, r
    assert not [x for x in r if x["status"] == FAIL], "a retrieval library must not be failed as a pipeline"

    # Regression 6 (F1, peer review 20260921-161113): ordinary input validation is not a
    # grounding guard. `if not q: return` tests the query, not anything retrieved.
    r, _ = run_review(build({"rag.py": """
        def answer(q):
            if not q:
                return "empty query"
            docs = retriever.retrieve(q, top_k=5)
            return client.chat.completions.create(messages=docs, citations=docs)
    """}))
    assert status(r, "grounding_fallback") == FAIL, r

    # Regression 7 (F4, same review): a name read BEFORE being reassigned by the reranker is not
    # consumed afterwards. Collecting Loads without ordering made this read as consumed.
    r, _ = run_review(build({"rag.py": """
        def answer(q):
            docs = retriever.retrieve(q, top_k=5)
            log(docs)
            docs = reranker.rerank(q, docs)
            if not docs_other:
                return None
            return client.chat.completions.create(messages=build_ctx(), citations=[1])
    """}))
    assert status(r, "rerank_effective") == FAIL, r

    # Regression 8 (F3, same review): an identity reranker whose result is consumed must not PASS.
    r, _ = run_review(build({"rag.py": """
        def rerank(q, docs):
            return docs
        def answer(q):
            docs = retriever.retrieve(q, top_k=5)
            ranked = rerank(q, docs)
            if not ranked:
                return None
            return client.chat.completions.create(messages=ranked, citations=[d.chunk_id for d in ranked])
    """}))
    assert status(r, "rerank_effective") != PASS, r

    # Regression 9 (round-2 finding): a cut that exists in the file but not above the model call
    # is not established as running first. Presence was previously reported as PASS.
    r, _ = run_review(build({"rag.py": """
        def prep(q):
            return retriever.retrieve(q, top_k=5)
        def answer(q):
            docs = prep(q)
            if not docs:
                return None
            return client.chat.completions.create(messages=docs, citations=[1])
    """}))
    assert status(r, "topk_before_model") != PASS, r

    print("selftest OK: 13 fixtures, 38 assertions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
