#!/usr/bin/env python3
"""Place ultradian sprint blocks on the owner's measured curve.

Deterministic on purpose. The model supplies commitments and evidence
expectations; the arithmetic of where a block lands is not a judgment call and
does not belong in a prompt that reruns every morning.

Usage:
    python3 plan_blocks.py --selftest
    python3 plan_blocks.py < input.json     # {"ultradian": {...}, "commitments": [...], "busy": [...]}

Input contract:
    ultradian    the `ultradian` object from briefings.config.json
    commitments  [{"id","title","weight":"deep"|"shallow","source","evidence":[...],"fixedAt":"HH:MM"?}]
    busy         [{"start":"HH:MM","end":"HH:MM","label"}]  calendar events that own the clock

Output: {"blocks": [...], "unplaced": [...]}  blocks carry id B1..Bn in clock order.
"""

import json
import sys

BAND_RANK = {"peak": 0, "high": 1, "unmeasured": 2, "low": 3}


def m(hhmm):
    h, mm = hhmm.split(":")
    return int(h) * 60 + int(mm)


def hhmm(mins):
    return f"{mins // 60:02d}:{mins % 60:02d}"


def band_at(bands, minute):
    for b in bands:
        if m(b["start"]) <= minute < m(b["end"]):
            return b["band"]
    return "unmeasured"  # an hour the survey never measured is not a low hour; ranking it
    # below "high" and above "low" is the only honest place to put it


def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def _walk(u, start, stop, busy_m, limit):
    """Emit non-overlapping block slots between start and stop, skipping busy time."""
    block = u["blockMinutes"]
    step = block + u["recoveryMinutes"]
    out, t = [], start
    while t + block <= stop and len(out) < limit:
        if any(overlaps(t, t + block, bs, be) for bs, be in busy_m):
            t += 15  # nudge past the meeting rather than losing the rest of the day
            continue
        out.append((t, t + block))
        t += step
    return out


def candidate_slots(u, busy):
    """Walk the day in block+recovery steps, skipping anything the calendar owns.

    The frog window is laid down FIRST. It is the owner's highest-value window, and
    filling the day front to back with a six block cap silently spends the cap before
    reaching it. Observed 2026-09-23: an 08:00 start filled all six slots by 18:15 and
    the 19:00 window, the whole point of the curve, never got a block.
    """
    cap = u.get("maxBlocksPerDay", 6)
    busy_m = [(m(b["start"]), m(b["end"])) for b in busy]
    fw = u["frogWindow"]

    reserved = _walk(u, m(fw["start"]), min(m(fw["end"]), m(u["dayEnd"])), busy_m, cap)
    rest = _walk(u, m(u["dayStart"]), m(fw["start"]), busy_m, cap - len(reserved))

    return [
        {
            "start": hhmm(a),
            "end": hhmm(b),
            "band": band_at(u["bands"], a),
            "focusMinutes": u["blockMinutes"],
            "recoveryMinutes": u["recoveryMinutes"],
        }
        for a, b in sorted(rest + reserved)
    ]


def plan(u, commitments, busy=None):
    """busy is the calendar. `ultradian.unavailable` is the standing daily rhythm.

    They are different kinds of fact and both block a slot. A curve says when the owner
    CAN do deep work; it does not say when they are AVAILABLE to. Conflating the two is
    how a frog window ends up running past the hour the owner actually stops.
    """
    slots = candidate_slots(u, list(busy or []) + list(u.get("unavailable", [])))
    taken, assigned = set(), {}

    # 1. fixed commitments claim their slot first
    for c in commitments:
        if not c.get("fixedAt"):
            continue
        for i, s in enumerate(slots):
            if i not in taken and s["start"] == c["fixedAt"]:
                taken.add(i)
                assigned[i] = c
                break

    # 2. deep work takes the best remaining band, shallow takes what is left
    rest = [c for c in commitments if id(c) not in {id(x) for x in assigned.values()}]
    rest.sort(key=lambda c: 0 if c.get("weight") == "deep" else 1)
    for c in rest:
        free = [i for i in range(len(slots)) if i not in taken]
        if not free:
            break
        if c.get("weight") == "deep":
            free.sort(key=lambda i: (BAND_RANK.get(slots[i]["band"], 3), i))
        else:
            free.sort(key=lambda i: (-BAND_RANK.get(slots[i]["band"], 3), i))
        i = free[0]
        taken.add(i)
        assigned[i] = c

    placed_ids = {c["id"] for c in assigned.values()}
    blocks = []
    for n, (i, s) in enumerate(sorted(enumerate(slots)), start=1):
        c = assigned.get(i)
        blocks.append(
            {
                "id": f"B{n}",
                "start": s["start"],
                "end": s["end"],
                "band": s["band"],
                "focusMinutes": s["focusMinutes"],
                "recoveryMinutes": s["recoveryMinutes"],
                "inFrogWindow": m(s["start"]) >= m(u["frogWindow"]["start"])
                and m(s["end"]) <= m(u["frogWindow"]["end"]),
                "commitment": c["title"] if c else None,
                "commitmentId": c["id"] if c else None,
                "commitmentSource": c.get("source") if c else None,
                "evidence": {"expect": c.get("evidence", []) if c else []},
                "status": "planned" if c else "open",
                "verifiedBy": [],
                "checkedAt": None,
                "triggerId": None,
            }
        )
    unplaced = [c["id"] for c in commitments if c["id"] not in placed_ids]
    return {"blocks": blocks, "unplaced": unplaced}


FIXTURE_CURVE = {  # A TEST FIXTURE. Not anyone's measured curve. See is_fixture().

    "blockMinutes": 75,
    "recoveryMinutes": 15,
    "dayStart": "08:00",
    "dayEnd": "21:00",
    "maxBlocksPerDay": 6,
    "bands": [
        {"band": "peak", "start": "08:00", "end": "11:00"},
        {"band": "high", "start": "11:00", "end": "13:00"},
        {"band": "low", "start": "13:00", "end": "16:00"},
        {"band": "high", "start": "16:00", "end": "19:00"},
        {"band": "peak", "start": "19:00", "end": "21:00"},
    ],
    "frogWindow": {"start": "19:00", "end": "21:00", "workdaysOnly": True},
}



def is_fixture(u):
    """True when the configured curve is still the documented example.

    A config that was never filled in looks exactly like a config that was, which is the
    whole failure this shop published a paper about. The example curve peaks in the
    morning; the owner this was built for peaks at 19:00. Shipping the example would have
    produced a plan that looked measured and was backwards.
    """
    return (
        u.get("bands") == FIXTURE_CURVE["bands"]
        and u.get("dayStart") == FIXTURE_CURVE["dayStart"]
        and u.get("dayEnd") == FIXTURE_CURVE["dayEnd"]
    )


def check_curve(u):
    """Raise unless this curve can be attributed. Callers must run this before plan()."""
    if not u.get("curveSource"):
        raise ValueError("ultradian.curveSource is empty: a curve nobody can attribute is not a measurement")
    if is_fixture(u):
        raise ValueError("ultradian.bands is still the documented fixture: replace it with the owner's measured curve")
    for w in u.get("unavailable", []):
        if not w.get("source"):
            raise ValueError(
                f"ultradian.unavailable[{w.get('label', '?')}] has no source: a window that blocks the "
                "owner's day must be derived from something, not typed in"
            )
    return True



def curve_conflicts(u):
    """Collisions between the owner's curve and the windows they are not available.

    Stated, never resolved. A meal window sitting on a peak band is a real conflict
    between two body facts, and the honest move is to say so and let the owner choose.
    Silently placing the block elsewhere hides the trade; silently placing it anyway
    schedules deep work for an hour the owner is at the table.
    """
    out = []
    fw = u["frogWindow"]
    fs, fe = m(fw["start"]), m(fw["end"])

    for w in u.get("unavailable", []):
        ws, we = m(w["start"]), m(w["end"])
        label = w.get("label", "an unavailable window")
        if overlaps(ws, we, fs, fe):
            out.append(
                f"COLLISION: {label} ({w['start']} to {w['end']}) overlaps the frog window "
                f"({fw['start']} to {fw['end']}). These are the same hours. Move the meal, move the "
                f"block, or run one shorter block before it. This plan does not choose."
            )
        for b in u["bands"]:
            if b["band"] in ("peak", "high") and overlaps(ws, we, m(b["start"]), m(b["end"])):
                out.append(
                    f"COLLISION: {label} ({w['start']} to {w['end']}) overlaps a {b['band']} band "
                    f"({b['start']} to {b['end']}). Capacity and availability disagree here."
                )

    if fe > m(u["dayEnd"]):
        out.append(
            f"NOTE: the frog window runs to {fw['end']} but the day ends at {u['dayEnd']}, so only "
            f"{fw['start']} to {u['dayEnd']} is usable. Capacity outlasts availability; the plan follows "
            f"availability."
        )
    return out


def selftest():
    deep = {"id": "c1", "title": "Draft the pillar essay", "weight": "deep", "source": "manual"}
    shallow = {"id": "c2", "title": "Clear review comments", "weight": "shallow", "source": "github"}
    out = plan(FIXTURE_CURVE, [shallow, deep])
    blocks = out["blocks"]

    starts = [m(b["start"]) for b in blocks]
    assert starts == sorted(starts), "blocks must be in clock order"
    for a, b in zip(blocks, blocks[1:]):
        assert m(a["end"]) <= m(b["start"]), f"blocks overlap: {a['id']} {b['id']}"
    assert all(m(b["end"]) <= m(FIXTURE_CURVE["dayEnd"]) for b in blocks), "block runs past dayEnd"
    assert len(blocks) <= FIXTURE_CURVE["maxBlocksPerDay"], "block cap exceeded"

    deep_block = next(b for b in blocks if b["commitmentId"] == "c1")
    assert deep_block["band"] in ("peak", "high"), "deep work landed off peak with better slots free"
    assert not out["unplaced"], "both commitments should have been placed"

    # a meeting owns the clock: no block may sit inside it
    busy = [{"start": "08:00", "end": "09:30", "label": "Client call"}]
    out2 = plan(FIXTURE_CURVE, [deep], busy)
    for b in out2["blocks"]:
        assert not overlaps(m(b["start"]), m(b["end"]), m("08:00"), m("09:30")), \
            f"block {b['id']} sits inside a calendar event"

    # more commitments than slots: the overflow is reported, never silently dropped
    many = [{"id": f"c{i}", "title": f"thing {i}", "weight": "deep"} for i in range(9)]
    out3 = plan(FIXTURE_CURVE, many)
    assert len(out3["unplaced"]) == 9 - len([b for b in out3["blocks"] if b["commitmentId"]]), \
        "unplaced count must account for every commitment that got no block"

    # the frog window always gets a block, even when the cap would otherwise be spent
    full = plan(FIXTURE_CURVE, [{"id": f"d{i}", "title": f"deep {i}", "weight": "deep"} for i in range(6)])
    assert any(b["inFrogWindow"] for b in full["blocks"]), \
        "frog window lost its block to a front-loaded day"

    # the fixture is detected, and an attributed real curve passes
    assert is_fixture(FIXTURE_CURVE), "fixture must be recognisable as itself"
    try:
        check_curve(FIXTURE_CURVE)
        raise AssertionError("check_curve must refuse the fixture")
    except ValueError:
        pass
    evening = json.loads(json.dumps(FIXTURE_CURVE))
    evening["curveSource"] = "Daily Architecture survey, 2026-09"
    evening["dayStart"], evening["dayEnd"] = "09:00", "22:00"
    evening["bands"] = [
        {"band": "low", "start": "13:00", "end": "15:30"},
        {"band": "peak", "start": "19:00", "end": "21:00"},
    ]
    assert check_curve(evening), "an attributed, non-fixture curve must pass"
    ev = plan(evening, [{"id": "d", "title": "revenue work", "weight": "deep"}])
    deep_ev = next(b for b in ev["blocks"] if b["commitmentId"] == "d")
    assert deep_ev["band"] != "low", "deep work must not land in a measured dip"
    assert band_at(evening["bands"], m("10:00")) == "unmeasured", \
        "an hour the survey did not measure must not be reported as low"


    # a standing unavailable window blocks a slot exactly as a calendar event does
    dinner = json.loads(json.dumps(evening))
    dinner["unavailable"] = [{"start": "17:00", "end": "19:00", "label": "dinner"}]
    for b in plan(dinner, [])["blocks"]:
        assert not overlaps(m(b["start"]), m(b["end"]), m("17:00"), m("19:00")), \
            f"block {b['id']} sits inside a standing unavailable window"
    # availability clamps capacity: a frog window may outlast the day, the plan may not
    short = json.loads(json.dumps(evening))
    short["dayEnd"] = "20:30"
    short["frogWindow"] = {"start": "19:00", "end": "21:00", "workdaysOnly": True}
    for b in plan(short, [])["blocks"]:
        assert m(b["end"]) <= m("20:30"), f"block {b['id']} runs past the owner's day end"


    # a standing window with no source is refused: same bar as the curve itself
    unsourced = json.loads(json.dumps(evening))
    unsourced["unavailable"] = [{"start": "17:00", "end": "19:00", "label": "dinner"}]
    try:
        check_curve(unsourced)
        raise AssertionError("check_curve must refuse an unavailable window with no source")
    except ValueError:
        pass
    sourced = json.loads(json.dumps(unsourced))
    sourced["unavailable"][0]["source"] = "derived: last meal 3h before sleep onset 23:30"
    assert check_curve(sourced), "a sourced unavailable window must pass"


    # collisions are reported, in full sentences, and never quietly resolved
    coll = json.loads(json.dumps(evening))
    coll["dayEnd"] = "20:30"
    coll["unavailable"] = [{"start": "18:30", "end": "19:30", "label": "last meal",
                            "source": "Body Clock Audit Part C"}]
    msgs = curve_conflicts(coll)
    assert any("frog window" in x for x in msgs), "a meal inside the frog window must be reported"
    assert any(x.startswith("NOTE:") for x in msgs), "a frog window past day end must be reported"
    clean = json.loads(json.dumps(evening))
    clean["dayEnd"] = "21:00"
    clean["unavailable"] = [{"start": "17:00", "end": "18:00", "label": "last meal",
                             "source": "Body Clock Audit Part C"}]
    assert curve_conflicts(clean) == [], "a meal clear of every band and the frog window is not a conflict"

    print(f"selftest ok: {len(blocks)} blocks, deep work at {deep_block['start']} ({deep_block['band']})")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    data = json.load(sys.stdin)
    json.dump(plan(data["ultradian"], data["commitments"], data.get("busy")), sys.stdout, indent=2)
