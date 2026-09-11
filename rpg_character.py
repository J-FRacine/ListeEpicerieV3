"""Façade publique de l'application Personnages JDR.

L'implémentation NiceGUI principale est isolée dans ``rpg_character_ui.py``.
Cette façade conserve le point d'import historique ``rpg_character`` afin de
ne pas modifier les autres applications ni les appels existants.

Modularisation :
- Sauvegardes : ``rpg_character_saves.py``
- Progression : ``rpg_character_progression.py``
"""
from __future__ import annotations

import rpg_character_ui as _impl
from rpg_character_progression import build_progression_panel
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


def _progression_panel(user_id, character):
    """Raccorde le panneau Progression modularisé aux dépendances existantes."""
    return build_progression_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_skills=_impl.list_rpg_skills,
        list_rpg_level_history=_impl.list_rpg_level_history,
        format_modifier=_impl.format_modifier,
        format_number=_impl.format_number,
        ability_labels=_impl.ABILITY_LABELS,
        ability_long_labels=_impl.ABILITY_LONG_LABELS,
        skill_display_name=_impl._skill_display_name,
        apply_rpg_level_up=_impl.apply_rpg_level_up,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


# Les fonctions du module rpg_character_ui sont résolues par son dictionnaire
# global au moment de l'exécution. On remplace donc uniquement les panneaux
# déjà extraits, sans modifier le gros fichier pendant cette phase.
_impl._saves_panel = _saves_panel
_impl._progression_panel = _progression_panel

rpg_character_panel = _impl.rpg_character_panel

__all__ = ["rpg_character_panel"]


def __getattr__(name):
    """Préserve l'accès aux attributs historiques pendant la modularisation."""
    return getattr(_impl, name)


def __dir__():
    """Expose aussi les attributs de l'implémentation aux outils d'inspection."""
    return sorted(set(globals()) | set(dir(_impl)))
