#!/usr/bin/env python3
"""XE-031: the two-reviewer design-doc loop, driven by stub reviewers. Stdlib only; run directly."""
import json, tempfile
from pathlib import Path

import design_review as d
import peer_review as pr

READY = ("codex", "openrouter-gemini")
PROBE = lambda t: (t in READY, "ready" if t in READY else f"{t} stub: not ready")


def reply(verdict="REVISE", open_=(), stances=(), new=()):
    return json.dumps({"verdict": verdict, "open_findings": [{"id": i, "status": s, "reason": "r"} for i, s in open_],
                       "stances": [{"id": i, "stance": s, "reason": "r"} for i, s in stances],
                       "new_findings": [{"severity": sev, "kind": k, "text": t} for sev, k, t in new]})


class Loop:
    def __init__(self, cap=20):
        self.dir = Path(tempfile.mkdtemp())
        self.draft, self.state, self.prompt = self.dir / "DESIGN.md", self.dir / "state.json", self.dir / "p.txt"
        self.draft.write_text("v0\n"); self.prompt.write_text("review it")
        self.v = 0
        d.init(self.state, "claude", self.draft, self.dir / "log.md", cap=cap, probe=PROBE)

    def rev(self, slot, *replies):
        it = iter(replies)
        def runner(tool, prompt):
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return r, "stub-model"
        return d.review(self.state, slot, self.draft, self.prompt, runner=runner)

    def write(self, disp, change=True):
        if change:
            self.v += 1
            self.draft.write_text(f"v{self.v}\n")
        return d.writer(self.state, disp, self.draft)


def test_converges_at_round_2():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "gap")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")], stances=[("R1-r1-1", "agree")]))
    L.write({"R1-r1-1": {"disposition": "accepted"}})
    L.rev("r1", reply("APPROVED", open_=[("R1-r1-1", "resolved")]))
    s = L.rev("r2", reply("APPROVED"))
    assert s["outcome"] == "converged" and s["round"] == 2, s["outcome"]


def test_a_writer_rejection_leaves_a_material_finding_open():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "wrong API")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")], stances=[("R1-r1-1", "disagree")]))
    s = L.write({"R1-r1-1": {"disposition": "rejected", "reason": "r2 is right"}})
    assert s["findings"]["R1-r1-1"]["open"] is True
    L.rev("r1", reply("APPROVED", open_=[("R1-r1-1", "still_open")]))
    s = L.rev("r2", reply("APPROVED", open_=[("R1-r1-1", "resolved")]))  # r2 didn't raise it; can't close it
    assert s["outcome"] is None and "R1-r1-1" in d.open_ids(s)


def test_approvals_of_different_revisions_do_not_converge():
    L = Loop()
    L.rev("r1", reply("APPROVED"))
    L.rev("r2", reply(new=[("minor", "finding", "typo")]))
    L.write({"R1-r2-1": {"disposition": "accepted"}})
    L.rev("r1", reply(new=[("minor", "finding", "another")]))
    s = L.rev("r2", reply("APPROVED", open_=[("R2-r1-1", "still_open")], stances=[("R2-r1-1", "disagree")]))
    assert s["outcome"] is None, s["outcome"]


def test_a_stale_draft_cannot_be_reviewed():
    L = Loop()
    L.rev("r1", reply()); L.rev("r2", reply())
    L.write({})
    L.draft.write_text("edited outside the loop\n")
    try:
        L.rev("r1", reply("APPROVED"))
        raise AssertionError("a draft the loop didn't hand over must be refused")
    except SystemExit as e:
        assert "not the revision under review" in str(e)


def test_a_reply_that_omits_an_open_finding_is_malformed_then_incomplete():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")], stances=[("R1-r1-1", "agree")]))
    L.write({"R1-r1-1": {"disposition": "accepted"}})
    s = L.rev("r1", reply("APPROVED"), reply("APPROVED"))
    assert s["outcome"] == "incomplete" and "omits open finding" in s["failure"]["why"], s["failure"]
    assert len([c for c in s["calls"] if c["round"] == 2]) == 2, "one retry of a malformed reply"


def test_reviewer_2_must_give_reviewer_1s_new_findings_a_status_too():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    s = L.rev("r2", reply(stances=[("R1-r1-1", "agree")]), reply(stances=[("R1-r1-1", "agree")]))
    assert s["outcome"] == "incomplete" and "R1-r1-1" in s["failure"]["why"], s["failure"]


def test_a_reply_with_the_wrong_element_types_is_malformed_not_a_crash():
    L = Loop()
    bad = json.dumps({"verdict": "REVISE", "open_findings": [None], "stances": [], "new_findings": []})
    s = L.rev("r1", bad, json.dumps({"verdict": "REVISE", "open_findings": [{"id": ["x"]}], "stances": [], "new_findings": []}))
    assert s["outcome"] == "incomplete" and "malformed" in s["failure"]["why"], s["failure"]


def test_a_reissued_finding_merges_and_the_stall_is_still_seen():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")], stances=[("R1-r1-1", "agree")]))
    L.write({"R1-r1-1": {"disposition": "rejected", "reason": "no"}}, change=False)
    L.rev("r1", reply(open_=[("R1-r1-1", "still_open")], new=[("material", "finding", "x again")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open"), ("R2-r1-1", "still_open")], stances=[("R2-r1-1", "agree")]))
    s = L.write({"R2-r1-1": {"disposition": "duplicate of R1-r1-1"}}, change=False)
    assert s["findings"]["R2-r1-1"]["open"] is False and s["findings"]["R1-r1-1"]["open"] is True
    assert s["stalls"] == 1, s["stalls"]
    L.rev("r1", reply(open_=[("R1-r1-1", "still_open")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")]))
    s = L.write({}, change=False)
    assert s["outcome"] == "stalled", s["outcome"]
    assert "`R1-r1-1` (material): x" in d.dissent(s)


def test_a_writer_revision_resets_the_stall_count():
    L = Loop()
    for _ in range(2):
        L.rev("r1", reply()); L.rev("r2", reply())
        L.write({}, change=False)
    L.rev("r1", reply()); L.rev("r2", reply())
    s = L.write({}, change=True)
    assert s["outcome"] is None and s["stalls"] == 0, (s["outcome"], s["stalls"])


def test_a_minor_finding_raised_and_closed_is_movement_not_a_stall():
    L = Loop()
    L.rev("r1", reply()); L.rev("r2", reply())
    L.write({}, change=False)
    L.rev("r1", reply(new=[("minor", "finding", "nit")])); L.rev("r2", reply(open_=[("R2-r1-1", "still_open")], stances=[("R2-r1-1", "agree")]))
    s = L.write({"R2-r1-1": {"disposition": "rejected", "reason": "fine as is"}}, change=False)
    assert s["stalls"] == 0, s["stalls"]


def test_the_cap_round_is_disposed_before_the_loop_ends():
    L = Loop(cap=2)
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")], stances=[("R1-r1-1", "extend")]))
    L.write({"R1-r1-1": {"disposition": "deferred", "reason": "later"}})
    L.rev("r1", reply(open_=[("R1-r1-1", "still_open")]))
    s = L.rev("r2", reply(open_=[("R1-r1-1", "still_open")], new=[("material", "finding", "y")]))
    assert s["outcome"] is None, "the cap round's new findings still need the writer"
    s = L.write({"R2-r2-1": {"disposition": "rejected", "reason": "out of scope"}})
    assert s["outcome"] == "cap_reached"
    txt = d.dissent(s)
    assert "## Dissent" in txt and "rejected: out of scope" in txt and "not yet disposed" not in txt, txt
    assert all(i in txt and i in s["findings"] for i in ("R1-r1-1", "R2-r2-1")), txt


def test_reviewer_2_failing_after_reviewer_1_ends_incomplete_with_no_retry_or_substitute():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    calls = []
    def runner(tool, prompt):
        calls.append(tool)
        if len(calls) == 1:
            pr.LAST_REVIEWER_USAGE = {"total": 42}
            raise pr.ReviewError("timeout", f"{tool} exceeded 1800s")
        return reply("APPROVED", open_=[("R1-r1-1", "resolved")], stances=[("R1-r1-1", "agree")]), "m"
    s = d.review(L.state, "r2", L.draft, L.prompt, runner=runner)
    assert s["outcome"] == "incomplete" and calls == ["openrouter-gemini"], calls
    assert "R1-r1-1" in s["findings"] and L.draft.read_text() == "v0\n"
    failed = [c for c in s["calls"] if c["slot"] == "r2"]
    assert failed and failed[0]["error"].startswith("timeout") and failed[0]["usage"] == {"total": 42}, failed
    assert "No other reviewer was substituted" in Path(s["log"]).read_text()


def test_a_same_family_reviewer_is_never_chosen_and_each_rejection_says_why():
    probe = lambda t: (t in ("codex", "claude", "openrouter-claude"), f"{t}: key refused")
    try:
        d.choose("claude", probe=probe)
        raise AssertionError("only one non-claude family is ready; the loop must not start")
    except SystemExit as e:
        assert "No same-family stand-in" in str(e) and "openrouter-gemini (gemini): openrouter-gemini: key refused" in str(e), str(e)
    r1, r2 = d.choose("claude", probe=PROBE)
    assert len({pr.family(r1), pr.family(r2), "claude"}) == 3


def test_readiness_is_a_real_call_and_a_failure_is_the_reason():
    real = pr.run_reviewer
    def fake(tool, prompt, root, timeout, schema=None):
        if tool == "codex":
            return '{"ok": true}', "gpt-6-astra"
        raise pr.ReviewError("review_unavailable", f"{tool} exited 1: not authenticated")
    pr.run_reviewer = fake
    try:
        assert d.ready("codex") == (True, "answered as gpt-6-astra")
        ok, why = d.ready("gemini")
        assert not ok and why == "review_unavailable: gemini exited 1: not authenticated", why
        try:
            d.choose("claude")
            raise AssertionError("only codex answered; the loop must not start")
        except SystemExit as e:
            assert "gemini (gemini): review_unavailable: gemini exited 1: not authenticated" in str(e), str(e)
    finally:
        pr.run_reviewer = real


def test_a_status_or_stance_without_a_reason_is_malformed():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    bare = json.dumps({"verdict": "REVISE", "open_findings": [{"id": "R1-r1-1", "status": "still_open"}],
                       "stances": [{"id": "R1-r1-1", "stance": "disagree"}], "new_findings": []})
    s = L.rev("r2", bare, bare)
    assert s["outcome"] == "incomplete" and "reason" in s["failure"]["why"], s["failure"]


def test_a_constraint_violation_is_kept_and_a_policy_proposal_set_aside():
    L = Loop()
    s = L.rev("r1", reply(new=[("material", "finding", "violates the no-n8n constraint"),
                               ("material", "policy_proposal", "drop the no-n8n constraint")]))
    assert list(s["findings"]) == ["R1-r1-1"] and s["policy_proposals"][0]["id"] == "R1-r1-2"
    assert d.summary(s)["policy_proposals"][0]["text"] == "drop the no-n8n constraint"


def test_the_run_note_records_every_call():
    L = Loop()
    L.rev("r1", reply()); L.rev("r2", reply())
    text = d.finish(L.state, L.dir / "runs").read_text()
    assert 'reviewer_calls: 2' in text and 'type: "gstack-design-review"' in text, text


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
