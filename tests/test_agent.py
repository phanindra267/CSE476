"""Tests for the FlightAgent plan-act loop."""

import pytest
from src.agent.flight_agent import FlightAgent
from src.agent.memory import ConversationMemory


class TestAgentMultiStep:
    """Test that the agent performs multiple steps and calls both tools."""

    def test_successful_search_returns_success(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 8000")
        assert state.status == "success"
        assert state.selected_flight is not None
        assert state.selected_flight["price"] <= 8000

    def test_multi_step_trace_has_enough_steps(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 8000")
        assert len(state.trace) >= 6, (
            f"Agent should take at least 6 steps, got {len(state.trace)}"
        )

    def test_search_flights_tool_called(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 9000")
        tool_calls = [t for t in state.trace if t.tool == "search_flights"]
        assert len(tool_calls) >= 1, "search_flights must be called"

    def test_compare_price_tool_called(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 9000")
        tool_calls = [t for t in state.trace if t.tool == "compare_price"]
        assert len(tool_calls) >= 1, "compare_price must be called"

    def test_both_tools_called_in_one_run(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 9000")
        tools_used = {t.tool for t in state.trace if t.tool}
        assert "search_flights" in tools_used
        assert "compare_price" in tools_used


class TestAgentDecision:
    """Test agent makes correct decisions based on tool results."""

    def test_selects_flight_under_budget(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 6000")
        if state.status == "success":
            assert state.selected_flight["price"] <= 6000

    def test_second_best_fallback_exists(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 9000")
        if state.status == "success":
            assert state.fallback_flight is not None, "Second-best fallback must exist"

    def test_nonstop_preference_respected(self):
        agent = FlightAgent()
        state = agent.run(
            "Find a non-stop flight from Delhi to Mumbai under 8000"
        )
        if state.status == "success":
            assert state.selected_flight["stops"] == 0, (
                "With non-stop preference, best should be non-stop"
            )

    def test_no_budget_match_handled_honestly(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 2000")
        assert state.status == "no_results"
        assert state.selected_flight is None
        # Should still have a fallback (closest option)
        assert state.fallback_flight is not None

    def test_no_results_provides_reasons(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 2000")
        assert len(state.selection_reasons) > 0

    def test_unknown_route_returns_empty(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from XYZ to ABC under 5000")
        # No flights for XYZ→ABC → should report no results
        assert state.status == "no_results"

    def test_missing_route_returns_error(self):
        agent = FlightAgent()
        state = agent.run("My budget is 8000")
        assert state.status == "error"


class TestAgentMemory:
    """Test that memory persists and influences across turns."""

    def test_budget_stored_in_memory(self):
        agent = FlightAgent()
        agent.run("Find a flight from Delhi to Mumbai under 6000")
        assert agent.memory.budget == 6000

    def test_nonstop_stored_in_memory(self):
        agent = FlightAgent()
        agent.run("Find a non-stop flight from Delhi to Mumbai under 8000")
        assert agent.memory.non_stop_preference is True

    def test_route_stored_in_memory(self):
        agent = FlightAgent()
        agent.run("Find a flight from Delhi to Mumbai under 8000")
        assert agent.memory.origin == "DEL"
        assert agent.memory.destination == "BOM"

    def test_memory_persists_across_turns(self):
        """Critical test: Turn 1 sets preferences, Turn 2 uses them."""
        agent = FlightAgent()

        # Turn 1: set preferences + route
        state1 = agent.run(
            "I want to fly Delhi to Mumbai under 6000. Prefer non-stop."
        )
        assert agent.memory.budget == 6000
        assert agent.memory.non_stop_preference is True
        assert agent.memory.origin == "DEL"
        assert agent.memory.destination == "BOM"

        # Turn 2: only say "find another flight" — memory should fill in route + budget
        state2 = agent.run("Find another suitable flight")
        # The agent should have used the remembered route
        assert state2.origin == "DEL"
        assert state2.destination == "BOM"
        assert state2.budget == 6000

    def test_memory_read_appears_in_trace(self):
        agent = FlightAgent()
        agent.run("Find a flight from Delhi to Mumbai under 7000")
        state2 = agent.run("Find another flight")
        memory_reads = [
            t for t in state2.trace if t.action == "retrieve_memory"
        ]
        assert len(memory_reads) >= 1
        assert "7,000" in str(memory_reads[0].result) or "DEL" in str(memory_reads[0].result)

    def test_memory_update_appears_in_trace(self):
        agent = FlightAgent()
        state = agent.run("Find a flight from Delhi to Mumbai under 8000")
        memory_updates = [
            t for t in state.trace if t.action == "memory_update"
        ]
        assert len(memory_updates) >= 1

    def test_turn_count_increments(self):
        agent = FlightAgent()
        agent.run("Find a flight from Delhi to Mumbai under 8000")
        assert agent.memory.turn_count == 1
        agent.run("Find another flight")
        assert agent.memory.turn_count == 2
