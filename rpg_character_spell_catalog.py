"""Catalogue initial des sorts de Clerc — Phase 15A.

Le catalogue volontairement compact couvre les sorts courants du Core Rulebook
jusqu'au niveau 4 ainsi que les listes complètes des domaines War et Sun. Un
sort personnalisé peut toujours être ajouté depuis l'interface.
"""
from __future__ import annotations


def _spell(key, name, level, school, summary, *, range_text="", source="Core Rulebook"):
    return {
        "key": key,
        "name": name,
        "spell_level": int(level),
        "school": school,
        "summary": summary,
        "range_text": range_text,
        "source_text": source,
        "slot_kind": "normal",
        "domain_source": None,
    }


CLERIC_SPELLS = {
    row["key"]: row
    for row in [
        # Niveau 0
        _spell("create_water", "Create Water", 0, "Conjuration", "Crée une petite quantité d’eau potable."),
        _spell("detect_magic", "Detect Magic", 0, "Divination", "Détecte les auras magiques."),
        _spell("detect_poison", "Detect Poison", 0, "Divination", "Détermine si une créature ou un objet est empoisonné."),
        _spell("guidance", "Guidance", 0, "Divination", "Accorde +1 à un jet d’attaque, de sauvegarde ou de compétence."),
        _spell("light", "Light", 0, "Evocation", "Un objet émet une lumière normale."),
        _spell("mending", "Mending", 0, "Transmutation", "Répare de petits dommages sur un objet."),
        _spell("purify_food_drink", "Purify Food and Drink", 0, "Transmutation", "Rend nourriture et boisson propres à la consommation."),
        _spell("read_magic", "Read Magic", 0, "Divination", "Permet de lire des écritures magiques."),
        _spell("resistance", "Resistance", 0, "Abjuration", "Accorde +1 de résistance aux jets de sauvegarde."),
        _spell("stabilize", "Stabilize", 0, "Conjuration", "Stabilise une créature mourante."),
        _spell("virtue", "Virtue", 0, "Transmutation", "Accorde 1 point de vie temporaire."),
        # Niveau 1
        _spell("bane", "Bane", 1, "Enchantment", "Ennemis affectés : pénalité morale aux attaques et contre la peur."),
        _spell("bless", "Bless", 1, "Enchantment", "Alliés : bonus moral aux attaques et contre la peur."),
        _spell("command", "Command", 1, "Enchantment", "Donne un ordre bref à une créature."),
        _spell("comprehend_languages", "Comprehend Languages", 1, "Divination", "Comprend les langues parlées et écrites."),
        _spell("cure_light_wounds", "Cure Light Wounds", 1, "Conjuration", "Soigne 1d8 + 1/niveau de lanceur (max +5).", range_text="Touch"),
        _spell("detect_undead", "Detect Undead", 1, "Divination", "Détecte les auras de morts-vivants."),
        _spell("divine_favor", "Divine Favor", 1, "Evocation", "Bonus de chance aux attaques et dégâts selon le niveau de lanceur."),
        _spell("doom", "Doom", 1, "Necromancy", "Une cible devient shaken."),
        _spell("endure_elements", "Endure Elements", 1, "Abjuration", "Protège des températures extrêmes."),
        _spell("entropic_shield", "Entropic Shield", 1, "Abjuration", "Les attaques à distance ont une chance de rater le lanceur."),
        _spell("hide_from_undead", "Hide from Undead", 1, "Abjuration", "Rend les créatures difficiles à percevoir par les morts-vivants."),
        _spell("magic_stone", "Magic Stone", 1, "Transmutation", "Trois pierres deviennent des projectiles magiques."),
        _spell("magic_weapon", "Magic Weapon", 1, "Transmutation", "Une arme gagne un bonus d’altération de +1."),
        _spell("obscuring_mist", "Obscuring Mist", 1, "Conjuration", "Un brouillard limite la vision."),
        _spell("protection_from_chaos", "Protection from Chaos", 1, "Abjuration", "Protection défensive contre les créatures et effets chaotiques.", range_text="Touch"),
        _spell("protection_from_evil", "Protection from Evil", 1, "Abjuration", "Protection défensive contre les créatures et effets maléfiques.", range_text="Touch"),
        _spell("protection_from_good", "Protection from Good", 1, "Abjuration", "Protection défensive contre les créatures et effets bons.", range_text="Touch"),
        _spell("protection_from_law", "Protection from Law", 1, "Abjuration", "Protection défensive contre les créatures et effets loyaux.", range_text="Touch"),
        _spell("remove_fear", "Remove Fear", 1, "Abjuration", "Supprime ou réduit les effets de peur."),
        _spell("sanctuary", "Sanctuary", 1, "Abjuration", "Les adversaires doivent réussir un jet pour attaquer la cible."),
        _spell("shield_of_faith", "Shield of Faith", 1, "Abjuration", "Bonus de déflexion à la CA."),
        _spell("summon_monster_1", "Summon Monster I", 1, "Conjuration", "Convoque une créature extraplanaire de faible puissance."),
        # Niveau 2
        _spell("aid", "Aid", 2, "Enchantment", "Bonus contre la peur, aux attaques et points de vie temporaires."),
        _spell("align_weapon", "Align Weapon", 2, "Transmutation", "Donne un alignement à une arme pour surmonter certaines RD."),
        _spell("augury", "Augury", 2, "Divination", "Indique si une action proche sera favorable ou défavorable."),
        _spell("bears_endurance", "Bear's Endurance", 2, "Transmutation", "Accorde +4 d’amélioration en Constitution."),
        _spell("bulls_strength", "Bull's Strength", 2, "Transmutation", "Accorde +4 d’amélioration en Force."),
        _spell("calm_emotions", "Calm Emotions", 2, "Enchantment", "Apaise les émotions fortes dans une zone."),
        _spell("consecrate", "Consecrate", 2, "Evocation", "Renforce l’énergie positive dans une zone."),
        _spell("cure_moderate_wounds", "Cure Moderate Wounds", 2, "Conjuration", "Soigne 2d8 + 1/niveau de lanceur (max +10).", range_text="Touch"),
        _spell("delay_poison", "Delay Poison", 2, "Conjuration", "Suspend temporairement les effets d’un poison."),
        _spell("eagles_splendor", "Eagle's Splendor", 2, "Transmutation", "Accorde +4 d’amélioration en Charisme."),
        _spell("find_traps", "Find Traps", 2, "Divination", "Améliore la capacité à localiser les pièges."),
        _spell("gentle_repose", "Gentle Repose", 2, "Necromancy", "Préserve un corps et retarde sa décomposition."),
        _spell("hold_person", "Hold Person", 2, "Enchantment", "Paralyse temporairement un humanoïde."),
        _spell("lesser_restoration", "Lesser Restoration", 2, "Conjuration", "Dissipe fatigue ou certains dégâts/pénalités de caractéristique."),
        _spell("make_whole", "Make Whole", 2, "Transmutation", "Répare un objet endommagé."),
        _spell("owls_wisdom", "Owl's Wisdom", 2, "Transmutation", "Accorde +4 d’amélioration en Sagesse."),
        _spell("remove_paralysis", "Remove Paralysis", 2, "Conjuration", "Libère une ou plusieurs créatures de la paralysie."),
        _spell("resist_energy", "Resist Energy", 2, "Abjuration", "Accorde une résistance à un type d’énergie."),
        _spell("silence", "Silence", 2, "Illusion", "Supprime les sons dans une zone."),
        _spell("sound_burst", "Sound Burst", 2, "Evocation", "Dégâts soniques et risque d’étourdissement."),
        _spell("spiritual_weapon", "Spiritual Weapon", 2, "Evocation", "Une arme de force attaque à distance selon le lanceur."),
        _spell("status", "Status", 2, "Divination", "Permet de suivre l’état et la position relative d’alliés."),
        _spell("summon_monster_2", "Summon Monster II", 2, "Conjuration", "Convoque une créature extraplanaire."),
        _spell("zone_of_truth", "Zone of Truth", 2, "Enchantment", "Les créatures dans la zone ont de la difficulté à mentir."),
        # Niveau 3
        _spell("animate_dead", "Animate Dead", 3, "Necromancy", "Crée des squelettes ou zombies sous contrôle."),
        _spell("bestow_curse", "Bestow Curse", 3, "Necromancy", "Inflige une malédiction à une créature."),
        _spell("blindness_deafness", "Blindness/Deafness", 3, "Necromancy", "Rend une cible aveugle ou sourde."),
        _spell("create_food_water", "Create Food and Water", 3, "Conjuration", "Crée nourriture et eau pour plusieurs créatures."),
        _spell("cure_serious_wounds", "Cure Serious Wounds", 3, "Conjuration", "Soigne 3d8 + 1/niveau de lanceur (max +15).", range_text="Touch"),
        _spell("daylight", "Daylight", 3, "Evocation", "Crée une lumière vive semblable au jour."),
        _spell("dispel_magic", "Dispel Magic", 3, "Abjuration", "Met fin à un sort ou contre une magie active."),
        _spell("glyph_of_warding", "Glyph of Warding", 3, "Abjuration", "Inscrit un piège magique sur une surface ou un objet."),
        _spell("invisibility_purge", "Invisibility Purge", 3, "Evocation", "Supprime l’invisibilité dans une zone autour du lanceur."),
        _spell("locate_object", "Locate Object", 3, "Divination", "Localise un type d’objet ou un objet connu."),
        _spell("magic_vestment", "Magic Vestment", 3, "Transmutation", "Améliore l’armure ou le bouclier."),
        _spell("prayer", "Prayer", 3, "Enchantment", "Bonus aux alliés et pénalités aux ennemis dans une zone."),
        _spell("protection_from_energy", "Protection from Energy", 3, "Abjuration", "Absorbe un montant de dégâts d’un type d’énergie."),
        _spell("remove_blindness_deafness", "Remove Blindness/Deafness", 3, "Conjuration", "Guérit cécité ou surdité magique."),
        _spell("remove_curse", "Remove Curse", 3, "Abjuration", "Libère une créature ou un objet d’une malédiction."),
        _spell("remove_disease", "Remove Disease", 3, "Conjuration", "Guérit une maladie."),
        _spell("searing_light", "Searing Light", 3, "Evocation", "Rayon de lumière particulièrement efficace contre les morts-vivants."),
        _spell("speak_with_dead", "Speak with Dead", 3, "Necromancy", "Permet de poser des questions à un cadavre."),
        _spell("stone_shape", "Stone Shape", 3, "Transmutation", "Façonne une quantité limitée de pierre."),
        _spell("summon_monster_3", "Summon Monster III", 3, "Conjuration", "Convoque une créature extraplanaire."),
        _spell("water_breathing", "Water Breathing", 3, "Transmutation", "Permet de respirer sous l’eau."),
        _spell("water_walk", "Water Walk", 3, "Transmutation", "Permet de marcher sur les liquides."),
        # Niveau 4
        _spell("air_walk", "Air Walk", 4, "Transmutation", "Permet de marcher dans l’air comme sur un plan incliné."),
        _spell("cure_critical_wounds", "Cure Critical Wounds", 4, "Conjuration", "Soigne 4d8 + 1/niveau de lanceur (max +20).", range_text="Touch"),
        _spell("death_ward", "Death Ward", 4, "Necromancy", "Protège contre effets de mort, énergie négative et niveaux négatifs."),
        _spell("dimensional_anchor", "Dimensional Anchor", 4, "Abjuration", "Empêche les déplacements extradimensionnels de la cible."),
        _spell("discern_lies", "Discern Lies", 4, "Divination", "Détecte les mensonges délibérés."),
        _spell("dismissal", "Dismissal", 4, "Abjuration", "Renvoie une créature extraplanaire vers son plan."),
        _spell("divine_power", "Divine Power", 4, "Evocation", "Renforce fortement le Clerc au combat."),
        _spell("freedom_of_movement", "Freedom of Movement", 4, "Abjuration", "La cible se déplace normalement malgré plusieurs entraves."),
        _spell("greater_magic_weapon", "Magic Weapon, Greater", 4, "Transmutation", "Améliore une arme pour une longue durée."),
        _spell("neutralize_poison", "Neutralize Poison", 4, "Conjuration", "Détoxifie un poison ou protège temporairement d’un poison."),
        _spell("restoration", "Restoration", 4, "Conjuration", "Restaure niveaux négatifs et dégâts de caractéristique selon le cas."),
        _spell("sending", "Sending", 4, "Evocation", "Envoie un court message à grande distance."),
        _spell("spell_immunity", "Spell Immunity", 4, "Abjuration", "Protège contre certains sorts choisis."),
        _spell("summon_monster_4", "Summon Monster IV", 4, "Conjuration", "Convoque une créature extraplanaire plus puissante."),
        _spell("tongues", "Tongues", 4, "Divination", "Permet de parler et comprendre toutes les langues."),
    ]
}


# Détails courts utilisés par le lancement guidé. Ils complètent le résumé sans
# reproduire le texte intégral des sorts. Les entrées absentes restent affichées
# avec « À vérifier » plutôt que d'inventer une durée ou une cible.
CASTING_DETAILS = {
    "cure_light_wounds": {
        "duration_text": "Instantanée",
        "target_text": "Créature touchée",
        "roll_text": "1d8 + min(niveau de lanceur, 5)",
    },
    "cure_moderate_wounds": {
        "duration_text": "Instantanée",
        "target_text": "Créature touchée",
        "roll_text": "2d8 + min(niveau de lanceur, 10)",
    },
    "cure_serious_wounds": {
        "duration_text": "Instantanée",
        "target_text": "Créature touchée",
        "roll_text": "3d8 + min(niveau de lanceur, 15)",
    },
    "cure_critical_wounds": {
        "duration_text": "Instantanée",
        "target_text": "Créature touchée",
        "roll_text": "4d8 + min(niveau de lanceur, 20)",
    },
    "bless": {
        "range_text": "50 ft",
        "duration_text": "1 min./niveau",
        "target_text": "Alliés dans une explosion de 50 ft centrée sur le lanceur",
    },
    "aid": {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Créature vivante touchée",
        "roll_text": "1d8 + niveau de lanceur (max +10) PV temporaires",
    },
    "divine_favor": {
        "range_text": "Personal",
        "duration_text": "1 minute",
        "target_text": "Le lanceur",
    },
    "shield_of_faith": {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Créature touchée",
    },
    "bulls_strength": {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Créature touchée",
    },
    "bears_endurance": {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Créature touchée",
    },
    "eagles_splendor": {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Créature touchée",
    },
    "owls_wisdom": {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Créature touchée",
    },
    "spiritual_weapon": {
        "duration_text": "1 round/niveau",
        "target_text": "Arme de force créée par le sort",
    },
    "magic_weapon": {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Arme touchée",
    },
    "magic_vestment": {
        "range_text": "Touch",
        "duration_text": "1 heure/niveau",
        "target_text": "Armure ou bouclier touché",
    },
    "divine_power": {
        "range_text": "Personal",
        "duration_text": "1 round/niveau",
        "target_text": "Le lanceur",
    },
}

for _alignment_key in (
    "protection_from_chaos",
    "protection_from_evil",
    "protection_from_good",
    "protection_from_law",
):
    CASTING_DETAILS[_alignment_key] = {
        "range_text": "Touch",
        "duration_text": "1 min./niveau",
        "target_text": "Créature touchée",
    }


def _with_casting_details(row):
    result = dict(row)
    result.update(CASTING_DETAILS.get(str(result.get("key") or ""), {}))
    return result


DOMAIN_SPELLS = {
    "war": {
        1: "Magic Weapon",
        2: "Spiritual Weapon",
        3: "Magic Vestment",
        4: "Divine Power",
        5: "Flame Strike",
        6: "Blade Barrier",
        7: "Power Word Blind",
        8: "Power Word Stun",
        9: "Power Word Kill",
    },
    "sun": {
        1: "Endure Elements",
        2: "Heat Metal",
        3: "Searing Light",
        4: "Fire Shield",
        5: "Flame Strike",
        6: "Fire Seeds",
        7: "Sunbeam",
        8: "Sunburst",
        9: "Prismatic Sphere",
    },
}

DOMAIN_ALIASES = {
    "war": "war",
    "guerre": "war",
    "sun": "sun",
    "soleil": "sun",
}


def normalize_domain(value):
    text = str(value or "").strip().casefold()
    return DOMAIN_ALIASES.get(text, text)


def domain_spell_rows(domains, max_spell_level=9):
    rows = []
    seen = set()
    for original in domains or ():
        normalized = normalize_domain(original)
        if normalized not in DOMAIN_SPELLS:
            continue
        display_domain = str(original or normalized).strip() or normalized.title()
        for level, name in DOMAIN_SPELLS[normalized].items():
            if level > int(max_spell_level):
                continue
            key = (normalized, level, name)
            if key in seen:
                continue
            seen.add(key)
            base_spell = next(
                (
                    _with_casting_details(row)
                    for row in CLERIC_SPELLS.values()
                    if str(row.get("name") or "").casefold() == str(name).casefold()
                ),
                None,
            )
            if base_spell:
                domain_row = dict(base_spell)
                domain_row.update(
                    {
                        "key": f"domain_{normalized}_{level}",
                        "spell_level": level,
                        "slot_kind": "domain",
                        "domain_source": display_domain,
                    }
                )
            else:
                domain_row = {
                    "key": f"domain_{normalized}_{level}",
                    "name": name,
                    "spell_level": level,
                    "school": "Domaine",
                    "summary": f"Sort de domaine {display_domain} — niveau {level}.",
                    "range_text": "",
                    "source_text": "Pathfinder RPG Core Rulebook",
                    "slot_kind": "domain",
                    "domain_source": display_domain,
                }
            rows.append(domain_row)
    return rows


def catalog_rows(*, max_spell_level=9, domains=()):
    maximum = int(max_spell_level)
    rows = [
        _with_casting_details(row)
        for row in CLERIC_SPELLS.values()
        if int(row["spell_level"]) <= maximum
    ]
    rows.extend(domain_spell_rows(domains, maximum))
    rows.sort(
        key=lambda row: (
            int(row["spell_level"]),
            1 if row.get("slot_kind") == "domain" else 0,
            str(row["name"]).casefold(),
        )
    )
    return rows


def catalog_by_key(*, max_spell_level=9, domains=()):
    return {
        row["key"]: row
        for row in catalog_rows(
            max_spell_level=max_spell_level,
            domains=domains,
        )
    }
