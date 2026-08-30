"""
Agent state — tracks the full state for a single agent run.

Contains the user goal, parsed intent, tool results, trace log,
and the final recommendation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class TraceEntry:
    """One step in the agent's execution trace."""
    step: int
    action: str
    tool: Optional[str] = None
    input: Optional[Any] = None
    result: Optional[Any] = None
    decision: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"step": self.step, "action": self.action}
        if self.tool:
            d["tool"] = self.tool
        if self.input is not None:
            d["input"] = self.input
        if self.result is not None:
            d["result"] = self.result
        if self.decision:
            d["decision"] = self.decision
        return d


@dataclass
class AgentState:
    """
    Full state for one agent run (one user request).

    The agent loop reads and writes this state at every step.
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    user_goal: str = ""

    # ── Parsed intent ─────────────────────────────────────────────────────────
    origin: Optional[str] = None
    destination: Optional[str] = None
    budget: Optional[float] = None
    non_stop: bool = False
    preferred_time: Optional[str] = None

    # ── Workflow state ────────────────────────────────────────────────────────
    current_step: str = "init"
    status: str = "running"  # running | success | no_results | error
    plan: List[str] = field(default_factory=list)

    # ── Tool results ──────────────────────────────────────────────────────────
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    comparison_result: Dict[str, Any] = field(default_factory=dict)

    # ── Decision output ───────────────────────────────────────────────────────
    selected_flight: Optional[Dict[str, Any]] = None
    fallback_flight: Optional[Dict[str, Any]] = None
    selection_reasons: List[str] = field(default_factory=list)

    # ── Trace ─────────────────────────────────────────────────────────────────
    trace: List[TraceEntry] = field(default_factory=list)
    _step_counter: int = 0

    def add_trace(
        self,
        action: str,
        tool: Optional[str] = None,
        input: Optional[Any] = None,
        result: Optional[Any] = None,
        decision: Optional[str] = None,
    ) -> TraceEntry:
        """Append a trace entry and return it."""
        self._step_counter += 1
        entry = TraceEntry(
            step=self._step_counter,
            action=action,
            tool=tool,
            input=input,
            result=result,
            decision=decision,
        )
        self.trace.append(entry)
        return entry

    def get_trace_dicts(self) -> List[dict]:
        """Return the trace as a list of plain dicts."""
        return [t.to_dict() for t in self.trace]
