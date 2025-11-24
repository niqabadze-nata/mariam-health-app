from dataclasses import dataclass
from datetime import datetime


@dataclass
class Entry:
    ts: datetime
    food: str
    sugar_g: float
    water_cups: float
    insulin_units: float
    time_eaten: datetime | None = None

    def as_row(self):
        return (
            self.ts.isoformat(),
            self.food,
            self.sugar_g,
            self.water_cups,
            self.insulin_units,
            self.time_eaten.isoformat() if self.time_eaten else None,
        )
