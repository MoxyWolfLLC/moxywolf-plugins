#!/usr/bin/env python3
"""DG-001: check_repo_diagram.py against real temporary git repositories. Stdlib only; run directly."""
import json, subprocess, tempfile
from pathlib import Path

import check_repo_diagram as c

ORIGIN = "https://github.com/example/app.git"


def sh(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def repo(origin=ORIGIN):
    r = Path(tempfile.mkdtemp())
    sh(r, "init", "-q")
    sh(r, "config", "user.email", "t@t"); sh(r, "config", "user.name", "t")
    (r / "src").mkdir()
    (r / "src" / "app.py").write_text("".join(f"line {i}\n" for i in range(1, 11)))
    (r / "src" / "store.py").write_text("write()\n")
    sh(r, "add", "."); sh(r, "commit", "-qm", "seed")
    sh(r, "remote", "add", "origin", origin)
    return r, sh(r, "rev-parse", "HEAD")


def el(i, t="rectangle", claim=None):
    e = {"id": i, "type": t, "isDeleted": False}
    if claim is not None:
        e["customData"] = {"claim": claim}
    return e


def note(head, rows, elements=None, origin=ORIGIN, compressed=False):
    elements = elements if elements is not None else [el("api"), el("db", "ellipse"), el("e1", "arrow"), el("title", "text")]
    table = "\n".join(f"| `{a}` | {b} | `{s}` |" for a, b, s in rows)
    fence = "compressed-json" if compressed else "json"
    body = (f"---\nexcalidraw-plugin: parsed\ntags: [excalidraw]\nrepo_head: {head}\nrepo_origin: {origin}\nrepo_dirty: []\n---\n\n"
            "==⚠ Switch to EXCALIDRAW VIEW ==\n\n## Sources\n\n| element | claim | source |\n|---|---|---|\n"
            f"{table}\n\n# Excalidraw Data\n\n## Text Elements\n\n%%\n## Drawing\n```{fence}\n"
            + json.dumps({"type": "excalidraw", "elements": elements}) + "\n```\n%%\n")
    p = Path(tempfile.mkdtemp()) / "d.excalidraw.md"
    p.write_text(body, encoding="utf-8")
    return p


GOOD = [("api", "serves requests", "src/app.py:1-10"), ("db", "the store", "src/store.py:1-1"), ("e1", "api writes db", "src/store.py:1-1")]


def fails(p, r):
    return c.check(p, r)[0]


def test_a_complete_note_passes():
    r, h = repo()
    f, info, n = c.check(note(h, GOOD), r)
    assert f == [], f
    assert n == 6, n
    assert info == [f"current HEAD {h[:7]}"], info


def test_an_unsupported_connection_fails_beside_a_valid_row():
    r, h = repo()
    f = fails(note(h, GOOD[:2]), r)
    assert f == ["element e1: drawn with no Sources row"], f


def test_a_row_for_an_absent_element_fails():
    r, h = repo()
    f = fails(note(h, GOOD + [("ghost", "x", "src/app.py:1-1")]), r)
    assert f == ["row ghost: no such claim element in the drawing"], f


def test_two_rows_for_one_element_fail():
    r, h = repo()
    f = fails(note(h, GOOD + [("api", "again", "src/app.py:2-3")]), r)
    assert f == ["element api: 2 Sources rows, expected one"], f


def test_a_path_missing_at_repo_head_fails():
    r, h = repo()
    f = fails(note(h, [GOOD[0], GOOD[1], ("e1", "x", "src/nope.py:1-1")]), r)
    assert any("src/nope.py does not exist" in x for x in f), f


def test_a_directory_citation_fails():
    r, h = repo()
    f = fails(note(h, [("api", "x", "src:1-1")] + GOOD[1:]), r)
    assert f == [f"row api: src is a tree at {h[:7]}, not a file"], f


def test_drift_is_reported_for_a_path_with_a_space():
    r, h = repo()
    (r / "src" / "my store.py").write_text("a\n")
    sh(r, "add", "."); sh(r, "commit", "-qm", "spaced")
    h = sh(r, "rev-parse", "HEAD")
    rows = [GOOD[0], ("db", "the store", "src/my store.py:1-1"), GOOD[2]]
    (r / "src" / "my store.py").write_text("a\nb\n")
    sh(r, "commit", "-qam", "later")
    f, info, _ = c.check(note(h, rows), r)
    assert f == [], f
    assert f"drift (not a failure): src/my store.py changed since {h[:7]}" in info, info


def test_a_line_range_past_the_end_fails():
    r, h = repo()
    f = fails(note(h, [("api", "x", "src/app.py:5-11")] + GOOD[1:]), r)
    assert any("lines 5-11 outside src/app.py (1-10" in x for x in f), f


def test_an_origin_with_a_token_fails():
    r, h = repo()
    f = fails(note(h, GOOD, origin="https://x-access-token:abc123@github.com/example/app.git"), r)
    assert "repo_origin carries userinfo (a user, password or token)" in f, f


def test_a_note_for_repo_a_fails_against_repo_b_at_the_same_commit():
    a, h = repo()
    b = Path(tempfile.mkdtemp())
    subprocess.run(["git", "clone", "-q", str(a), str(b)], check=True)
    sh(b, "remote", "set-url", "origin", "https://github.com/other/fork.git")
    assert sh(b, "rev-parse", "HEAD") == h
    f = fails(note(h, GOOD), b)
    assert any("does not match --repo's origin" in x for x in f), f


def test_an_empty_sources_table_fails():
    r, h = repo()
    f = fails(note(h, []), r)
    assert len([x for x in f if "drawn with no Sources row" in x]) == 3, f


def test_nothing_examined_is_a_failure():
    r, h = repo()
    f = fails(note(h, [], elements=[el("title", "text"), el("legend", claim=False)]), r)
    assert f == ["checked 0 elements and 0 rows; nothing was examined"], f


def test_a_compressed_drawing_fails_with_the_fix():
    r, h = repo()
    f = fails(note(h, GOOD, compressed=True), r)
    assert len(f) == 1 and "Decompress current Excalidraw file" in f[0], f


def test_working_tree_edits_are_not_read():
    r, h = repo()
    (r / "src" / "app.py").write_text("only one line\n")
    assert fails(note(h, GOOD), r) == []


def test_head_moved_past_repo_head_is_drift_not_failure():
    r, h = repo()
    (r / "src" / "store.py").write_text("write()\nflush()\n")
    sh(r, "commit", "-qam", "later")
    f, info, _ = c.check(note(h, GOOD), r)
    assert f == [], f
    assert f"drift (not a failure): src/store.py changed since {h[:7]}" in info, info
    assert not any("app.py" in i for i in info), info


def test_unknown_rows_count_as_rows_and_are_not_resolved():
    r, h = repo()
    assert fails(note(h, [GOOD[0], GOOD[1], ("e1", "durability not traced", "unknown")]), r) == []


def test_cli_exit_codes():
    r, h = repo()
    assert c.main([str(note(h, GOOD)), "--repo", str(r)]) == 0
    assert c.main([str(note(h, GOOD[:2])), "--repo", str(r)]) == 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
