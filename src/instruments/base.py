from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Instrument(ABC):
    id: str
    currency: str

    @abstractmethod
    def describe(self) -> Dict[str, Any]:
        ...
