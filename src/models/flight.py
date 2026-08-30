"""Flight data model."""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Flight:
    """Represents a single flight option."""

    flight_id: str
    airline: str
    from_city: str      # IATA code e.g. "DEL"
    to_city: str        # IATA code e.g. "BOM"
    departure: str      # "HH:MM"
    arrival: str        # "HH:MM"
    duration_minutes: int
    stops: int
    price: float

    # Optional scoring field (set by agent during evaluation)
    _score: float = 0.0

    def to_dict(self) -> dict:
        """Convert to plain dict for serialization (excludes internal score)."""
        return {
            "flight_id": self.flight_id,
            "airline": self.airline,
            "from": self.from_city,
            "to": self.to_city,
            "departure": self.departure,
            "arrival": self.arrival,
            "duration_minutes": self.duration_minutes,
            "stops": self.stops,
            "price": self.price,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Flight":
        """Create a Flight from a dictionary (handles 'from'/'to' key names)."""
        return cls(
            flight_id=d["flight_id"],
            airline=d["airline"],
            from_city=d.get("from", d.get("from_city", "")),
            to_city=d.get("to", d.get("to_city", "")),
            departure=d["departure"],
            arrival=d["arrival"],
            duration_minutes=int(d["duration_minutes"]),
            stops=int(d["stops"]),
            price=float(d["price"]),
        )

    @property
    def is_nonstop(self) -> bool:
        return self.stops == 0

    def __repr__(self) -> str:
        stop_label = "non-stop" if self.is_nonstop else f"{self.stops} stop(s)"
        return (
            f"{self.flight_id} | {self.airline} | "
            f"{self.from_city}→{self.to_city} | "
            f"{self.departure}-{self.arrival} | "
            f"₹{self.price:,.0f} | {stop_label}"
        )
