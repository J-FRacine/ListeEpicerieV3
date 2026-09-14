"""Calculs purs liés aux dons utilisés dans Combat rapide."""
from __future__ import annotations

from typing import Any, Iterable, Mapping


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _id_set(values: Iterable[Any]) -> set[int]:
    result = set()
    for value in values or ():
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result


def collect_feat_combat_effects(
    feats,
    *,
    active_feat_ids=(),
    selected_attack_id=None,
):
    """Retourne les modificateurs des dons applicables à ce combat.

    - Les dons passifs sont toujours actifs.
    - Les dons activables ne sont actifs que lorsque leur id est fourni.
    - Les dons informatifs ne modifient jamais les chiffres.
    - Un bonus d'attaque lié à une attaque ne s'applique qu'à cette attaque.
    """
    active_ids = _id_set(active_feat_ids)
    try:
        selected_id = int(selected_attack_id)
    except (TypeError, ValueError):
        selected_id = None

    result = {
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_modifiers": {},
        "damage_notes": [],
        "applied_feats": [],
    }

    for feat in feats or ():
        kind = str(feat.get("feat_kind") or "info").strip().lower()
        try:
            feat_id = int(feat.get("id"))
        except (TypeError, ValueError):
            feat_id = None

        is_active = (
            kind == "passive"
            or (kind == "active" and feat_id in active_ids)
        )
        if not is_active:
            continue

        result["applied_feats"].append(
            {
                "id": feat_id,
                "name": str(feat.get("feat_name") or "Don"),
                "kind": kind,
            }
        )

        result["initiative_modifier"] += _as_int(
            feat.get("initiative_modifier")
        )
        result["cmb_modifier"] += _as_int(
            feat.get("cmb_modifier")
        )
        result["cmd_modifier"] += _as_int(
            feat.get("cmd_modifier")
        )

        save_modifier = _as_int(feat.get("save_modifier"))
        save_key = str(feat.get("save_key") or "").strip().lower()
        if save_modifier and save_key:
            if save_key == "all":
                result["save_modifiers"]["all"] = (
                    result["save_modifiers"].get("all", 0)
                    + save_modifier
                )
            else:
                result["save_modifiers"][save_key] = (
                    result["save_modifiers"].get(save_key, 0)
                    + save_modifier
                )

        linked_attack = feat.get("linked_attack_id")
        if linked_attack in (None, ""):
            attack_matches = True
        else:
            try:
                attack_matches = (
                    selected_id is not None
                    and int(linked_attack) == selected_id
                )
            except (TypeError, ValueError):
                attack_matches = False

        if attack_matches:
            result["attack_modifier"] += _as_int(
                feat.get("attack_modifier")
            )
            damage_note = str(
                feat.get("damage_note") or ""
            ).strip()
            if damage_note:
                result["damage_notes"].append(damage_note)

    return result


def feat_save_modifier(effects: Mapping[str, Any], save_key: str) -> int:
    modifiers = effects.get("save_modifiers") or {}
    return _as_int(modifiers.get("all")) + _as_int(
        modifiers.get(save_key)
    )
