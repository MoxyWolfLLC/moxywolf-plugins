"""Custom mcp-eval evaluators for bank semantics mcp-eval does not ship.

mcp-eval 0.1.10 has no "first tool was one of", no call-count ceiling, and no
liveness check. Without these, the export would have to approximate the bank,
and the two harnesses would grade the same question differently.

Import this module BEFORE `Dataset.from_file`: the loader resolves evaluator
names through the registry and silently drops names it does not know, so an
unregistered evaluator is a check that quietly never runs. run_mcpeval.py
imports it and then asserts every evaluator name in the dataset resolved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

try:  # Importable without mcp-eval so the plugin's stdlib tests can load it.
    from mcp_eval.evaluators import register_evaluator
    from mcp_eval.evaluators.base import EvaluatorContext, SyncEvaluator
    from mcp_eval.evaluators.shared import EvaluatorResult

    HAVE_MCP_EVAL = True
except Exception:  # pragma: no cover - exercised only where mcp-eval is absent
    HAVE_MCP_EVAL = False

    class SyncEvaluator:  # type: ignore[no-redef]
        pass

    @dataclass
    class EvaluatorResult:  # type: ignore[no-redef]
        passed: bool
        expected: Any = None
        actual: Any = None
        score: float | None = None
        details: Dict[str, Any] | None = None

    EvaluatorContext = Any  # type: ignore[misc,assignment]

    def register_evaluator(name, cls):  # type: ignore[no-redef]
        return None


def _names(ctx) -> List[str]:
    # mcp-eval's metrics already strip the "<server>_" namespace mcp-agent adds,
    # so these are the server's own tool names.
    return [c.name for c in (ctx.tool_calls or [])]


@dataclass
class FirstToolIn(SyncEvaluator):
    """The first tool the agent called is one of `tool_names`."""

    tool_names: List[str] = field(default_factory=list)
    requires_final_metrics: bool = True

    def evaluate_sync(self, ctx) -> EvaluatorResult:
        names = _names(ctx)
        first = names[0] if names else None
        return EvaluatorResult(passed=first in self.tool_names, expected=f"first tool in {self.tool_names}", actual=first, details={"sequence": names})

    def to_dict(self) -> Dict[str, Any]:
        return {"tool_names": list(self.tool_names)}


@dataclass
class ToolCallsAtMost(SyncEvaluator):
    """The agent made at most `max_calls` tool calls in total."""

    max_calls: int = 1
    requires_final_metrics: bool = True

    def evaluate_sync(self, ctx) -> EvaluatorResult:
        n = len(ctx.tool_calls or [])
        return EvaluatorResult(passed=n <= self.max_calls, expected=f"<= {self.max_calls}", actual=n)

    def to_dict(self) -> Dict[str, Any]:
        return {"max_calls": self.max_calls}


@dataclass
class AnsweredWithoutToolErrors(SyncEvaluator):
    """Discovery liveness: a non-empty final answer and no tool call errored.

    A typed absence (an explained 404 payload) is not a tool error, so a server
    that correctly says "we do not hold that" still passes.
    """

    requires_final_metrics: bool = True

    def evaluate_sync(self, ctx) -> EvaluatorResult:
        text = ctx.output if isinstance(ctx.output, str) else str(ctx.output or "")
        errors = [c.name for c in (ctx.tool_calls or []) if getattr(c, "is_error", False)]
        ok = bool(text.strip()) and not errors
        return EvaluatorResult(passed=ok, expected="non-empty answer, no tool errors", actual={"answer_chars": len(text.strip()), "errored_tools": errors})

    def to_dict(self) -> Dict[str, Any]:
        return {}


@dataclass
class ToolSequence(SyncEvaluator):
    """Recorder, always passes. Writes the tool names in call order into the
    report, because mcp-eval's report keeps only a tool-call count. results.py
    needs the sequence to see wrong-tool failures and to propose promotions."""

    requires_final_metrics: bool = True

    def evaluate_sync(self, ctx) -> EvaluatorResult:
        names = _names(ctx)
        return EvaluatorResult(passed=True, expected="recorded", actual=len(names), details={"sequence": names})

    def to_dict(self) -> Dict[str, Any]:
        return {}


CUSTOM = {"ToolSequence": ToolSequence, "FirstToolIn": FirstToolIn, "ToolCallsAtMost": ToolCallsAtMost, "AnsweredWithoutToolErrors": AnsweredWithoutToolErrors}

for _name, _cls in CUSTOM.items():
    register_evaluator(_name, _cls)
