from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

MONTH_NAMES_FR = (
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
)


def month_start(value: date | None = None) -> date:
    """Normalise une date au premier jour de son mois."""
    value = value or date.today()
    return date(value.year, value.month, 1)


def month_label(value: date) -> str:
    """Libellé français stable utilisé par tous les sélecteurs mensuels."""
    value = month_start(value)
    return f"{MONTH_NAMES_FR[value.month - 1]} {value.year}"


def shift_month(value: date, amount: int) -> date:
    """Décale un mois sans dépendre du nombre de jours du mois courant."""
    value = month_start(value)
    absolute = value.year * 12 + (value.month - 1) + int(amount)
    year, month_index = divmod(absolute, 12)
    return date(year, month_index + 1, 1)


@dataclass
class MonthCursor:
    """État mensuel minimal partagé par une vue NiceGUI.

    Remplace les dictionnaires mutables ad hoc utilisés auparavant. La classe
    garde la mutation explicite tout en centralisant la normalisation des mois.
    """

    value: date = field(default_factory=month_start)

    def set(self, value: date) -> date:
        self.value = month_start(value)
        return self.value

    def shift(self, amount: int) -> date:
        self.value = shift_month(self.value, amount)
        return self.value

    def reset(self) -> date:
        self.value = month_start()
        return self.value

    @property
    def label(self) -> str:
        return month_label(self.value)
