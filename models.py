from dataclasses import dataclass
from datetime import datetime


@dataclass
class Entry:
    ts: datetime
    food: str
    sugar_g: float
    water_cups: float
    insulin_units: float

    def as_row(self):
        return (
            self.ts.isoformat(),
            self.food,
            self.sugar_g,
            self.water_cups,
            self.insulin_units,
        )
