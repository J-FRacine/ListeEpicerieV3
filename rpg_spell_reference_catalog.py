"""Référence structurée des sorts Pathfinder 1e — JDR V1.12.0.

La page de référence tente de charger les données ouvertes du Core Rulebook
(PFSRD/OGL) depuis Moddable Games. En cas d'indisponibilité réseau, elle se
replie sur le catalogue local déjà livré avec JF Apps.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from urllib.request import Request, urlopen


REFERENCE_URL = "https://rules.moddable.games/games/pathfinder-1e/data/spells.json"
REFERENCE_ATTRIBUTION = (
    "Pathfinder Roleplaying Game Core Rulebook (Paizo Publishing, 2009), "
    "Open Game License 1.0a; données structurées PSRD-Data via Moddable Games."
)


def _slug(value):
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")
    return text or "spell"


def _effect_text(value):
    if isinstance(value, dict):
        return " • ".join(f"{key}: {item}" for key, item in value.items() if item)
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("type") or "Effet"
                text = item.get("text") or item.get("value") or ""
                if text:
                    parts.append(f"{name}: {text}")
            elif item:
                parts.append(str(item))
        return " • ".join(parts)
    return str(value or "")


def _cleric_level(raw):
    levels = raw.get("levels") or []
    found = []
    for row in levels:
        if str(row.get("class") or "").strip().casefold() == "cleric":
            try:
                found.append(int(row.get("level")))
            except (TypeError, ValueError):
                pass
    return min(found) if found else None


def _normalize_remote(raw):
    level = _cleric_level(raw)
    if level is None:
        return None
    return {
        "key": f"core_{_slug(raw.get('name'))}",
        "name": str(raw.get("name") or "Sort").strip(),
        "spell_level": level,
        "school": str(raw.get("school") or "").title(),
        "casting_time": str(raw.get("casting_time") or ""),
        "components_text": str(raw.get("component_text") or ""),
        "range_text": str(raw.get("range") or ""),
        "target_text": _effect_text(raw.get("effects")),
        "duration_text": str(raw.get("duration") or ""),
        "saving_throw_text": str(raw.get("saving_throw") or ""),
        "spell_resistance_text": str(raw.get("spell_resistance") or ""),
        "summary": str(raw.get("short_description") or raw.get("description") or ""),
        "full_description": str(raw.get("description") or raw.get("short_description") or ""),
        "source_text": str(raw.get("source") or "Core Rulebook"),
        "slot_kind": "normal",
        "domain_source": None,
        "reference_source": "remote",
    }


@lru_cache(maxsize=1)
def remote_core_cleric_spells():
    request = Request(
        REFERENCE_URL,
        headers={"User-Agent": "JF-Apps-Pathfinder-Reference/1.12"},
    )
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = []
    for raw in payload if isinstance(payload, list) else []:
        normalized = _normalize_remote(raw)
        if normalized:
            rows.append(normalized)
    rows.sort(key=lambda row: (row["spell_level"], row["name"].casefold()))
    return tuple(rows)


def _fallback_row(row):
    return {
        "key": str(row.get("key") or f"local_{_slug(row.get('name'))}"),
        "name": str(row.get("name") or "Sort"),
        "spell_level": int(row.get("spell_level") or 0),
        "school": str(row.get("school") or ""),
        "casting_time": str(row.get("casting_time") or ""),
        "components_text": str(row.get("components_text") or row.get("components") or ""),
        "range_text": str(row.get("range_text") or ""),
        "target_text": str(row.get("target_text") or ""),
        "duration_text": str(row.get("duration_text") or ""),
        "saving_throw_text": str(row.get("saving_throw_text") or ""),
        "spell_resistance_text": str(row.get("spell_resistance_text") or ""),
        "summary": str(row.get("summary") or ""),
        "full_description": str(row.get("full_description") or row.get("summary") or ""),
        "source_text": str(row.get("source_text") or "Core Rulebook"),
        "slot_kind": str(row.get("slot_kind") or "normal"),
        "domain_source": row.get("domain_source"),
        "reference_source": "local",
    }


def cleric_spell_reference_rows(*, max_spell_level=9, local_catalog=()):
    """Retourne les sorts de Clerc accessibles, avec repli local fiable."""
    maximum = int(max_spell_level)
    local_rows = [_fallback_row(row) for row in (local_catalog or ())]
    local_by_name = {row["name"].casefold(): row for row in local_rows}
    try:
        remote = [dict(row) for row in remote_core_cleric_spells()]
    except Exception:
        remote = []

    if not remote:
        rows = [row for row in local_rows if row["spell_level"] <= maximum]
    else:
        rows = []
        seen = set()
        for row in remote:
            if row["spell_level"] > maximum:
                continue
            local = local_by_name.get(row["name"].casefold())
            if local:
                # Le résumé français local reste prioritaire, les statistiques
                # détaillées de la référence ouverte complètent la fiche.
                row["summary"] = local.get("summary") or row["summary"]
                row["key"] = local.get("key") or row["key"]
            rows.append(row)
            seen.add(row["name"].casefold())
        # Conserver les sorts de domaine/locaux absents du jeu Core distant.
        for row in local_rows:
            if row["spell_level"] <= maximum and row["name"].casefold() not in seen:
                rows.append(row)

    rows.sort(
        key=lambda row: (
            int(row.get("spell_level") or 0),
            1 if row.get("slot_kind") == "domain" else 0,
            str(row.get("name") or "").casefold(),
        )
    )
    return rows
