"""Références de divinités Pathfinder 1e utilisées par la fiche JDR.

Le catalogue sert à préremplir et à afficher des repères. Il ne choisit jamais
automatiquement les domaines du personnage et ne modifie aucun calcul de règle.
"""
from __future__ import annotations


DEITY_PROFILES = {
    "iomedae": {
        "deity_name": "Iomedae",
        "title": "The Inheritor / L’Héritière",
        "alignment": "LG",
        "areas_of_concern": (
            "Honneur, justice, gouvernement et vaillance"
        ),
        "favored_weapon": "Épée longue (Longsword)",
        "symbol": "Épée et soleil",
        "sacred_animal": "Lion",
        "sacred_colors": "Rouge et blanc",
        "source_text": "Pathfinder 1e — Inner Sea Gods p. 76",
        "personal_domain_preset": ("War", "Sun"),
        "domains": {
            "Glory": (
                "Chivalry",
                "Heroism",
                "Honor",
                "Hubris (Glory)*",
            ),
            "Good": (
                "Archon (Good)",
                "Redemption",
            ),
            "Law": (
                "Archon (Law)",
                "Sovereignty",
            ),
            "Sun": (
                "Day",
                "Light",
                "Revelation",
            ),
            "War": (
                "Duels",
                "Tactics",
            ),
        },
        "domain_note": (
            "* Hubris (Glory) nécessite le trait Acolyte of Apocrypha."
        ),
        "unique_cleric_spells": (
            "Good Hope — niveau 4",
            "Mark of Justice — niveau 4",
            "Holy Sword — niveau 8",
        ),
        "future_equipment_reference": (
            "L’arme favorite d’Iomedae est l’épée longue. "
            "La future phase Armes pourra proposer de relier automatiquement "
            "cette référence à l’Équipement et aux Attaques."
        ),
    },
}
