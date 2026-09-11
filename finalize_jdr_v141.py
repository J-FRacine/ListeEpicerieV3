from __future__ import annotations

import argparse
import py_compile
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

VERSION = "1.4.1"
DATE = "2026-09-11"
EXPECTED_BASE = "fde33144220983233e351f0c4a4dbf53a57e1a2a"

RELEASE_NOTE = '''    {
        "app_key": "rpg",
        "version": "1.4.1",
        "date": "2026-09-11",
        "title": "Personnages JDR — V1.4.1",
        "summary": "Aides de création Fighter et Clerc niveaux 1 à 4, avec repères d’équipement et correction de l’enchaînement Identité/Race.",
        "changes": [
            "Création guidée : un nouveau personnage peut compléter Identité puis Race sans être bloqué par la race encore non choisie; les deux étapes sont enregistrées ensemble lorsque nécessaire.",
            "Aide Fighter / Guerrier niveaux 1 à 4 : BBA, sauvegardes de base, dons, compétences de classe, budget de rangs et rappels de progression.",
            "Comparaison Humain / Elfe pour un Fighter orienté vers la magie, sans modifier automatiquement les caractéristiques ni imposer une multiclassification.",
            "Aide Clerc / Cleric niveaux 1 à 4 : BBA, sauvegardes, canalisation, sorts par jour, Sagesse, Charisme, dons et compétences de classe.",
            "Catalogue de référence pour des armes, armures et boucliers courants; l’Équipement et les Attaques existants restent les données réelles utilisées par la feuille et Combat rapide.",
            "Aucun changement de schéma PostgreSQL, aucune migration, aucun SQL manuel et aucune nouvelle dépendance Python.",
        ],
    },
'''

MANUAL_INSERT = '''### V1.4.1 — aides Fighter et Clerc

La création guidée contient maintenant des repères spécialisés pour **Fighter / Guerrier** et **Clerc / Cleric** aux niveaux 1 à 4. Ces aides servent de référence et n’écrasent pas silencieusement les choix déjà inscrits sur la feuille.

Pour un nouveau personnage dont la race n’est pas encore choisie, l’étape **Identité** peut maintenant être complétée avant **Race** : lorsque la sélection raciale est encore en attente, les deux étapes sont enregistrées ensemble au moment approprié au lieu de bloquer l’assistant. Le champ **Sous-classe / archétype** demeure facultatif.

#### Fighter / Guerrier

L’aide Fighter présente notamment :

- le dé de vie **d10**;
- le BBA et les sauvegardes de base des niveaux 1 à 4;
- les rappels de Bravoure, Entraînement aux armures et augmentation de caractéristique;
- le nombre de dons généraux, de dons de combat bonus et le don racial supplémentaire de l’Humain;
- les compétences de classe du Fighter et un repère du budget de rangs;
- une comparaison **Humain / Elfe** pour un Fighter qui souhaite garder une orientation magique;
- un rappel que l’Elfe ne donne pas à lui seul de progression de sorts de classe et qu’un futur choix magique doit rester volontaire.

Les changements de race restent non destructifs : ils ne modifient jamais automatiquement les six scores de caractéristiques.

#### Clerc / Cleric

L’aide Clerc présente notamment :

- le dé de vie **d8**;
- le BBA et les sauvegardes de base des niveaux 1 à 4;
- la canalisation d’énergie et ses repères de dés, d’utilisations quotidiennes et de DD;
- les sorts divins par jour jusqu’au niveau 4, avec le niveau maximal de sorts accessible;
- la **Sagesse** comme caractéristique principale des sorts et le **Charisme** pour la canalisation;
- les dons et le bonus racial de l’Humain;
- les compétences de classe du Clerc et un repère du budget de rangs;
- le rappel des **deux domaines** à choisir selon la divinité ou les règles de campagne.

#### Armes, armures et boucliers

L’assistant offre aussi un **catalogue de référence** pour des armes, armures et boucliers courants. Il sert à faciliter la saisie, mais ne crée pas une seconde logique concurrente :

- l’onglet **Équipement** reste la source réelle pour ce qui est transporté ou équipé;
- les armures et boucliers équipés continuent d’alimenter la CA, la DEX maximale, les pénalités aux tests, le poids et la vitesse;
- le risque d’échec des sorts profanes reste visible lorsqu’une armure est pertinente pour une orientation magique;
- l’onglet **Attaques** reste la source réelle pour les dégâts, critique, portée, type, bonus et munitions;
- **Combat rapide** continue d’utiliser les attaques enregistrées sur la feuille.

V1.4.1 n’ajoute aucune table de base de données et ne nécessite aucune migration PostgreSQL.

'''

STATUS_INSERT = '''## JDR — finalisation V1.4.1 — 2026-09-11

- Base GitHub utilisée pour la finalisation : `fde33144220983233e351f0c4a4dbf53a57e1a2a` (`main`).
- JDR passe officiellement à **V1.4.1**; Finances reste **V1.13.5**.
- La création guidée accepte maintenant l’enchaînement Identité → Race d’un nouveau personnage lorsque la race n’est pas encore choisie; la sous-classe / l’archétype reste facultatif.
- Aide **Fighter / Guerrier** niveaux 1 à 4 : progression de classe, dons, compétences, comparaison Humain / Elfe et orientation magique non destructive.
- Aide **Clerc / Cleric** niveaux 1 à 4 : progression, canalisation, sorts divins, Sagesse/Charisme, dons, compétences et domaines.
- Le catalogue armes/armures sert de référence seulement; les onglets Équipement et Attaques demeurent les sources réelles utilisées par les calculs et Combat rapide.
- Aucun changement de schéma PostgreSQL, aucune migration, aucun SQL manuel et aucune nouvelle dépendance.
- La validation utilisateur sur Canner/dans le navigateur a confirmé le fonctionnement de la création guidée, de Combat rapide et des aides Fighter/Clerc. PostgreSQL de production n’a pas été testé indépendamment dans cette finalisation.
- Prochaine intervention technique recommandée : modularisation progressive de `rpg_character.py`, dans une livraison séparée et sans changement fonctionnel volontaire.

'''


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: repère attendu une seule fois, trouvé {count} fois.")
    return text.replace(old, new, 1)


def patch_app_versions(text: str) -> str:
    if '"rpg": "1.4.1"' in text and '"version": "1.4.1"' in text:
        return text

    prefix, marker, suffix = text.partition("RELEASE_NOTES = [\n")
    if not marker:
        raise RuntimeError("app_versions.py: RELEASE_NOTES introuvable.")
    prefix = _replace_once(
        prefix,
        '    "rpg": "1.4.0",',
        '    "rpg": "1.4.1",',
        "app_versions.py / version JDR",
    )
    return prefix + marker + RELEASE_NOTE + suffix


def patch_manual(text: str) -> str:
    if '"title": "Personnages JDR — V1.4.1"' not in text:
        text = _replace_once(
            text,
            '"title": "Personnages JDR — V1.4.0"',
            '"title": "Personnages JDR — V1.4.1"',
            "manual.py / titre JDR",
        )

    if "### V1.4.1 — aides Fighter et Clerc" not in text:
        anchor = '        "content": """\n### Création rapide ou guidée\n'
        replacement = '        "content": """\n' + MANUAL_INSERT + '### Création rapide ou guidée\n'
        text = _replace_once(text, anchor, replacement, "manual.py / section JDR")

    old_keywords = (
        '            "progression niveau montée niveau sous-classe facultative historique dons capacités"\n'
    )
    new_keywords = (
        '            "progression niveau montée niveau sous-classe facultative historique dons capacités "\n'
        '            "fighter guerrier cleric clerc humain elfe magie canalisation domaines sorts divins"\n'
    )
    if old_keywords in text:
        text = text.replace(old_keywords, new_keywords, 1)
    return text


def patch_status(text: str) -> str:
    if "Dernière mise à jour : 2026-09-11" not in text:
        text = _replace_once(
            text,
            "Dernière mise à jour : 2026-09-10",
            "Dernière mise à jour : 2026-09-11",
            "PROJECT_STATUS.md / date",
        )

    # Le tableau était déjà en retard sur Grocery et JDR; le réaligner sur app_versions.py.
    text = text.replace("| Liste d'épicerie | 1.1.2 |", "| Liste d'épicerie | 1.2.0 |", 1)
    text = text.replace("| Personnages JDR | 1.3.0 |", "| Personnages JDR | 1.4.1 |", 1)
    text = text.replace("| Personnages JDR | 1.4.0 |", "| Personnages JDR | 1.4.1 |", 1)

    if "## JDR — finalisation V1.4.1 — 2026-09-11" not in text:
        anchor = "## Finances — état actuel\n"
        text = _replace_once(
            text,
            anchor,
            STATUS_INSERT + anchor,
            "PROJECT_STATUS.md / insertion V1.4.1",
        )
    return text


def patch_integration_test(text: str) -> str:
    if "APP_VERSIONS['rpg'], '1.4.1'" in text:
        return text
    text = _replace_once(
        text,
        "self.assertEqual(app_versions.APP_VERSIONS['rpg'], '1.4.0')",
        "self.assertEqual(app_versions.APP_VERSIONS['rpg'], '1.4.1')",
        "test_rpg_character_integration.py / version",
    )
    text = _replace_once(
        text,
        "self.assertEqual(note['version'], '1.4.0')",
        "self.assertEqual(note['version'], '1.4.1')",
        "test_rpg_character_integration.py / note",
    )
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalise JDR V1.4.1 dans une copie locale du dépôt F Apps.")
    parser.add_argument("repo", nargs="?", default=".", help="Dossier racine du dépôt (défaut: dossier courant)")
    args = parser.parse_args()
    root = Path(args.repo).resolve()

    paths = {
        "app_versions.py": root / "app_versions.py",
        "manual.py": root / "manual.py",
        "PROJECT_STATUS.md": root / "PROJECT_STATUS.md",
        "tests/test_rpg_character_integration.py": root / "tests" / "test_rpg_character_integration.py",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        print("ERREUR — fichiers manquants :", ", ".join(missing))
        return 2

    originals = {name: _read(path) for name, path in paths.items()}
    patched = {
        "app_versions.py": patch_app_versions(originals["app_versions.py"]),
        "manual.py": patch_manual(originals["manual.py"]),
        "PROJECT_STATUS.md": patch_status(originals["PROJECT_STATUS.md"]),
        "tests/test_rpg_character_integration.py": patch_integration_test(
            originals["tests/test_rpg_character_integration.py"]
        ),
    }

    backup_dir = root / "_backup_avant_JDR_V141"
    backup_dir.mkdir(exist_ok=True)
    for name, path in paths.items():
        backup = backup_dir / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            _write(backup, originals[name])
        _write(path, patched[name])

    # Contrôles de syntaxe sans importer l'application ni la base.
    try:
        py_compile.compile(str(paths["app_versions.py"]), doraise=True)
        py_compile.compile(str(paths["manual.py"]), doraise=True)
        py_compile.compile(str(paths["tests/test_rpg_character_integration.py"]), doraise=True)
    except py_compile.PyCompileError as exc:
        print("ERREUR DE COMPILATION — restauration des fichiers originaux.")
        for name, path in paths.items():
            _write(path, originals[name])
        print(exc)
        return 3

    # Vérifications textuelles ciblées.
    checks = [
        ('"rpg": "1.4.1"', patched["app_versions.py"]),
        ('"version": "1.4.1"', patched["app_versions.py"]),
        ('"title": "Personnages JDR — V1.4.1"', patched["manual.py"]),
        ("### V1.4.1 — aides Fighter et Clerc", patched["manual.py"]),
        ("## JDR — finalisation V1.4.1 — 2026-09-11", patched["PROJECT_STATUS.md"]),
        ("APP_VERSIONS['rpg'], '1.4.1'", patched["tests/test_rpg_character_integration.py"]),
    ]
    for needle, haystack in checks:
        if needle not in haystack:
            print(f"ERREUR — vérification manquante : {needle}")
            for name, path in paths.items():
                _write(path, originals[name])
            return 4

    out_zip = root / "JDR_V141_FINAL_FICHIERS_A_UPLOADER.zip"
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in paths.items():
            archive.write(path, arcname=name)

    print("JDR V1.4.1 finalisé avec succès.")
    print("Compilation Python : OK")
    print(f"ZIP prêt à téléverser : {out_zip}")
    print(f"Sauvegarde locale : {backup_dir}")
    print("Aucune connexion PostgreSQL et aucun déploiement Canner n'ont été effectués.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
