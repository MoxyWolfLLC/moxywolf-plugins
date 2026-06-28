"""
Loop state I/O for the Synergy Engine prep loop.

Atomic, schema-validated, no LLM dependency. See references/loop-contract.md
for the column-ownership table and the seven verifier checks this state
file supports.

Schema v2 adds:
  - State.release_owner: the named human accountable for the outcome (§4 of
    Governed Autonomy). Required at init; surfaced by the verifier in every
    last_verifier.json so the name travels with the audit trail.
  - ChainBlock + nonce machinery: a full-chain integrity protocol that
    binds planner ↔ verifier ↔ tracker write ↔ calendar create. Each
    handoff burns one single-use nonce. Any script that tries to write to
    the tracker, write to state, or fake a verifier report without holding
    a live nonce gets rejected. Closes the AI-fakes-AI loophole the
    Governed Autonomy paper (§7) calls out.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = 2

# Exit codes consumed by cron / wrapper scripts.
EXIT_CONTINUE = 0
EXIT_GOAL_MET = 10
EXIT_HARD_STOP = 20
EXIT_TRANSIENT = 30
EXIT_QUOTA = 40

# Nonce-handoff kinds. The chain enforces order: PLAN → (TRACKER | CALENDAR)* → VERIFIER.
NONCE_PLAN = "plan"
NONCE_TRACKER = "tracker"
NONCE_CALENDAR = "calendar"
NONCE_VERIFIER = "verifier"
ALL_NONCE_KINDS = (NONCE_PLAN, NONCE_TRACKER, NONCE_CALENDAR, NONCE_VERIFIER)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_day(ts_iso: Optional[str]) -> Optional[str]:
    if not ts_iso:
        return None
    return ts_iso[:10]


def new_nonce() -> str:
    """Cryptographic single-use token. 32 hex chars = 128 bits of entropy.
    Sufficient that guessing one in a tick window is computationally infeasible."""
    return secrets.token_hex(16)


@dataclass
class LoopBlock:
    first_started_utc: Optional[str] = None
    last_tick_utc: Optional[str] = None
    last_tick_status: Optional[str] = None
    last_tick_exit_code: Optional[int] = None
    consecutive_no_progress_ticks: int = 0
    ticks_this_week: int = 0
    ticks_total: int = 0
    # If set, loop_tick.py refuses to start and loop_verify.py
    # reports the reason. Set by check #4 or a hard-stop bound.
    halt_reason: Optional[str] = None


@dataclass
class FingerprintBlock:
    last_built_utc: Optional[str] = None
    source_hash: Optional[str] = None


@dataclass
class DiscoveryBlock:
    author_center_cursor: Optional[str] = None
    content_center_cursor: Optional[str] = None
    last_discover_utc: Optional[str] = None
    queued_since_last_run: int = 0


@dataclass
class CitationBlock:
    last_harvest_utc: Optional[str] = None
    bibliography_hash: Optional[str] = None
    registry_pending_verify: int = 0


@dataclass
class QuotasBlock:
    apify_calls_today: int = 0
    apollo_calls_today: int = 0
    openalex_calls_today: int = 0
    day_started_utc: Optional[str] = None


@dataclass
class BoundsBlock:
    max_ticks_per_week: int = 5
    max_consecutive_no_progress: int = 3
    max_apify_per_day: int = 200
    max_apollo_per_day: int = 100
    max_openalex_per_day: int = 500
    wall_clock_deadline_utc: Optional[str] = None
    budget_usd_remaining: float = 0.0
    # Target batch size; the goal is `handoff.drafts_ready_for_review >= n_per_batch`
    n_per_batch: int = 5


@dataclass
class HandoffBlock:
    drafts_ready_for_review: int = 0
    last_calendar_block_id: Optional[str] = None
    last_calendar_block_utc: Optional[str] = None
    calendar_window: str = "1-3pm PT"
    calendar_title_pattern: str = "Review {project} outreach batch ({n} drafts)"


@dataclass
class ChainBlock:
    """Active nonce chain for the in-flight tick. All nonces are single-use
    and cleared after consumption. tick_id binds the chain to one tick so
    a stale nonce from a previous tick can never be replayed."""
    tick_id: Optional[str] = None  # UUID-like, identifies the current tick
    tick_started_utc: Optional[str] = None
    plan_nonce: Optional[str] = None
    plan_nonce_issued_utc: Optional[str] = None
    tracker_nonce: Optional[str] = None
    tracker_nonce_issued_utc: Optional[str] = None
    calendar_nonce: Optional[str] = None
    calendar_nonce_issued_utc: Optional[str] = None
    verifier_nonce: Optional[str] = None
    verifier_nonce_issued_utc: Optional[str] = None
    # Audit: which kinds have been consumed this tick.
    consumed: list[str] = field(default_factory=list)


@dataclass
class State:
    schema_version: int = SCHEMA_VERSION
    project: str = ""
    tracker_path: str = ""
    # §4 Governed Autonomy: the single named human accountable for the
    # outcome of this loop's actions, regardless of how much the machine did.
    release_owner: str = ""
    loop: LoopBlock = field(default_factory=LoopBlock)
    fingerprint: FingerprintBlock = field(default_factory=FingerprintBlock)
    discovery: DiscoveryBlock = field(default_factory=DiscoveryBlock)
    citation: CitationBlock = field(default_factory=CitationBlock)
    quotas: QuotasBlock = field(default_factory=QuotasBlock)
    bounds: BoundsBlock = field(default_factory=BoundsBlock)
    handoff: HandoffBlock = field(default_factory=HandoffBlock)
    chain: ChainBlock = field(default_factory=ChainBlock)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "State":
        if d.get("schema_version") != SCHEMA_VERSION:
            raise StateSchemaError(
                f"state.json schema_version={d.get('schema_version')!r} "
                f"!= expected {SCHEMA_VERSION}; refusing to load"
            )
        return cls(
            schema_version=d["schema_version"],
            project=d.get("project", ""),
            tracker_path=d.get("tracker_path", ""),
            release_owner=d.get("release_owner", ""),
            loop=LoopBlock(**d.get("loop", {})),
            fingerprint=FingerprintBlock(**d.get("fingerprint", {})),
            discovery=DiscoveryBlock(**d.get("discovery", {})),
            citation=CitationBlock(**d.get("citation", {})),
            quotas=QuotasBlock(**d.get("quotas", {})),
            bounds=BoundsBlock(**d.get("bounds", {})),
            handoff=HandoffBlock(**d.get("handoff", {})),
            chain=ChainBlock(**d.get("chain", {})),
        )


class StateSchemaError(Exception):
    """Raised when state.json fails schema validation."""


class StateNotFoundError(Exception):
    """Raised when state.json does not exist. /synergy-loop-start handles this."""


class NonceError(Exception):
    """Raised when a nonce-protected operation fails. The audit log records
    every NonceError so a forensic reader can see who tried to bypass the
    chain and when. Subclasses: NonceMissing, NonceMismatch, NonceReplayed,
    NonceOutOfOrder."""


class NonceMissing(NonceError):
    """The caller didn't present a nonce. Either it forgot, or it's not part
    of the chain."""


class NonceMismatch(NonceError):
    """The presented nonce doesn't match what state.chain has on file.
    A different process issued it, or it's a guess."""


class NonceReplayed(NonceError):
    """The nonce was already consumed in this tick. Replay attempt."""


class NonceOutOfOrder(NonceError):
    """The caller tried to use a nonce kind whose prerequisite hadn't fired.
    e.g. asking for a TRACKER nonce before PLAN ran."""


def state_path(loop_state_dir: Path) -> Path:
    return loop_state_dir / "state.json"


def audit_log_path(loop_state_dir: Path) -> Path:
    """Append-only chain audit log. Every nonce issue/consume/reject lands
    here as one JSON-line. Survives across ticks; the §10 decision log is a
    rollup of this."""
    return loop_state_dir / "chain-audit.jsonl"


def _audit(loop_state_dir: Path, event: str, **kwargs: Any) -> None:
    """Append one JSON line to chain-audit.jsonl. Open-append-close so
    concurrent ticks (shouldn't happen, but) don't corrupt the file."""
    loop_state_dir.mkdir(parents=True, exist_ok=True)
    rec = {"utc": utcnow_iso(), "event": event, **kwargs}
    line = json.dumps(rec, sort_keys=True)
    with open(audit_log_path(loop_state_dir), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load(loop_state_dir: Path) -> State:
    """Load state.json. Raises StateNotFoundError if missing,
    StateSchemaError if schema_version mismatches or JSON is malformed."""
    p = state_path(loop_state_dir)
    if not p.exists():
        raise StateNotFoundError(str(p))
    try:
        raw = p.read_text(encoding="utf-8")
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        raise StateSchemaError(f"state.json is not valid JSON: {e}") from e
    return State.from_dict(d)


def save(loop_state_dir: Path, state: State) -> None:
    """Atomic write: tmp file in same dir, fsync, rename. A half-written
    state.json is never observable."""
    loop_state_dir.mkdir(parents=True, exist_ok=True)
    target = state_path(loop_state_dir)
    # NamedTemporaryFile in the same dir so rename is atomic on the same fs.
    fd, tmp_name = tempfile.mkstemp(
        prefix=".state.", suffix=".tmp", dir=str(loop_state_dir)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, target)
    except Exception:
        # Clean up the tmp on failure so we don't leave litter behind.
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def init(
    loop_state_dir: Path,
    project: str,
    tracker_path: str,
    release_owner: str,
    bounds: Optional[BoundsBlock] = None,
    handoff: Optional[HandoffBlock] = None,
) -> State:
    """Create a fresh state.json. Called once by /synergy-loop-start.
    Refuses to overwrite an existing state.json. release_owner is required —
    §4 Governed Autonomy: no anonymous loops."""
    if not release_owner or not release_owner.strip():
        raise ValueError(
            "release_owner is required. Per Governed Autonomy §4, every loop "
            "must name the human accountable for its outcomes. Pass --owner."
        )
    p = state_path(loop_state_dir)
    if p.exists():
        raise FileExistsError(
            f"state.json already exists at {p}; refusing to overwrite. "
            f"Delete .loop-state/ to reinitialize."
        )
    s = State(
        project=project,
        tracker_path=tracker_path,
        release_owner=release_owner.strip(),
        bounds=bounds or BoundsBlock(),
        handoff=handoff or HandoffBlock(),
    )
    s.loop.first_started_utc = utcnow_iso()
    save(loop_state_dir, s)
    _audit(
        loop_state_dir,
        "loop_initialized",
        project=project,
        release_owner=release_owner.strip(),
    )
    return s


def roll_daily_counters_if_needed(s: State) -> bool:
    """If the UTC day has changed since quotas were last reset, zero them.
    Returns True if a roll happened."""
    today = utc_day(utcnow_iso())
    if s.quotas.day_started_utc != today:
        s.quotas.apify_calls_today = 0
        s.quotas.apollo_calls_today = 0
        s.quotas.openalex_calls_today = 0
        s.quotas.day_started_utc = today
        return True
    return False


def is_halted(s: State) -> bool:
    return bool(s.loop.halt_reason)


def halt(s: State, reason: str) -> None:
    """Set a halt reason. loop_tick.py refuses to run while this is set;
    only manual edit / /synergy-loop-start --force can clear it."""
    s.loop.halt_reason = reason


def record_tick(s: State, status: str, exit_code: int, made_progress: bool) -> None:
    s.loop.last_tick_utc = utcnow_iso()
    s.loop.last_tick_status = status
    s.loop.last_tick_exit_code = exit_code
    s.loop.ticks_total += 1
    s.loop.ticks_this_week += 1
    if made_progress:
        s.loop.consecutive_no_progress_ticks = 0
    else:
        s.loop.consecutive_no_progress_ticks += 1


# --- Nonce chain --------------------------------------------------------------
#
# Public protocol (all calls go through these — never set chain.* directly):
#
#   start_tick(loopdir)               -> (state, tick_id, plan_nonce)
#   issue_nonce(loopdir, kind, ...)   -> nonce  (kind ∈ tracker | calendar | verifier)
#   consume_nonce(loopdir, kind, n)   -> None   (raises NonceError on mismatch)
#   clear_chain(loopdir)              -> None   (end of tick, success or failure)
#
# Invariants enforced:
#   - issue_nonce(TRACKER|CALENDAR|VERIFIER) requires a live plan_nonce on file
#   - consume_nonce burns the nonce (sets the field to None, appends to consumed)
#   - the same nonce cannot be consumed twice (replay -> NonceReplayed)
#   - mismatched nonces never succeed silently — always raise + audit


def start_tick(loop_state_dir: Path) -> tuple[State, str, str]:
    """Begin a new tick. Generates tick_id + plan_nonce, writes them to
    state.chain, and returns (state, tick_id, plan_nonce). The caller (the
    tick's plan command) must pass the plan_nonce on every subsequent
    issue_nonce / consume_nonce call.

    If a previous tick left a chain half-open, that's overwritten — but the
    overwrite is recorded in the audit log so the forensic trail survives."""
    state = load(loop_state_dir)
    if state.chain.tick_id is not None:
        _audit(
            loop_state_dir,
            "chain_overwritten",
            previous_tick_id=state.chain.tick_id,
            previous_started_utc=state.chain.tick_started_utc,
            consumed_so_far=state.chain.consumed,
        )

    tick_id = secrets.token_hex(8)
    plan_nonce = new_nonce()
    now = utcnow_iso()
    state.chain = ChainBlock(
        tick_id=tick_id,
        tick_started_utc=now,
        plan_nonce=plan_nonce,
        plan_nonce_issued_utc=now,
    )
    save(loop_state_dir, state)
    _audit(
        loop_state_dir,
        "tick_started",
        tick_id=tick_id,
        plan_nonce=plan_nonce,
    )
    return state, tick_id, plan_nonce


def issue_nonce(loop_state_dir: Path, kind: str, plan_nonce: str) -> str:
    """Issue a downstream nonce (TRACKER, CALENDAR, or VERIFIER) for the
    current tick. Caller must present the plan_nonce returned by
    start_tick. Raises NonceMismatch if the plan_nonce doesn't match,
    NonceOutOfOrder if there's no active chain."""
    if kind not in (NONCE_TRACKER, NONCE_CALENDAR, NONCE_VERIFIER):
        raise NonceError(f"unknown nonce kind: {kind}")
    state = load(loop_state_dir)
    if state.chain.tick_id is None or state.chain.plan_nonce is None:
        _audit(loop_state_dir, "nonce_issue_no_chain", kind=kind)
        raise NonceOutOfOrder(
            f"cannot issue {kind} nonce: no active tick (call start_tick first)"
        )
    if plan_nonce != state.chain.plan_nonce:
        _audit(
            loop_state_dir,
            "nonce_issue_mismatch",
            kind=kind,
            presented=plan_nonce,
            expected_tick_id=state.chain.tick_id,
        )
        raise NonceMismatch(
            f"presented plan_nonce does not match active tick "
            f"(tick_id={state.chain.tick_id})"
        )

    n = new_nonce()
    now = utcnow_iso()
    if kind == NONCE_TRACKER:
        state.chain.tracker_nonce = n
        state.chain.tracker_nonce_issued_utc = now
    elif kind == NONCE_CALENDAR:
        state.chain.calendar_nonce = n
        state.chain.calendar_nonce_issued_utc = now
    elif kind == NONCE_VERIFIER:
        state.chain.verifier_nonce = n
        state.chain.verifier_nonce_issued_utc = now
    save(loop_state_dir, state)
    _audit(
        loop_state_dir,
        "nonce_issued",
        tick_id=state.chain.tick_id,
        kind=kind,
        nonce=n,
    )
    return n


def consume_nonce(loop_state_dir: Path, kind: str, presented: str) -> None:
    """Consume a single-use nonce. Burns it (sets the field to None) and
    appends to chain.consumed. Subsequent attempts with the same nonce raise
    NonceReplayed.

    The caller is the side that received the nonce: e.g. the tracker writer
    consumes a TRACKER nonce it was handed, the verifier consumes the
    VERIFIER nonce it was issued. The PLAN nonce is consumed at the end of
    resolve, when the chain is cleared."""
    if kind not in ALL_NONCE_KINDS:
        raise NonceError(f"unknown nonce kind: {kind}")
    state = load(loop_state_dir)
    if state.chain.tick_id is None:
        _audit(loop_state_dir, "nonce_consume_no_chain", kind=kind)
        raise NonceOutOfOrder(f"cannot consume {kind} nonce: no active tick")
    if kind in state.chain.consumed:
        _audit(
            loop_state_dir,
            "nonce_replayed",
            tick_id=state.chain.tick_id,
            kind=kind,
            presented=presented,
        )
        raise NonceReplayed(
            f"{kind} nonce already consumed in tick {state.chain.tick_id}"
        )

    stored = {
        NONCE_PLAN: state.chain.plan_nonce,
        NONCE_TRACKER: state.chain.tracker_nonce,
        NONCE_CALENDAR: state.chain.calendar_nonce,
        NONCE_VERIFIER: state.chain.verifier_nonce,
    }[kind]
    if stored is None:
        _audit(
            loop_state_dir,
            "nonce_missing",
            tick_id=state.chain.tick_id,
            kind=kind,
        )
        raise NonceMissing(
            f"no {kind} nonce on file for tick {state.chain.tick_id} "
            f"(was issue_nonce called?)"
        )
    if presented != stored:
        _audit(
            loop_state_dir,
            "nonce_consume_mismatch",
            tick_id=state.chain.tick_id,
            kind=kind,
            presented=presented,
        )
        raise NonceMismatch(
            f"{kind} nonce mismatch for tick {state.chain.tick_id}"
        )

    # Burn it.
    if kind == NONCE_PLAN:
        state.chain.plan_nonce = None
    elif kind == NONCE_TRACKER:
        state.chain.tracker_nonce = None
    elif kind == NONCE_CALENDAR:
        state.chain.calendar_nonce = None
    elif kind == NONCE_VERIFIER:
        state.chain.verifier_nonce = None
    state.chain.consumed.append(kind)
    save(loop_state_dir, state)
    _audit(
        loop_state_dir,
        "nonce_consumed",
        tick_id=state.chain.tick_id,
        kind=kind,
    )


def clear_chain(loop_state_dir: Path, reason: str = "tick_complete") -> None:
    """End-of-tick cleanup. Wipes all chain fields so the next tick starts
    fresh. The audit log preserves the chain history."""
    state = load(loop_state_dir)
    if state.chain.tick_id is None:
        return  # idempotent
    prior_tick = state.chain.tick_id
    consumed = list(state.chain.consumed)
    state.chain = ChainBlock()
    save(loop_state_dir, state)
    _audit(
        loop_state_dir,
        "chain_cleared",
        tick_id=prior_tick,
        consumed=consumed,
        reason=reason,
    )


def chain_status(loop_state_dir: Path) -> dict[str, Any]:
    """Read-only chain snapshot for /synergy-loop-status."""
    state = load(loop_state_dir)
    return {
        "tick_id": state.chain.tick_id,
        "tick_started_utc": state.chain.tick_started_utc,
        "plan_nonce_live": state.chain.plan_nonce is not None,
        "tracker_nonce_live": state.chain.tracker_nonce is not None,
        "calendar_nonce_live": state.chain.calendar_nonce is not None,
        "verifier_nonce_live": state.chain.verifier_nonce is not None,
        "consumed": state.chain.consumed,
    }


if __name__ == "__main__":
    # Tiny smoke test: round-trip a default state + exercise the nonce chain.
    import shutil

    tmp = Path(tempfile.mkdtemp(prefix="loop_state_smoke_"))
    try:
        s = init(
            tmp,
            project="frontier-founder",
            tracker_path="/tmp/tracker.xlsx",
            release_owner="Dorian Cougias",
        )
        assert load(tmp).project == "frontier-founder"
        assert load(tmp).release_owner == "Dorian Cougias"
        s2 = load(tmp)
        s2.discovery.queued_since_last_run = 7
        save(tmp, s2)
        assert load(tmp).discovery.queued_since_last_run == 7

        # Nonce chain
        _, tick_id, pn = start_tick(tmp)
        tn = issue_nonce(tmp, NONCE_TRACKER, pn)
        consume_nonce(tmp, NONCE_TRACKER, tn)
        # Replay should fail
        try:
            consume_nonce(tmp, NONCE_TRACKER, tn)
            raise AssertionError("replay should have raised")
        except NonceReplayed:
            pass
        # Mismatched plan nonce should fail
        try:
            issue_nonce(tmp, NONCE_CALENDAR, "wrong")
            raise AssertionError("mismatch should have raised")
        except NonceMismatch:
            pass
        # init refuses empty owner
        try:
            init(tmp / "x", project="p", tracker_path="t", release_owner=" ")
            raise AssertionError("blank owner should have raised")
        except ValueError:
            pass
        clear_chain(tmp, reason="smoke_test_done")
        assert chain_status(tmp)["tick_id"] is None
        print("loop_state.py smoke test OK")
    finally:
        shutil.rmtree(tmp)
