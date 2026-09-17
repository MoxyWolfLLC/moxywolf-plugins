#!/usr/bin/env python3
"""EV-007: reference identity, and repository claims that resolve. Stdlib only."""
import os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_gate as rg


def test_one_work_cited_in_two_url_forms_is_one_work():
    """The point of the item: a duplicate check keyed on the string reports a padded bibliography
    as a broad one."""
    a, ka = rg.canonical_work("Smith. https://arxiv.org/abs/2502.16161v3")
    b, kb = rg.canonical_work("Smith. Announcement. https://arxiv.org/pdf/2502.16161")
    assert a == b == "arxiv:2502.16161" and ka == kb == "arxiv"


def test_a_doi_is_one_work_regardless_of_resolver_or_case():
    for t in ("https://doi.org/10.1000/abc.123", "https://dx.doi.org/10.1000/ABC.123.",
              "See doi 10.1000/abc.123 for detail"):
        assert rg.canonical_work(t)[0] == "doi:10.1000/abc.123", t


def test_identity_reports_which_rule_produced_it():
    """A DOI match and a bare-URL fallback carry different confidence, and a reader should not
    have to infer which happened from the string."""
    assert rg.canonical_work("x https://arxiv.org/abs/2502.16161")[1] == "arxiv"
    assert rg.canonical_work("x PMID: 12345678")[1] == "pmid"
    assert rg.canonical_work("x https://example.com/post")[1] == "url"
    assert rg.canonical_work("no identifier here") == (None, None)


def test_a_preprint_and_its_journal_doi_are_NOT_linked():
    """Stated so nobody reads more into this than it does: linking a preprint to the DOI it later
    received needs a registry lookup and is not attempted. Two identifiers, two works, by design."""
    a = rg.canonical_work("Smith. https://arxiv.org/abs/2502.16161")[0]
    b = rg.canonical_work("Smith. https://doi.org/10.1000/published.version")[0]
    assert a != b


def test_the_duplicate_check_catches_a_work_cited_twice():
    paper = ("# P\n\n## References\n\n1. Smith. https://arxiv.org/abs/2502.16161v3\n\n"
             "2. Smith. Same study. https://arxiv.org/pdf/2502.16161\n\n"
             "3. Jones. https://doi.org/10.1000/xyz\n")
    status, detail, examined, _ = rg.check_duplicate_sources(paper, {})
    assert status == rg.FAIL and "arxiv:2502.16161" in detail
    assert examined == 3, detail


def _repo(t):
    r = Path(t)/"r"; r.mkdir()
    for c in (["git","init","-q"],["git","config","user.email","t@t"],["git","config","user.name","t"]):
        subprocess.run(c, cwd=r, check=True, capture_output=True)
    (r/"test_thing.py").write_text("x\n")
    subprocess.run(["git","add","-A"], cwd=r, check=True, capture_output=True)
    subprocess.run(["git","commit","-qm","c"], cwd=r, check=True, capture_output=True)
    sha = subprocess.run(["git","rev-parse","--short","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
    return str(r), sha


def test_a_cited_commit_and_test_file_that_exist_resolve():
    with tempfile.TemporaryDirectory() as t:
        repo, sha = _repo(t)
        st, detail, n, _ = rg.check_repository_references(
            f"Built at commit {sha}, verified by `test_thing.py`.", {"repository": repo})
        assert st == rg.PASS and n == 2, detail


def test_a_cited_commit_that_never_existed_fails_and_is_named():
    with tempfile.TemporaryDirectory() as t:
        repo, _ = _repo(t)
        st, detail, n, _ = rg.check_repository_references("Built at commit deadbee.", {"repository": repo})
        assert st == rg.FAIL and "deadbee" in detail and n == 1


def test_a_cited_test_file_that_is_not_tracked_fails():
    with tempfile.TemporaryDirectory() as t:
        repo, _ = _repo(t)
        st, detail, _, _ = rg.check_repository_references("Verified by `test_imaginary.py`.", {"repository": repo})
        assert st == rg.FAIL and "test_imaginary.py" in detail


def test_no_repository_is_a_SKIP_not_a_PASS():
    """The failure this must never produce: a paper citing commits, no repository to check them
    against, and a green line. A gate that examined nothing cannot pass."""
    st, detail, n, _ = rg.check_repository_references("Built at commit abc1234.", {})
    assert st == rg.SKIP, st
    assert n == 0 and "went unchecked" in detail


def test_a_paper_citing_nothing_is_a_SKIP_with_zero_examined():
    st, _, n, _ = rg.check_repository_references("A paper with no repository claims.", {"repository": "/tmp"})
    assert st == rg.SKIP and n == 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
