from dataclasses import dataclass, field
from typing import Dict, List
from .positions import Position

@dataclass
class Portfolio:
    positions: List[Position] = field(default_factory=list)

    def add(self, position: Position):
        self.positions.append(position)

    def total_greeks(self, greeks_by_instrument: Dict[str, Dict[str, float]]):
        totals = {}

        for pos in self.positions:
            if pos.instrument_id not in greeks_by_instrument:
                continue
            
            for greek_name, value in greeks_by_instrument[pos.instrument_id].items():
                totals[greek_name] = totals.get(greek_name, 0) + value * pos.quantity
        
        return totals
    def total_delta(self, greeks_by_instrument):
        """Convenience: return portfolio delta only."""
        totals = self.total_greeks(greeks_by_instrument)
        return totals.get("delta", 0.0)
