#!/usr/bin/env python3
"""AP-004: Zenodo deposit. Offline: the transport is injected, so nothing reaches the network."""
import contextlib, io, json, os, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zenodo_deposit as zd

TOKEN = "T0kenValueThatMustNeverBePrinted1234567890abc"
META = {"title": "A runner", "upload_type": "software", "creators": [{"name": "Doe, Jane"}], "license": "MIT"}


def artifact():
    d = Path(tempfile.mkdtemp()) / "my-runner"
    (d / "expected").mkdir(parents=True)
    (d / "__pycache__").mkdir()
    (d / ".zenodo.json").write_text(json.dumps(META))
    (d / "check.py").write_text("print('ok')\n")
    (d / "expected" / "out.txt").write_text("PASS\n")
    (d / "__pycache__" / "check.cpython-311.pyc").write_bytes(b"x")
    (d / "stray.pyc").write_bytes(b"x")
    return d


def fake(calls, fail=None):
    def t(method, url, token, body=None, ctype="application/json"):
        calls.append((method, url, token, body))
        if fail and fail in url:
            return 403, {"message": "denied"}
        if method == "POST" and url.endswith("/deposit/depositions"):
            return 201, {"id": 7, "links": {"bucket": "https://z/bucket/7", "html": "https://z/uploads/7"},
                         "metadata": {"prereserve_doi": {"doi": "10.5281/zenodo.7"}}}
        if url.endswith("/actions/publish"):
            return 202, {"doi": "10.5281/zenodo.7", "links": {"html": "https://z/records/7"}}
        return 200, {}
    return t


def run(argv, transport, env_token=TOKEN):
    out, err = io.StringIO(), io.StringIO()
    old = os.environ.get("ZENODO_TOKEN")
    if env_token is None:
        os.environ.pop("ZENODO_TOKEN", None)
    else:
        os.environ["ZENODO_TOKEN"] = env_token
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = zd.main(argv, transport)
    finally:
        if old is None:
            os.environ.pop("ZENODO_TOKEN", None)
        else:
            os.environ["ZENODO_TOKEN"] = old
    return rc, out.getvalue() + err.getvalue()


def test_draft_never_calls_publish_and_records_state():
    d, calls = artifact(), []
    rc, out = run(["draft", str(d)], fake(calls))
    assert rc == 0, out
    assert not any("publish" in c[1] for c in calls)
    state = json.loads((d / zd.STATE).read_text())
    assert state["id"] == 7 and state["reserved_doi"] == "10.5281/zenodo.7" and "doi" not in state


def test_zip_holds_the_folder_under_its_slug_and_skips_caches_and_state():
    d, calls = artifact(), []
    (d / zd.STATE).write_text("{}")
    run(["draft", str(d)], fake(calls))
    upload = next(c for c in calls if c[0] == "PUT" and "/bucket/" in c[1])
    assert upload[1].endswith("/my-runner.zip")
    names = sorted(zipfile.ZipFile(io.BytesIO(upload[3])).namelist())
    assert names == ["my-runner/.zenodo.json", "my-runner/check.py", "my-runner/expected/out.txt"], names


def test_metadata_sent_equals_the_folder_zenodo_json():
    d, calls = artifact(), []
    run(["draft", str(d)], fake(calls))
    meta = next(c for c in calls if c[0] == "PUT" and c[1].endswith("/deposit/depositions/7"))
    assert meta[3] == {"metadata": META}


def test_publish_without_a_recorded_draft_refuses():
    d, calls = artifact(), []
    rc, out = run(["publish", str(d)], fake(calls))
    assert rc == 1 and "run `draft` first" in out and not calls


def test_publish_after_draft_records_the_doi_and_refuses_a_second_time():
    d, calls = artifact(), []
    run(["draft", str(d)], fake(calls))
    rc, out = run(["publish", str(d)], fake(calls))
    assert rc == 0 and "https://doi.org/10.5281/zenodo.7" in out
    assert json.loads((d / zd.STATE).read_text())["doi"] == "10.5281/zenodo.7"
    rc, out = run(["publish", str(d)], fake(calls))
    assert rc == 1 and "already published" in out


def test_sandbox_draft_cannot_be_published_live():
    d, calls = artifact(), []
    run(["draft", str(d), "--sandbox"], fake(calls))
    assert calls[0][1].startswith(zd.SANDBOX)
    rc, out = run(["publish", str(d)], fake(calls))
    assert rc == 1 and "sandbox" in out


def test_missing_token_exits_nonzero_without_a_traceback():
    d = artifact()
    rc, out = run(["draft", str(d)], fake([]), env_token=None)
    assert rc == 2 and "Traceback" not in out and "ZENODO_TOKEN" in out


def test_token_file_is_read_and_the_token_is_never_printed():
    d, calls = artifact(), []
    tf = d.parent / "zenodo.env"
    tf.write_text(f"# vault\nZENODO_TOKEN={TOKEN}\n")
    rc, out = run(["draft", str(d), "--token-file", str(tf)], fake(calls), env_token=None)
    assert rc == 0 and calls[0][2] == TOKEN and TOKEN not in out
    rc, out = run(["draft", str(d), "--token-file", str(tf)], fake(calls, fail="/deposit/depositions"), env_token=None)
    assert rc == 1 and "HTTP 403" in out and TOKEN not in out


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
