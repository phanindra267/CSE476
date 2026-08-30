"""Tests for compare_price tool."""

import pytest
from src.tools.compare_price import compare_price


def _flight(fid: str, price: float, stops: int = 0) -> dict:
    """Helper to create a flight dict for testing."""
    return {
        "flight_id": fid,
        "airline": "Test Airline",
        "from": "DEL",
        "to": "BOM",
        "departure": "09:00",
        "arrival": "11:00",
        "duration_minutes": 120,
        "stops": stops,
        "price": price,
    }


class TestComparePrice:
    """Test compare_price correctly finds cheapest, second-best, and budget splits."""

    def test_empty_returns_no_results(self):
        result = compare_price([])
        assert result["cheapest"] is None
        assert result["second_best"] is None
        assert result["under_budget"] == []

    def test_single_option(self):
        result = compare_price([_flight("FL01", 7000)])
        assert result["cheapest"]["flight_id"] == "FL01"
        assert result["second_best"] is None
        assert result["price_difference"] is None

    def test_correctly_finds_cheapest(self):
        options = [_flight("FL01", 8000), _flight("FL02", 5500)]
        result = compare_price(options)
        assert result["cheapest"]["flight_id"] == "FL02"

    def test_correctly_finds_second_best(self):
        options = [
            _flight("FL01", 9000),
            _flight("FL02", 5500),
            _flight("FL03", 7000),
        ]
        result = compare_price(options)
        assert result["cheapest"]["flight_id"] == "FL02"
        assert result["second_best"]["flight_id"] == "FL03"

    def test_price_difference(self):
        options = [_flight("FL01", 8000), _flight("FL02", 6500)]
        result = compare_price(options)
        assert result["price_difference"] == pytest.approx(1500.0)

    def test_budget_splits_correctly(self):
        options = [
            _flight("FL01", 5000),
            _flight("FL02", 7000),
            _flight("FL03", 9000),
        ]
        result = compare_price(options, budget=6000)
        assert len(result["under_budget"]) == 1
        assert result["under_budget"][0]["flight_id"] == "FL01"
        assert len(result["over_budget"]) == 2

    def test_nonstop_under_budget(self):
        options = [
            _flight("FL01", 5000, stops=0),
            _flight("FL02", 4500, stops=1),
            _flight("FL03", 7000, stops=0),
        ]
        result = compare_price(options, budget=6000)
        nonstop = result["nonstop_under_budget"]
        assert len(nonstop) == 1
        assert nonstop[0]["flight_id"] == "FL01"

    def test_no_budget_returns_all_under(self):
        options = [_flight("FL01", 5000), _flight("FL02", 7000)]
        result = compare_price(options)
        assert len(result["under_budget"]) == 2

    def test_summary_is_nonempty_string(self):
        options = [_flight("FL01", 7000), _flight("FL02", 8000)]
        result = compare_price(options)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_invalid_input_type_raises(self):
        with pytest.raises(TypeError):
            compare_price("not a list")

    def test_all_over_budget(self):
        options = [_flight("FL01", 8000), _flight("FL02", 9000)]
        result = compare_price(options, budget=5000)
        assert len(result["under_budget"]) == 0
        assert len(result["over_budget"]) == 2
        assert result["cheapest"]["flight_id"] == "FL01"
