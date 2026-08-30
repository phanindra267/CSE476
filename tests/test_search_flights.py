"""Tests for search_flights tool."""

import pytest
from src.tools.search_flights import search_flights


class TestSearchFlights:
    """Test search_flights returns correct structured results."""

    def test_basic_route_returns_results(self):
        results = search_flights("DEL", "BOM")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_price_is_numeric(self):
        results = search_flights("DEL", "BOM")
        for f in results:
            assert isinstance(f["price"], (int, float)), "Price must be numeric"

    def test_unknown_route_returns_empty(self):
        results = search_flights("XYZ", "ABC")
        assert results == []

    def test_case_insensitive_airports(self):
        results_upper = search_flights("DEL", "BOM")
        results_lower = search_flights("del", "bom")
        assert len(results_upper) == len(results_lower)

    def test_all_required_fields_present(self):
        required = {
            "flight_id", "airline", "from", "to",
            "departure", "arrival", "duration_minutes",
            "stops", "price",
        }
        results = search_flights("DEL", "BOM")
        for f in results:
            assert required.issubset(set(f.keys())), (
                f"Missing fields: {required - set(f.keys())}"
            )

    def test_multiple_airlines_in_results(self):
        results = search_flights("DEL", "BOM")
        airlines = {f["airline"] for f in results}
        assert len(airlines) > 1, "Should have flights from multiple airlines"

    def test_nonstop_and_connecting_in_results(self):
        results = search_flights("DEL", "BOM")
        stops = {f["stops"] for f in results}
        assert 0 in stops, "Should have non-stop flights"
        assert any(s > 0 for s in stops), "Should have connecting flights"

    def test_same_origin_destination_raises(self):
        with pytest.raises(ValueError):
            search_flights("DEL", "DEL")

    def test_empty_origin_raises(self):
        with pytest.raises(ValueError):
            search_flights("", "BOM")

    def test_empty_destination_raises(self):
        with pytest.raises(ValueError):
            search_flights("DEL", "")

    def test_reverse_route_different_results(self):
        del_bom = search_flights("DEL", "BOM")
        bom_del = search_flights("BOM", "DEL")
        del_ids = {f["flight_id"] for f in del_bom}
        bom_ids = {f["flight_id"] for f in bom_del}
        assert del_ids != bom_ids, "Reverse route should have different flights"

    def test_different_routes_return_results(self):
        """Ensure we have data for multiple routes."""
        assert len(search_flights("DEL", "BLR")) > 0
        assert len(search_flights("BOM", "BLR")) > 0
        assert len(search_flights("HYD", "DEL")) > 0
