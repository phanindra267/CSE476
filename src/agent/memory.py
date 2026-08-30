"""
Conversation memory — persists user preferences across turns.

Stores:
  - budget
  - origin / destination
  - non_stop preference
  - preferred_time (morning / afternoon / evening)
  - last selected flight
  - turn history

The memory is an in-process session store. No external database needed.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationMemory:
    """
    In-session memory that persists across multiple user turns.

    The agent WRITES to memory after each turn and READS from memory
    at the start of each subsequent turn to apply remembered constraints.
    """

    # Hard constraints
    budget: Optional[float] = None
    origin: Optional[str] = None
    destination: Optional[str] = None

    # Soft preferences
    non_stop_preference: bool = False
    preferred_time: Optional[str] = None  # "morning" | "afternoon" | "evening"

    # Last recommendation
    last_selected_flight: Optional[Dict[str, Any]] = None

    # Turn history
    turn_count: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)

    # ── Write operations ──────────────────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        """Store a named preference in memory."""
        if hasattr(self, key):
            setattr(self, key, value)

    def record_turn(self, turn_summary: Dict[str, Any]) -> None:
        """Record a completed turn in history."""
        self.turn_count += 1
        self.history.append(
            {"turn": self.turn_count, **turn_summary}
        )

    # ── Read operations ───────────────────────────────────────────────────────

    def get_preferences(self) -> Dict[str, Any]:
        """Return all currently stored preferences as a dict."""
        return {
            "budget": self.budget,
            "origin": self.origin,
            "destination": self.destination,
            "non_stop_preference": self.non_stop_preference,
            "preferred_time": self.preferred_time,
            "last_selected_flight": self.last_selected_flight,
            "turn_count": self.turn_count,
        }

    def has_route(self) -> bool:
        """Check whether origin and destination are both set."""
        return bool(self.origin and self.destination)

    def summary_str(self) -> str:
        """Human-readable summary of stored memory."""
        parts = []
        if self.budget is not None:
            parts.append(f"Budget=₹{self.budget:,.0f}")
        if self.origin:
            parts.append(f"Origin={self.origin}")
        if self.destination:
            parts.append(f"Destination={self.destination}")
        if self.non_stop_preference:
            parts.append("Non-stop=Yes")
        if self.preferred_time:
            parts.append(f"Time={self.preferred_time}")
        if self.last_selected_flight:
            parts.append(
                f"Last flight={self.last_selected_flight.get('flight_id', '?')}"
            )
        return ", ".join(parts) if parts else "Empty (no prior preferences)"

    # ── Reset ─────────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Reset all memory to defaults."""
        self.budget = None
        self.origin = None
        self.destination = None
        self.non_stop_preference = False
        self.preferred_time = None
        self.last_selected_flight = None
        self.turn_count = 0
        self.history.clear()
