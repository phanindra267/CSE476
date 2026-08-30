"""Tests for ConversationMemory."""

import pytest
from src.agent.memory import ConversationMemory


class TestMemoryStorage:
    """Test that memory stores and retrieves preferences correctly."""

    def test_initial_state_is_empty(self):
        mem = ConversationMemory()
        assert mem.budget is None
        assert mem.origin is None
        assert mem.destination is None
        assert mem.non_stop_preference is False
        assert mem.preferred_time is None
        assert mem.turn_count == 0

    def test_store_budget(self):
        mem = ConversationMemory()
        mem.store("budget", 6000.0)
        assert mem.budget == 6000.0

    def test_store_origin(self):
        mem = ConversationMemory()
        mem.store("origin", "DEL")
        assert mem.origin == "DEL"

    def test_store_destination(self):
        mem = ConversationMemory()
        mem.store("destination", "BOM")
        assert mem.destination == "BOM"

    def test_store_non_stop(self):
        mem = ConversationMemory()
        mem.store("non_stop_preference", True)
        assert mem.non_stop_preference is True

    def test_store_preferred_time(self):
        mem = ConversationMemory()
        mem.store("preferred_time", "morning")
        assert mem.preferred_time == "morning"

    def test_store_ignores_unknown_keys(self):
        mem = ConversationMemory()
        mem.store("unknown_key", "value")  # Should not crash
        assert not hasattr(mem, "unknown_key") or getattr(mem, "unknown_key", None) is None


class TestMemoryRetrieval:
    """Test that memory is read back correctly."""

    def test_get_preferences_returns_all_fields(self):
        mem = ConversationMemory()
        mem.budget = 7000
        mem.origin = "DEL"
        mem.destination = "BOM"
        mem.non_stop_preference = True
        prefs = mem.get_preferences()
        assert prefs["budget"] == 7000
        assert prefs["origin"] == "DEL"
        assert prefs["destination"] == "BOM"
        assert prefs["non_stop_preference"] is True

    def test_has_route_true(self):
        mem = ConversationMemory()
        mem.origin = "DEL"
        mem.destination = "BOM"
        assert mem.has_route() is True

    def test_has_route_false_missing_origin(self):
        mem = ConversationMemory()
        mem.destination = "BOM"
        assert mem.has_route() is False

    def test_summary_str_with_data(self):
        mem = ConversationMemory()
        mem.budget = 6000
        mem.origin = "DEL"
        s = mem.summary_str()
        assert "6,000" in s
        assert "DEL" in s

    def test_summary_str_empty(self):
        mem = ConversationMemory()
        s = mem.summary_str()
        assert "Empty" in s or "empty" in s.lower()


class TestMemoryPersistence:
    """Test that memory persists across turns (critical rubric item)."""

    def test_record_turn_increments_count(self):
        mem = ConversationMemory()
        mem.record_turn({"goal": "test"})
        assert mem.turn_count == 1
        mem.record_turn({"goal": "test2"})
        assert mem.turn_count == 2

    def test_memory_influences_later_turn(self):
        """Simulate Turn 1 setting budget, Turn 2 using it."""
        mem = ConversationMemory()

        # Turn 1: set budget
        mem.budget = 6000
        mem.origin = "DEL"
        mem.destination = "BOM"
        mem.non_stop_preference = True
        mem.record_turn({"goal": "set preferences"})

        # Turn 2: read back
        prefs = mem.get_preferences()
        assert prefs["budget"] == 6000
        assert prefs["origin"] == "DEL"
        assert prefs["destination"] == "BOM"
        assert prefs["non_stop_preference"] is True
        assert prefs["turn_count"] == 1

    def test_clear_resets_everything(self):
        mem = ConversationMemory()
        mem.budget = 8000
        mem.origin = "DEL"
        mem.clear()
        assert mem.budget is None
        assert mem.origin is None
        assert mem.turn_count == 0
