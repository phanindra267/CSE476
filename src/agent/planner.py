"""
Planner — extracts user intent from natural language.

Uses regex-based NLP to parse:
  - origin / destination cities
  - budget constraints
  - non-stop preference
  - time-of-day preference
"""

import re
from typing import Any, Dict, Optional


# Airport name → IATA code aliases
AIRPORT_ALIASES: Dict[str, str] = {
    "delhi": "DEL", "new delhi": "DEL", "del": "DEL",
    "mumbai": "BOM", "bombay": "BOM", "bom": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR", "blr": "BLR",
    "hyderabad": "HYD", "hyd": "HYD",
    "chennai": "MAA", "madras": "MAA", "maa": "MAA",
    "kolkata": "CCU", "calcutta": "CCU", "ccu": "CCU",
    "goa": "GOI", "goi": "GOI",
    "jaipur": "JAI", "jai": "JAI",
    "pune": "PNQ", "pnq": "PNQ",
}


def _extract_airport(text: str) -> Optional[str]:
    """Find the first airport name/code in a text fragment."""
    text_lower = text.lower().strip()
    # Check aliases (longest-first to avoid partial matches)
    for alias in sorted(AIRPORT_ALIASES, key=len, reverse=True):
        if alias in text_lower:
            return AIRPORT_ALIASES[alias]
    # Fallback: bare 3-letter uppercase code
    match = re.search(r"\b([A-Z]{3})\b", text.upper())
    if match:
        return match.group(1)
    return None


def parse_user_request(text: str) -> Dict[str, Any]:
    """
    Parse a natural-language flight request into structured intent.

    Returns
    -------
    dict with optional keys:
      origin, destination, budget, non_stop, preferred_time
    """
    req = text.lower()
    intent: Dict[str, Any] = {}

    # ── Budget ────────────────────────────────────────────────────────────────
    budget_match = re.search(
        r"(?:under|budget\s*(?:is|of|=|:)?\s*|max(?:imum)?\s+"
        r"(?:budget\s+(?:is|of)?\s*)?|within\s+(?:a\s+)?"
        r"(?:budget\s+of\s+)?|below|up\s+to|less\s+than|"
        r"cheaper\s+than|inr|rs\.?|₹)\s*"
        r"(?:rs\.?|₹|inr)?\s*(\d[\d,]*)",
        req,
    )
    if budget_match:
        val = float(budget_match.group(1).replace(",", ""))
        if 100 <= val <= 500_000:
            intent["budget"] = val

    # ── Time preference ───────────────────────────────────────────────────────
    if any(w in req for w in ["morning", "early morning", "am flight"]):
        intent["preferred_time"] = "morning"
    elif any(w in req for w in ["afternoon", "midday", "noon"]):
        intent["preferred_time"] = "afternoon"
    elif any(w in req for w in ["evening", "night", "late"]):
        intent["preferred_time"] = "evening"

    # ── Non-stop preference ───────────────────────────────────────────────────
    if any(w in req for w in [
        "non-stop", "non stop", "nonstop", "direct", "no stop", "no layover"
    ]):
        intent["non_stop"] = True

    # ── Route extraction ──────────────────────────────────────────────────────
    # Try multiple patterns in order of specificity
    origin_code = None
    dest_code = None

    # Pattern 1: "from X to Y"
    route_match = re.search(
        r"from\s+([\w\s]+?)\s+to\s+([\w\s]+?)"
        r"(?:\s+under|\s+below|\s+with|\s+budget|\s+max|\s+prefer|$|\.|,)",
        req,
    )
    # Pattern 2: "fly X to Y" / "fly from X to Y"
    if not route_match:
        route_match = re.search(
            r"fly\s+(?:from\s+)?([\w\s]+?)\s+to\s+([\w\s]+?)"
            r"(?:\s+under|\s+below|\s+with|\s+budget|\s+max|\s+prefer|$|\.|,)",
            req,
        )
    # Pattern 3: "<City> to <City>" (only if both sides resolve to airports)
    if not route_match:
        route_match = re.search(
            r"([\w\s]+?)\s+to\s+([\w\s]+?)"
            r"(?:\s+under|\s+below|\s+with|\s+budget|\s+max|\s+prefer|$|\.|,)",
            req,
        )

    if route_match:
        from_text = route_match.group(1).strip()
        to_text = route_match.group(2).strip()
        origin_code = _extract_airport(from_text)
        dest_code = _extract_airport(to_text)

    # Fallback: try individual "from X" / "to Y" patterns
    if not origin_code:
        from_match = re.search(r"from\s+([\w\s]+?)(?:\s+to\s|\s|$|,|\.)", req)
        if from_match:
            origin_code = _extract_airport(from_match.group(1))
    if not dest_code:
        to_match = re.search(r"to\s+([\w\s]+?)(?:\s+under|\s+below|\s+prefer|\s|$|,|\.)", req)
        if to_match:
            dest_code = _extract_airport(to_match.group(1))

    if origin_code:
        intent["origin"] = origin_code
    if dest_code:
        intent["destination"] = dest_code

    return intent
