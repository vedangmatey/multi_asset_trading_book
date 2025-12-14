from dataclasses import dataclass

@dataclass
class Position:
    instrument_id: str
    quantity: float  # + long, - short

    def value(self, price: float) -> float:
        return self.quantity * price
