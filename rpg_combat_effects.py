"""Règles des effets temporaires de Combat rapide."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


EFFECT_TARGETS = {
    "state": "État / note seulement",
    "attack": "Attaque",
    "ac": "CA totale",
    "initiative": "Initiative",
    "cmb": "BMO / CMB",
    "cmd": "DMD / CMD",
    "save_all": "Tous les jets de sauvegarde",
    "fortitude": "Vigueur",
    "reflex": "Réflexes",
    "will": "Volonté",
}


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_effect(
    *,
    effect_id: int,
    name: Any,
    target: Any = "state",
    modifier: Any = 0,
    rounds: Any = 0,
    note: Any = "",
) -> dict[str, Any]:
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Donnez un nom à l’effet.")

    clean_target = str(target or "state").strip()
    if clean_target not in EFFECT_TARGETS:
        clean_target = "state"

    clean_modifier = _as_int(modifier)
    if clean_target == "state":
        clean_modifier = 0

    return {
        "id": int(effect_id),
        "name": clean_name[:120],
        "target": clean_target,
        "modifier": clean_modifier,
        "rounds_remaining": max(0, _as_int(rounds)),
        "note": str(note or "").strip()[:500],
    }


def effect_duration_text(effect: Mapping[str, Any]) -> str:
    rounds = max(0, _as_int(effect.get("rounds_remaining")))
    if rounds == 0:
        return "Jusqu’à la fin du combat"
    if rounds == 1:
        return "1 round restant"
    return f"{rounds} rounds restants"


def summarize_effect_modifiers(
    effects: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    totals = {
        "attack": 0,
        "ac": 0,
        "initiative": 0,
        "cmb": 0,
        "cmd": 0,
        "save_all": 0,
        "fortitude": 0,
        "reflex": 0,
        "will": 0,
    }
    for effect in effects or ():
        target = str(effect.get("target") or "state")
        if target in totals:
            totals[target] += _as_int(effect.get("modifier"))
    return totals


def advance_effect_round(
    effects: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Avance un round; 0 round signifie jusqu'à la fin du combat."""
    active: list[dict[str, Any]] = []
    expired: list[dict[str, Any]] = []

    for raw in effects or ():
        effect = dict(raw)
        remaining = max(0, _as_int(effect.get("rounds_remaining")))
        if remaining == 0:
            active.append(effect)
            continue

        remaining -= 1
        effect["rounds_remaining"] = remaining
        if remaining <= 0:
            expired.append(effect)
        else:
            active.append(effect)

    return active, expired
