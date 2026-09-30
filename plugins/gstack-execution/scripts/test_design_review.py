#!/usr/bin/env python3
"""XE-031: the two-reviewer design-doc loop, driven by stub reviewers. Stdlib only; run directly."""
import json, tempfile
from pathlib import Path

import design_review as d
import peer_review as pr

BOTH = lambda t: t in ("codex", "openrouter-gemini")


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
        d.init(self.state, "claude", self.draft, self.dir / "log.md", cap=cap, installed=BOTH)

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
    L.rev("r2", reply(stances=[("R1-r1-1", "agree")]))
    L.write({"R1-r1-1": {"disposition": "accepted"}})
    L.rev("r1", reply("APPROVED", open_=[("R1-r1-1", "resolved")]))
    s = L.rev("r2", reply("APPROVED", open_=[("R1-r1-1", "still_open")]))
    assert s["outcome"] == "converged" and s["round"] == 2, s["outcome"]


def test_a_writer_rejection_leaves_a_material_finding_open():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "wrong API")]))
    L.rev("r2", reply(stances=[("R1-r1-1", "disagree")]))
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
    s = L.rev("r2", reply("APPROVED", stances=[("R2-r1-1", "disagree")]))
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
    L.rev("r2", reply(stances=[("R1-r1-1", "agree")]))
    L.write({"R1-r1-1": {"disposition": "accepted"}})
    s = L.rev("r1", reply("APPROVED"), reply("APPROVED"))
    assert s["outcome"] == "incomplete" and "omits open finding" in s["failure"]["why"], s["failure"]


def test_a_reissued_finding_merges_and_the_stall_is_still_seen():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    L.rev("r2", reply(stances=[("R1-r1-1", "agree")]))
    L.write({"R1-r1-1": {"disposition": "rejected", "reason": "no"}}, change=False)
    L.rev("r1", reply(open_=[("R1-r1-1", "still_open")], new=[("material", "finding", "x again")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")], stances=[("R2-r1-1", "agree")]))
    s = L.write({"R2-r1-1": {"disposition": "duplicate of R1-r1-1"}}, change=False)
    assert s["findings"]["R2-r1-1"]["open"] is False and s["findings"]["R1-r1-1"]["open"] is True
    assert s["stalls"] == 1, s["stalls"]
    L.rev("r1", reply(open_=[("R1-r1-1", "still_open")]))
    L.rev("r2", reply(open_=[("R1-r1-1", "still_open")]))
    s = L.write({}, change=False)
    assert s["outcome"] == "stalled", s["outcome"]
    assert "`R1-r1-1` (material): x" in d.dissent(s)


def test_the_cap_writes_dissent_with_real_ids():
    L = Loop(cap=2)
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    L.rev("r2", reply(stances=[("R1-r1-1", "extend")], new=[("material", "finding", "y")]))
    L.write({"R1-r1-1": {"disposition": "deferred", "reason": "later"}, "R1-r2-1": {"disposition": "accepted"}})
    L.rev("r1", reply(open_=[("R1-r1-1", "still_open"), ("R1-r2-1", "still_open")]))
    s = L.rev("r2", reply(open_=[("R1-r1-1", "still_open"), ("R1-r2-1", "still_open")]))
    assert s["outcome"] == "cap_reached"
    txt = d.dissent(s)
    assert "## Dissent" in txt and all(i in txt and i in s["findings"] for i in ("R1-r1-1", "R1-r2-1")), txt


def test_reviewer_2_failing_after_reviewer_1_ends_incomplete_with_no_substitute():
    L = Loop()
    L.rev("r1", reply(new=[("material", "finding", "x")]))
    calls = []
    def runner(tool, prompt):
        calls.append(tool)
        raise pr.ReviewError("timeout", f"{tool} exceeded 1800s")
    s = d.review(L.state, "r2", L.draft, L.prompt, runner=runner)
    assert s["outcome"] == "incomplete" and calls == ["openrouter-gemini", "openrouter-gemini"], calls
    assert "R1-r1-1" in s["findings"] and L.draft.read_text() == "v0\n"
    assert "No other reviewer was substituted" in Path(s["log"]).read_text()


def test_a_same_family_reviewer_is_never_chosen():
    try:
        d.choose("claude", installed=lambda t: t in ("codex", "openrouter-gpt", "claude", "openrouter-claude"))
        raise AssertionError("only one non-claude family is reachable; the loop must not start")
    except SystemExit as e:
        assert "No same-family stand-in" in str(e)
    r1, r2 = d.choose("claude", installed=BOTH)
    assert len({pr.family(r1), pr.family(r2), "claude"}) == 3


def test_a_constraint_violation_is_kept_and_a_policy_proposal_set_aside():
    L = Loop()
    s = L.rev("r1", reply(new=[("material", "finding", "violates the no-n8n constraint"),
                               ("material", "policy_proposal", "drop the no-n8n constraint")]))
    assert list(s["findings"]) == ["R1-r1-1"] and s["policy_proposals"][0]["id"] == "R1-r1-2"
    assert d.summary(s)["policy_proposals"][0]["text"] == "drop the no-n8n constraint"


def test_the_run_note_records_every_call():
    L = Loop()
    L.rev("r1", reply()); L.rev("r2", reply())
    p = d.finish(L.state, L.dir / "runs")
    text = p.read_text()
    assert 'reviewer_calls: 2' in text and 'type: "gstack-design-review"' in text, text


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
