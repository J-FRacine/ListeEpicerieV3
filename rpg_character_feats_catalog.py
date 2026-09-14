"""Petit catalogue de référence pour les dons Pathfinder 1e.

Ce catalogue sert uniquement à préremplir le formulaire. Le personnage garde
toujours ses propres données enregistrées et l'utilisateur peut tout modifier.
Aucune règle de don n'est imposée automatiquement à la feuille permanente.
"""
from __future__ import annotations


FEAT_KIND_LABELS = {
    "passive": "Passif",
    "active": "Activable",
    "info": "Informatif",
}

SAVE_TARGET_LABELS = {
    "": "Aucun jet",
    "all": "Tous les jets",
    "fortitude": "Vigueur",
    "reflex": "Réflexes",
    "will": "Volonté",
    "fear": "Peur",
    "horror": "Horreur",
    "madness": "Folie",
}

FEAT_TEMPLATES = {
    "": {"label": "Saisie libre"},
    "power_attack": {
        "label": "Attaque en puissance — Power Attack",
        "feat_name": "Attaque en puissance",
        "english_name": "Power Attack",
        "feat_kind": "active",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "FOR 13; BBA +1",
        "summary": (
            "Échanger une partie de la précision contre des dégâts supplémentaires "
            "sur les attaques de mêlée."
        ),
        "effects": (
            "Le malus d’attaque et le bonus de dégâts varient avec le BBA et la "
            "façon de manier l’arme. Inscrivez ci-dessous les valeurs correspondant "
            "au personnage actuel."
        ),
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "",
        "save_modifier": 0,
        "damage_note": "Bonus de dégâts à préciser selon BBA et prise en main.",
    },
    "weapon_focus": {
        "label": "Arme de prédilection — Weapon Focus",
        "feat_name": "Arme de prédilection",
        "english_name": "Weapon Focus",
        "feat_kind": "passive",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": (
            "Maîtrise de l’arme choisie; BBA +1 "
            "(conditions particulières possibles selon la classe)."
        ),
        "summary": "Bonus de +1 aux jets d’attaque avec l’arme choisie.",
        "effects": (
            "Liez idéalement le don à l’attaque correspondante afin que Combat "
            "rapide n’applique pas le bonus aux autres armes."
        ),
        "attack_modifier": 1,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "",
        "save_modifier": 0,
        "damage_note": "",
    },
    "improved_initiative": {
        "label": "Science de l’initiative — Improved Initiative",
        "feat_name": "Science de l’initiative",
        "english_name": "Improved Initiative",
        "feat_kind": "passive",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "",
        "summary": "Bonus de +4 aux tests d’initiative.",
        "effects": (
            "Le bonus est appliqué dans Combat rapide. Ne le recopiez pas aussi "
            "dans Divers initiative si vous voulez éviter un double comptage."
        ),
        "attack_modifier": 0,
        "initiative_modifier": 4,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "",
        "save_modifier": 0,
        "damage_note": "",
    },
    "combat_casting": {
        "label": "Incantation en combat — Combat Casting",
        "feat_name": "Incantation en combat",
        "english_name": "Combat Casting",
        "feat_kind": "active",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "",
        "summary": (
            "Bonus de +4 aux tests de concentration pour lancer un sort ou utiliser "
            "un pouvoir magique en lançant sur la défensive ou en étant agrippé."
        ),
        "effects": (
            "Don situationnel. Combat rapide permet de le cocher comme rappel, "
            "mais ne calcule pas encore les tests de concentration; le bonus de +4 "
            "doit donc être appliqué au test de concentration approprié."
        ),
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "",
        "save_modifier": 0,
        "damage_note": "",
    },
    "selective_channeling": {
        "label": "Canalisation sélective — Selective Channeling",
        "feat_name": "Canalisation sélective",
        "english_name": "Selective Channeling",
        "feat_kind": "active",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "CHA 13; aptitude de classe Canalisation d’énergie",
        "summary": (
            "Permet d’exclure certaines créatures de la zone d’une canalisation "
            "d’énergie."
        ),
        "effects": (
            "À chaque canalisation, choisissez un nombre de cibles dans la zone "
            "pouvant aller jusqu’au modificateur de Charisme du personnage; ces "
            "cibles ne sont pas affectées par cette canalisation. Combat rapide "
            "l’affiche comme don activable, sans modifier automatiquement les dés "
            "ou le DD de canalisation."
        ),
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "",
        "save_modifier": 0,
        "damage_note": "",
    },
    "great_fortitude": {
        "label": "Vigueur surhumaine — Great Fortitude",
        "feat_name": "Vigueur surhumaine",
        "english_name": "Great Fortitude",
        "feat_kind": "passive",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "",
        "summary": "Bonus de +2 aux jets de Vigueur.",
        "effects": "Le bonus est appliqué à Vigueur dans Combat rapide.",
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "fortitude",
        "save_modifier": 2,
        "damage_note": "",
    },
    "lightning_reflexes": {
        "label": "Réflexes surhumains — Lightning Reflexes",
        "feat_name": "Réflexes surhumains",
        "english_name": "Lightning Reflexes",
        "feat_kind": "passive",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "",
        "summary": "Bonus de +2 aux jets de Réflexes.",
        "effects": "Le bonus est appliqué à Réflexes dans Combat rapide.",
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "reflex",
        "save_modifier": 2,
        "damage_note": "",
    },
    "iron_will": {
        "label": "Volonté de fer — Iron Will",
        "feat_name": "Volonté de fer",
        "english_name": "Iron Will",
        "feat_kind": "passive",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "",
        "summary": "Bonus de +2 aux jets de Volonté.",
        "effects": "Le bonus est appliqué à Volonté dans Combat rapide.",
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "will",
        "save_modifier": 2,
        "damage_note": "",
    },
    "toughness": {
        "label": "Robustesse — Toughness",
        "feat_name": "Robustesse",
        "english_name": "Toughness",
        "feat_kind": "info",
        "source_text": "Pathfinder RPG — Core Rulebook",
        "prerequisites": "",
        "summary": "Augmente les points de vie du personnage.",
        "effects": (
            "Ce don est conservé comme référence dans cette phase. Les PV de la "
            "fiche ne sont pas modifiés automatiquement pour éviter de changer "
            "silencieusement un personnage déjà créé."
        ),
        "attack_modifier": 0,
        "initiative_modifier": 0,
        "cmb_modifier": 0,
        "cmd_modifier": 0,
        "save_key": "",
        "save_modifier": 0,
        "damage_note": "",
    },
}
