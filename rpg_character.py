"""Façade publique de l'application Personnages JDR.

L'implémentation NiceGUI principale est isolée dans ``rpg_character_ui.py``.
Cette façade conserve le point d'import historique ``rpg_character`` afin de
ne pas modifier les autres applications ni les appels existants.

Phase 2 de modularisation : le panneau Sauvegardes est fourni par
``rpg_character_saves.py`` et raccordé ici sans changer l'API publique.
"""
from __future__ import annotations

import rpg_character_ui as _impl
from rpg_character_saves import build_saves_panel


def _saves_panel(user_id, character):
    """Raccorde le panneau Sauvegardes modularisé aux dépendances existantes."""
    return build_saves_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_saves=_impl.list_rpg_saves,
        save_definitions=_impl.SAVE_DEFINITIONS,
        ability_labels=_impl.ABILITY_LABELS,
        ability_modifier_for_character=_impl.ability_modifier_for_character,
        save_total=_impl.save_total,
        format_modifier=_impl.format_modifier,
        as_number=_impl._as_number,
        update_rpg_saves=_impl.update_rpg_saves,
        notify_error=_impl._safe_notify_error,
        calculation_rules_dialog=_impl._calculation_rules_dialog,
    )


# rpg_character_panel cherche _saves_panel dans le dictionnaire global du
# module rpg_character_ui au moment où le panneau est construit.
_impl._saves_panel = _saves_panel

rpg_character_panel = _impl.rpg_character_panel

__all__ = ["rpg_character_panel"]


def __getattr__(name):
    """Préserve l'accès aux attributs historiques pendant la modularisation."""
    return getattr(_impl, name)


def __dir__():
    """Expose aussi les attributs de l'implémentation aux outils d'inspection."""
    return sorted(set(globals()) | set(dir(_impl)))
