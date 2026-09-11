"""Façade publique de l'application Personnages JDR.

L'implémentation NiceGUI principale est isolée dans ``rpg_character_ui.py``.
Cette façade conserve le point d'import historique ``rpg_character`` afin de
ne pas modifier les autres applications ni les appels existants.
"""
from __future__ import annotations

import rpg_character_ui as _impl

rpg_character_panel = _impl.rpg_character_panel

__all__ = ["rpg_character_panel"]


def __getattr__(name):
    """Préserve l'accès aux attributs historiques pendant la modularisation."""
    return getattr(_impl, name)


def __dir__():
    """Expose aussi les attributs de l'implémentation aux outils d'inspection."""
    return sorted(set(globals()) | set(dir(_impl)))
