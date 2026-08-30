"""
FlightAgent — the core agent with a visible PLAN → ACT → OBSERVE → DECIDE loop.

Architecture:
    User Goal → Memory Retrieval → Plan → search_flights() → Observe →
    compare_price() → Observe → Decision Engine → Memory Update → Response

The agent loop is a while-loop that transitions through named states,
calling real tools and making decisions based on tool results.
"""

from typing import Any, Dict, List, Optional

from .memory import ConversationMemory
from .planner import parse_user_request
from .state import AgentState
from ..tools.search_flights import search_flights
from ..tools.compare_price import compare_price


class FlightAgent:
    """
    An AI agent that finds and picks flights within a user's budget.

    Implements a genuine multi-step agent loop:
      init → retrieve_memory → parse_request → create_plan →
      execute_search → observe_search → execute_compare →
      observe_compare → decision → memory_update → end

    Memory persists across multiple turns in the same session.
    """

    def __init__(self, memory: Optional[ConversationMemory] = None):
        self.memory = memory if memory is not None else ConversationMemory()

    # ══════════════════════════════════════════════════════════════════════════
    #  STEP HANDLERS — Each corresponds to one state in the agent loop.
    # ══════════════════════════════════════════════════════════════════════════

    def _step_retrieve_memory(self, state: AgentState) -> None:
        """STEP 1: Read previously stored memory and apply to this run."""
        mem_summary = self.memory.summary_str()
        state.add_trace(
            action="retrieve_memory",
            tool="memory",
            input=f"session (turn {self.memory.turn_count + 1})",
            result=mem_summary,
            decision="Use remembered preferences for this turn",
        )

        # Apply remembered values as defaults for this run
        if self.memory.budget and state.budget is None:
            state.budget = self.memory.budget
        if self.memory.origin and state.origin is None:
            state.origin = self.memory.origin
        if self.memory.destination and state.destination is None:
            state.destination = self.memory.destination
        if self.memory.non_stop_preference and not state.non_stop:
            state.non_stop = self.memory.non_stop_preference
        if self.memory.preferred_time and state.preferred_time is None:
            state.preferred_time = self.memory.preferred_time

        state.current_step = "parse_request"

    def _step_parse_request(self, state: AgentState) -> None:
        """STEP 2: Parse the user's natural-language request."""
        intent = parse_user_request(state.user_goal)

        # Override state with newly parsed values (new input takes priority)
        if "origin" in intent:
            state.origin = intent["origin"]
        if "destination" in intent:
            state.destination = intent["destination"]
        if "budget" in intent:
            state.budget = intent["budget"]
        if intent.get("non_stop"):
            state.non_stop = True
        if "preferred_time" in intent:
            state.preferred_time = intent["preferred_time"]

        state.add_trace(
            action="parse_request",
            tool="planner",
            input=state.user_goal,
            result=intent,
            decision="Extracted user intent from natural language",
        )
        state.current_step = "create_plan"

    def _step_create_plan(self, state: AgentState) -> None:
        """STEP 3: Create an execution plan based on parsed intent."""
        # Validate we have enough info
        if not state.origin or not state.destination:
            state.add_trace(
                action="plan",
                input={"origin": state.origin, "destination": state.destination},
                result="Missing origin or destination",
                decision="Cannot proceed — need both origin and destination",
            )
            state.status = "error"
            state.current_step = "end"
            return

        plan = [
            f"1. search_flights({state.origin} → {state.destination})",
        ]
        if state.budget:
            plan.append(f"2. Filter by budget ≤ ₹{state.budget:,.0f}")
        else:
            plan.append("2. Evaluate all results (no budget constraint)")
        plan.append("3. compare_price() on candidates")
        prefs = []
        if state.non_stop:
            prefs.append("non-stop")
        if state.preferred_time:
            prefs.append(state.preferred_time)
        if prefs:
            plan.append(f"4. Apply preferences: {', '.join(prefs)}")
        plan.append(f"{'5' if prefs else '4'}. Select best + second-best")

        state.plan = plan
        state.add_trace(
            action="plan",
            input={
                "origin": state.origin,
                "destination": state.destination,
                "budget": state.budget,
                "non_stop": state.non_stop,
                "preferred_time": state.preferred_time,
            },
            result=plan,
            decision="Execute search → compare → decide",
        )
        state.current_step = "execute_search"

    def _step_execute_search(self, state: AgentState) -> None:
        """STEP 4: Call search_flights() tool."""
        tool_input = {"from": state.origin, "to": state.destination}

        try:
            results = search_flights(state.origin, state.destination)
            state.search_results = results

            # Build compact summary for trace
            summary = f"{len(results)} flight(s) found"
            if results:
                prices = [f["price"] for f in results]
                summary += f" (₹{min(prices):,.0f} – ₹{max(prices):,.0f})"

            state.add_trace(
                action="tool_call",
                tool="search_flights",
                input=tool_input,
                result=summary,
                decision="Proceed to observe results" if results else "No flights found",
            )
        except (ValueError, FileNotFoundError) as e:
            state.search_results = []
            state.add_trace(
                action="tool_call",
                tool="search_flights",
                input=tool_input,
                result=f"ERROR: {str(e)}",
                decision="Search failed — report error",
            )

        state.current_step = "observe_search"

    def _step_observe_search(self, state: AgentState) -> None:
        """STEP 5: Observe search results, apply budget filter, decide next step."""
        all_flights = list(state.search_results)

        if not all_flights:
            state.add_trace(
                action="observe",
                tool="agent",
                result="No flights returned by search",
                decision="Skip comparison — report no results",
            )
            state.status = "no_results"
            state.current_step = "decision"
            return

        # Apply budget hard constraint
        if state.budget is not None:
            under = [f for f in all_flights if f["price"] <= state.budget]
            over = [f for f in all_flights if f["price"] > state.budget]
            state.add_trace(
                action="observe",
                tool="agent",
                input=f"Budget filter ≤ ₹{state.budget:,.0f}",
                result=f"{len(under)} under budget, {len(over)} over budget",
                decision=(
                    "Compare under-budget options"
                    if under
                    else "No flights under budget — compare all to find closest"
                ),
            )
            # If nothing under budget, keep ALL for comparison so we can
            # show the closest option in the no-results message.
            if under:
                state.search_results = under
            # else: keep all results for the compare step
        else:
            state.add_trace(
                action="observe",
                tool="agent",
                result=f"All {len(all_flights)} flights are candidates (no budget set)",
                decision="Compare all options",
            )

        state.current_step = "execute_compare"

    def _step_execute_compare(self, state: AgentState) -> None:
        """STEP 6: Call compare_price() tool."""
        options = state.search_results
        tool_input = {
            "options_count": len(options),
            "budget": state.budget,
        }

        try:
            comp = compare_price(options, budget=state.budget)
            state.comparison_result = comp

            state.add_trace(
                action="tool_call",
                tool="compare_price",
                input=tool_input,
                result=comp.get("summary", "Comparison done"),
                decision="Proceed to decision engine",
            )
        except (TypeError, Exception) as e:
            state.comparison_result = {}
            state.add_trace(
                action="tool_call",
                tool="compare_price",
                input=tool_input,
                result=f"ERROR: {str(e)}",
                decision="Comparison failed — use raw search results",
            )

        state.current_step = "decision"

    def _step_decision(self, state: AgentState) -> None:
        """
        STEP 7: Decision engine — select best flight based on:
          1. Budget compliance
          2. Non-stop preference
          3. Price (lower is better)
          4. Second-best fallback (always provided if available)
        """
        comp = state.comparison_result
        all_results = state.search_results

        # ── Case: no flights at all ───────────────────────────────────────────
        if not all_results:
            state.status = "no_results"
            state.selection_reasons = [
                "No flights found for this route."
            ]
            state.add_trace(
                action="decision",
                tool="agent",
                result="No flights available",
                decision="Inform user — no flights for route",
            )
            state.current_step = "memory_update"
            return

        # ── Case: budget set but nothing under budget ─────────────────────────
        under = comp.get("under_budget", [])
        if state.budget is not None and not under:
            # Find closest options
            sorted_all = sorted(all_results, key=lambda f: f["price"])
            closest = sorted_all[0]
            second = sorted_all[1] if len(sorted_all) > 1 else None
            gap = closest["price"] - state.budget

            state.selected_flight = None
            state.fallback_flight = closest
            state.status = "no_results"
            state.selection_reasons = [
                f"No flight fits the ₹{state.budget:,.0f} budget.",
                f"Cheapest available: {closest['flight_id']} ({closest['airline']}) "
                f"at ₹{closest['price']:,.0f} — ₹{gap:,.0f} over budget.",
            ]
            if second:
                state.selection_reasons.append(
                    f"Second-cheapest: {second['flight_id']} ({second['airline']}) "
                    f"at ₹{second['price']:,.0f}."
                )
                # Store second as well for display
                state.fallback_flight = closest  # cheapest overall

            state.add_trace(
                action="decision",
                tool="agent",
                input=f"Budget=₹{state.budget:,.0f}",
                result=f"No options under budget. Closest: ₹{closest['price']:,.0f}",
                decision="Report honestly — budget cannot be met",
            )
            state.current_step = "memory_update"
            return

        # ── Case: we have valid candidates ────────────────────────────────────
        candidates = under if (state.budget is not None and under) else all_results

        # Apply non-stop + price scoring
        scored: List[Dict[str, Any]] = []
        for f in candidates:
            score = 0.0
            # Lower price → higher score (normalized to 0–10 range)
            prices = [c["price"] for c in candidates]
            price_range = max(prices) - min(prices) if len(prices) > 1 else 1
            price_score = (
                ((max(prices) - f["price"]) / price_range) * 5
                if price_range > 0
                else 5
            )
            score += price_score

            # Non-stop bonus
            if state.non_stop and f.get("stops", 0) == 0:
                score += 5
            elif not state.non_stop and f.get("stops", 0) == 0:
                score += 2  # mild preference for non-stop even without explicit pref

            # Time preference bonus
            dep = f.get("departure", "12:00")
            if state.preferred_time == "morning" and "06:00" <= dep < "12:00":
                score += 3
            elif state.preferred_time == "afternoon" and "12:00" <= dep < "17:00":
                score += 3
            elif state.preferred_time == "evening" and "17:00" <= dep < "23:00":
                score += 3

            scored.append({**f, "_score": round(score, 2)})

        scored.sort(key=lambda x: x["_score"], reverse=True)

        best = scored[0]
        second = scored[1] if len(scored) > 1 else None

        state.selected_flight = best
        state.fallback_flight = second
        state.status = "success"

        # Build reasons
        reasons = []
        if state.budget:
            saving = state.budget - best["price"]
            reasons.append(
                f"₹{best['price']:,.0f} — ₹{saving:,.0f} under your "
                f"₹{state.budget:,.0f} budget"
            )
        else:
            reasons.append(f"₹{best['price']:,.0f}")

        if best.get("stops", 0) == 0:
            reasons.append("Non-stop flight")
        else:
            reasons.append(f"{best['stops']} stop(s)")

        if state.preferred_time:
            dep = best.get("departure", "")
            if state.preferred_time == "morning" and "06:00" <= dep < "12:00":
                reasons.append(f"Morning departure ({dep}) — matches preference")
            elif state.preferred_time == "afternoon" and "12:00" <= dep < "17:00":
                reasons.append(f"Afternoon departure ({dep}) — matches preference")
            elif state.preferred_time == "evening" and "17:00" <= dep < "23:00":
                reasons.append(f"Evening departure ({dep}) — matches preference")

        state.selection_reasons = reasons

        # Trace the decision
        decision_text = (
            f"Best: {best['flight_id']} ({best['airline']}) at ₹{best['price']:,.0f}"
        )
        if second:
            decision_text += (
                f" | Second-best: {second['flight_id']} ({second['airline']}) "
                f"at ₹{second['price']:,.0f}"
            )

        state.add_trace(
            action="decision",
            tool="agent",
            input="Scored and ranked candidates",
            result=decision_text,
            decision="Selected best option based on budget + preferences",
        )
        state.current_step = "memory_update"

    def _step_memory_update(self, state: AgentState) -> None:
        """STEP 8: Update persistent memory with this turn's info."""
        # Write preferences to memory
        if state.budget is not None:
            self.memory.budget = state.budget
        if state.origin:
            self.memory.origin = state.origin
        if state.destination:
            self.memory.destination = state.destination
        if state.non_stop:
            self.memory.non_stop_preference = state.non_stop
        if state.preferred_time:
            self.memory.preferred_time = state.preferred_time
        if state.selected_flight:
            self.memory.last_selected_flight = state.selected_flight

        # Record turn
        self.memory.record_turn({
            "goal": state.user_goal,
            "status": state.status,
            "selected": (
                state.selected_flight.get("flight_id")
                if state.selected_flight
                else None
            ),
        })

        state.add_trace(
            action="memory_update",
            tool="memory",
            input="Write preferences and result",
            result=self.memory.summary_str(),
            decision="Memory updated for future turns",
        )
        state.current_step = "end"

    # ══════════════════════════════════════════════════════════════════════════
    #  MAIN AGENT LOOP
    # ══════════════════════════════════════════════════════════════════════════

    def run(self, user_goal: str) -> AgentState:
        """
        Execute the agent's plan-act-observe-decide loop for one user request.

        Parameters
        ----------
        user_goal : str
            The user's natural-language flight request.

        Returns
        -------
        AgentState
            Full state including trace, recommendation, and reasons.
        """
        state = AgentState(user_goal=user_goal)

        # Step handler dispatch table
        HANDLERS = {
            "init":             self._step_retrieve_memory,
            "parse_request":    self._step_parse_request,
            "create_plan":      self._step_create_plan,
            "execute_search":   self._step_execute_search,
            "observe_search":   self._step_observe_search,
            "execute_compare":  self._step_execute_compare,
            "decision":         self._step_decision,
            "memory_update":    self._step_memory_update,
        }

        MAX_STEPS = 20  # safety guard
        steps = 0

        while state.current_step != "end" and steps < MAX_STEPS:
            handler = HANDLERS.get(state.current_step)
            if handler is None:
                state.add_trace(
                    action="error",
                    result=f"Unknown step: {state.current_step}",
                    decision="Stopping agent loop",
                )
                break
            handler(state)
            steps += 1

        return state

    # ══════════════════════════════════════════════════════════════════════════
    #  CONVENIENCE METHODS
    # ══════════════════════════════════════════════════════════════════════════

    def get_response_text(self, state: AgentState) -> str:
        """Generate a human-readable response from the agent state."""
        lines = []

        if state.status == "error":
            lines.append(
                "❌ I need both an origin and a destination to search. "
                "Please specify them (e.g., 'Find a flight from Delhi to Mumbai')."
            )
            return "\n".join(lines)

        if state.status == "no_results":
            lines.append("⚠️ " + " ".join(state.selection_reasons))
            if state.fallback_flight:
                fb = state.fallback_flight
                lines.append(
                    f"\n💡 Closest option: {fb['flight_id']} ({fb['airline']}) — "
                    f"₹{fb['price']:,.0f}"
                )
            return "\n".join(lines)

        # Success
        best = state.selected_flight
        if best:
            lines.append("✅ **Recommended Flight**")
            stop_label = "Non-stop" if best.get("stops", 0) == 0 else f"{best['stops']} stop(s)"
            lines.append(
                f"   {best['flight_id']} | {best['airline']} | "
                f"{best.get('from', state.origin)}→{best.get('to', state.destination)} | "
                f"{best['departure']}–{best['arrival']} | "
                f"₹{best['price']:,.0f} | {stop_label}"
            )
            for reason in state.selection_reasons:
                lines.append(f"   • {reason}")

        fb = state.fallback_flight
        if fb:
            lines.append(f"\n🔄 **Second-best Fallback**")
            stop_label = "Non-stop" if fb.get("stops", 0) == 0 else f"{fb['stops']} stop(s)"
            lines.append(
                f"   {fb['flight_id']} | {fb['airline']} | "
                f"₹{fb['price']:,.0f} | {stop_label}"
            )
            if best and fb:
                diff = abs(fb['price'] - best['price'])
                lines.append(f"   • ₹{diff:,.0f} {'more' if fb['price'] > best['price'] else 'less'} than recommended")

        return "\n".join(lines)

    def reset_memory(self) -> None:
        """Clear all memory (new session)."""
        self.memory.clear()
