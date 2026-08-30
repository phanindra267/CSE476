"""
Tool 1: search_flights(from_city, to_city)

Searches the local flight dataset for matching routes.
Returns a list of flight dictionaries.
"""

import json
import os
from typing import Any, Dict, List

# Locate data/flights.json relative to this file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_THIS_DIR, "..", ".."))
_DATA_PATH = os.path.join(_PROJECT_ROOT, "data", "flights.json")

# In-memory cache
_FLIGHT_CACHE: List[Dict[str, Any]] | None = None


def _load_flights() -> List[Dict[str, Any]]:
    """Load flight data from JSON file with caching."""
    global _FLIGHT_CACHE
    if _FLIGHT_CACHE is not None:
        return _FLIGHT_CACHE

    paths_to_try = [
        _DATA_PATH,
        os.path.join(os.getcwd(), "data", "flights.json"),
    ]

    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _FLIGHT_CACHE = json.load(f)
            return _FLIGHT_CACHE

    raise FileNotFoundError(
        f"flights.json not found. Tried:\n" + "\n".join(paths_to_try)
    )


def _reset_cache() -> None:
    """Reset the flight cache (useful for testing)."""
    global _FLIGHT_CACHE
    _FLIGHT_CACHE = None


def search_flights(from_city: str, to_city: str) -> List[Dict[str, Any]]:
    """
    Search for flights between two cities.

    Parameters
    ----------
    from_city : str
        Origin city IATA code (e.g., "DEL"). Case-insensitive.
    to_city : str
        Destination city IATA code (e.g., "BOM"). Case-insensitive.

    Returns
    -------
    list[dict]
        List of matching flight dictionaries. Empty list if no matches.

    Raises
    ------
    ValueError
        If from_city or to_city is empty/invalid.
    """
    # Input validation
    if not from_city or not isinstance(from_city, str):
        raise ValueError("from_city must be a non-empty string")
    if not to_city or not isinstance(to_city, str):
        raise ValueError("to_city must be a non-empty string")

    from_city = from_city.strip().upper()
    to_city = to_city.strip().upper()

    if from_city == to_city:
        raise ValueError(
            f"Origin and destination cannot be the same: {from_city}"
        )

    all_flights = _load_flights()

    # Filter by route (case-insensitive match)
    results = [
        f for f in all_flights
        if f["from"].upper() == from_city
        and f["to"].upper() == to_city
    ]

    # Ensure price is numeric
    for f in results:
        f["price"] = float(f["price"])

    return results
