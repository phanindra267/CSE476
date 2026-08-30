"""
Tool 2: compare_price(options, budget=None)

Receives flight search results and performs price comparison:
  - Sorts by price
  - Finds cheapest and second-best option
  - Calculates price differences
  - Identifies options under budget
  - Separates non-stop vs connecting flights
"""

from typing import Any, Dict, List, Optional


def compare_price(
    options: List[Dict[str, Any]],
    budget: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compare flight options by price and categorize them.

    Parameters
    ----------
    options : list[dict]
        List of flight option dictionaries from search_flights.
    budget : float, optional
        User's maximum budget. If provided, flights are also split
        into under_budget / over_budget lists.

    Returns
    -------
    dict
        Structured comparison with cheapest, second_best, under_budget,
        nonstop_under_budget, price_difference, and summary.

    Raises
    ------
    TypeError
        If options is not a list.
    """
    if not isinstance(options, list):
        raise TypeError("options must be a list of flight dictionaries")

    if not options:
        return {
            "cheapest": None,
            "second_best": None,
            "under_budget": [],
            "over_budget": [],
            "nonstop_under_budget": [],
            "price_difference": None,
            "summary": "No options available to compare.",
        }

    # Sort all options by price ascending
    sorted_options = sorted(options, key=lambda x: float(x["price"]))

    cheapest = sorted_options[0]
    second_best = sorted_options[1] if len(sorted_options) > 1 else None
    price_diff = (
        float(second_best["price"]) - float(cheapest["price"])
        if second_best
        else None
    )

    # Budget-based categorization
    under_budget: List[Dict[str, Any]] = []
    over_budget: List[Dict[str, Any]] = []
    nonstop_under_budget: List[Dict[str, Any]] = []

    if budget is not None:
        for f in sorted_options:
            if float(f["price"]) <= budget:
                under_budget.append(f)
                if int(f.get("stops", 0)) == 0:
                    nonstop_under_budget.append(f)
            else:
                over_budget.append(f)
    else:
        under_budget = list(sorted_options)
        nonstop_under_budget = [
            f for f in sorted_options if int(f.get("stops", 0)) == 0
        ]

    # Build summary string
    parts = [
        f"Cheapest: {cheapest['flight_id']} ({cheapest['airline']}) "
        f"at ₹{float(cheapest['price']):,.0f}"
    ]
    if second_best:
        parts.append(
            f"Second-best: {second_best['flight_id']} ({second_best['airline']}) "
            f"at ₹{float(second_best['price']):,.0f} "
            f"(₹{price_diff:,.0f} more)"
        )
    if budget is not None:
        parts.append(
            f"Under budget (₹{budget:,.0f}): {len(under_budget)} option(s), "
            f"of which {len(nonstop_under_budget)} are non-stop"
        )

    return {
        "cheapest": cheapest,
        "second_best": second_best,
        "under_budget": under_budget,
        "over_budget": over_budget,
        "nonstop_under_budget": nonstop_under_budget,
        "price_difference": price_diff,
        "summary": ". ".join(parts) + ".",
    }
