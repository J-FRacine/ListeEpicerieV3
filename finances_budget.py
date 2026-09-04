"""Contrat minimal du panneau Budget, sans dépendance d'interface."""
from dataclasses import dataclass
from typing import Callable


@dataclass
class BudgetPanelHandle:
    """Point de liaison utilisé par le parent pour actualiser Budget."""

    on_refresh: Callable[[], None]

    def refresh(self) -> None:
        self.on_refresh()
