"""État temporaire et effets de Combat rapide — JDR V1.12.0.

L'état reste en mémoire serveur par utilisateur/personnage afin qu'une navigation
hors de la fenêtre Combat rapide ne fasse pas disparaître le combat en cours.
Aucune donnée temporaire n'est écrite dans la fiche permanente.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from itertools import count
from typing import Any, Mapping


EFFECT_TARGET_LABELS = {
    "note": "État / note seulement",
    "attack": "Attaque",
    "damage": "Dégâts / Damage",
    "ac": "CA totale",
    "initiative": "Initiative",
    "cmb": "BMO / CMB",
    "cmd": "DMD / CMD",
    "all_saves": "Tous les jets de sauvegarde",
    "fortitude": "Vigueur",
    "reflex": "Réflexes",
    "will": "Volonté",
}

_STATE: dict[tuple[int, int], dict[str, Any]] = {}
_IDS = count(1)


def _key(user_id: Any, character_id: Any) -> tuple[int, int]:
    return int(user_id), int(character_id)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _default_state(character: Mapping[str, Any] | None = None) -> dict[str, Any]:
    character = dict(character or {})
    return {
        "round": 1,
        "effects": [],
        "journal": [],
        "selected_attack_id": None,
        "temporary_attack_bonus": 0,
        "tactics": "",
        "current_hp": _int(character.get("current_hp")),
        "nonlethal_damage": max(0, _int(character.get("nonlethal_damage"))),
        "active_feat_ids": [],
    }


def combat_state(user_id: Any, character_id: Any, *, character=None) -> dict[str, Any]:
    """Retourne une copie de l'état courant, créé au besoin."""
    key = _key(user_id, character_id)
    if key not in _STATE:
        _STATE[key] = _default_state(character)
    return deepcopy(_STATE[key])


def update_combat_state(user_id: Any, character_id: Any, **changes: Any) -> dict[str, Any]:
    key = _key(user_id, character_id)
    if key not in _STATE:
        _STATE[key] = _default_state()
    state = _STATE[key]
    for field, value in changes.items():
        if field in {"effects", "journal"}:
            state[field] = deepcopy(value)
        elif field == "active_feat_ids":
            state[field] = sorted({int(item) for item in (value or [])})
        elif field == "round":
            state[field] = max(1, _int(value, 1))
        elif field == "nonlethal_damage":
            state[field] = max(0, _int(value))
        else:
            state[field] = value
    return deepcopy(state)


def clear_combat_state(user_id: Any, character_id: Any) -> None:
    _STATE.pop(_key(user_id, character_id), None)


def _journal(state: dict[str, Any], message: str) -> None:
    state.setdefault("journal", []).append({
        "at": datetime.now().strftime("%H:%M"),
        "round": max(1, _int(state.get("round"), 1)),
        "message": str(message),
    })
    state["journal"] = state["journal"][-200:]


def add_journal_entry(user_id: Any, character_id: Any, message: str) -> dict[str, Any]:
    key = _key(user_id, character_id)
    if key not in _STATE:
        _STATE[key] = _default_state()
    _journal(_STATE[key], message)
    return deepcopy(_STATE[key])


def add_effect(
    user_id: Any,
    character_id: Any,
    *,
    name: str,
    target: str = "note",
    modifier: Any = 0,
    rounds: Any = 0,
) -> dict[str, Any]:
    key = _key(user_id, character_id)
    if key not in _STATE:
        _STATE[key] = _default_state()
    state = _STATE[key]
    target = str(target or "note")
    if target not in EFFECT_TARGET_LABELS:
        target = "note"
    label = str(name or "").strip() or "Effet temporaire"
    duration = max(0, _int(rounds))
    effect = {
        "id": next(_IDS),
        "name": label,
        "target": target,
        "modifier": _int(modifier),
        "remaining_rounds": duration or None,
    }
    state.setdefault("effects", []).append(effect)
    suffix = ""
    if target != "note" and effect["modifier"]:
        suffix += f" ({effect['modifier']:+d} {EFFECT_TARGET_LABELS[target]})"
    if duration:
        suffix += f" — {duration} round(s)"
    _journal(state, f"Effet ajouté : {label}{suffix}")
    return deepcopy(state)


def remove_effect(user_id: Any, character_id: Any, effect_id: Any) -> dict[str, Any]:
    key = _key(user_id, character_id)
    if key not in _STATE:
        _STATE[key] = _default_state()
    state = _STATE[key]
    wanted = _int(effect_id, -1)
    removed = next((row for row in state.get("effects", []) if _int(row.get("id"), -2) == wanted), None)
    state["effects"] = [row for row in state.get("effects", []) if _int(row.get("id"), -2) != wanted]
    if removed:
        _journal(state, f"Effet retiré : {removed.get('name') or 'Effet'}")
    return deepcopy(state)


def advance_round(user_id: Any, character_id: Any) -> dict[str, Any]:
    key = _key(user_id, character_id)
    if key not in _STATE:
        _STATE[key] = _default_state()
    state = _STATE[key]
    state["round"] = max(1, _int(state.get("round"), 1)) + 1
    kept = []
    expired = []
    for raw in state.get("effects", []):
        row = dict(raw)
        remaining = row.get("remaining_rounds")
        if remaining in (None, "", 0):
            kept.append(row)
            continue
        remaining = _int(remaining) - 1
        if remaining <= 0:
            expired.append(row)
        else:
            row["remaining_rounds"] = remaining
            kept.append(row)
    state["effects"] = kept
    _journal(state, f"Début du round {state['round']}.")
    for row in expired:
        _journal(state, f"Effet expiré : {row.get('name') or 'Effet'}")
    return deepcopy(state)


def effect_modifiers(state: Mapping[str, Any] | None) -> dict[str, Any]:
    """Additionne uniquement les modificateurs structurés actifs."""
    result = {
        "attack_modifier": 0,
        "damage_modifier": 0,
        "ac_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_modifiers": {"all": 0, "fortitude": 0, "reflex": 0, "will": 0},
    }
    for row in (state or {}).get("effects", []) or []:
        target = str(row.get("target") or "note")
        modifier = _int(row.get("modifier"))
        if target == "attack":
            result["attack_modifier"] += modifier
        elif target == "damage":
            result["damage_modifier"] += modifier
        elif target == "ac":
            result["ac_modifier"] += modifier
        elif target == "initiative":
            result["initiative_modifier"] += modifier
        elif target == "cmb":
            result["cmb_modifier"] += modifier
        elif target == "cmd":
            result["cmd_modifier"] += modifier
        elif target == "all_saves":
            result["save_modifiers"]["all"] += modifier
        elif target in {"fortitude", "reflex", "will"}:
            result["save_modifiers"][target] += modifier
    return result
