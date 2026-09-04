"""Contrat du panneau Compte, indépendant de NiceGUI et des données."""
from dataclasses import dataclass
from typing import Callable


@dataclass
class AccountPanelHandle:
    """Liaison minimale entre Finances et le panneau Compte.

    Le panneau fournit des callbacks sans argument, idéalement des lambdas
    résolvant leurs fonctions cibles à l'appel. Ils ne sont pas exécutés à la
    construction et peuvent être remplacés ensuite.

    Le parent appelle reload_options() puis refresh() lors d'une actualisation
    globale. La sélection et les widgets restent sous la responsabilité du
    panneau. reload_options() ne déclenche pas explicitement le rendu.
    """

    on_refresh: Callable[[], None]
    on_reload_options: Callable[[], None]

    def refresh(self) -> None:
        self.on_refresh()

    def reload_options(self) -> None:
        self.on_reload_options()
