from __future__ import annotations

import argparse
import importlib.util
import py_compile
import shutil
import sys
import zipfile
from pathlib import Path

VERSION = "1.6.0"
DATE = "2026-09-14"
EXPECTED_BASE = "eb1d83b396d596319134be87a0e9b9d611a202d3"

RELEASE_NOTE = '''    {
        "app_key": "rpg",
        "version": "1.6.0",
        "date": "2026-09-14",
        "title": "Personnages JDR — V1.6.0",
        "summary": (
            "Portrait persistant du personnage directement dans la bannière, "
            "avec ajout, remplacement, agrandissement et suppression."
        ),
        "changes": [
            "Le portrait apparaît directement à gauche du nom du personnage dans la bannière.",
            "Ajout, remplacement, aperçu agrandi et suppression de la photo sans supprimer le personnage.",
            "Formats JPEG, PNG et WEBP acceptés; orientation automatique, réduction à 1000 px maximum et conversion JPEG avant stockage.",
            "Les photos de départ sont limitées à 8 Mo et 25 mégapixels afin de garder un stockage raisonnable.",
            "Le portrait est conservé dans PostgreSQL dans une table privée dédiée, une image par personnage, avec suppression automatique lorsque le personnage est supprimé.",
            "Création automatique non destructive de la table rpg_character_portraits; aucun SQL manuel.",
            "Ajout de Pillow pour le traitement local des images avant leur enregistrement.",
        ],
    },
'''

MANUAL_INSERT = '''### V1.6.0 — portrait / photo du personnage

La V1.6.0 ajoute un **portrait persistant** directement dans la bannière de la fiche, à gauche du nom du personnage.

Le bouton **Photo** permet :

- d’ajouter un portrait;
- de remplacer le portrait existant;
- de supprimer uniquement la photo sans supprimer le personnage;
- de cliquer sur le portrait pour l’afficher en plus grand.

Les formats **JPEG, PNG et WEBP** sont acceptés. Avant l’enregistrement, la photo est automatiquement orientée selon ses informations EXIF, réduite à **1000 × 1000 px maximum**, convertie en JPEG et, si nécessaire, sa transparence est aplatie sur fond blanc.

Le fichier choisi est limité à **8 Mo** et à **25 mégapixels** avant traitement.

Le portrait est conservé dans PostgreSQL dans la table privée `rpg_character_portraits`, avec une seule image par personnage. La suppression d’un personnage supprime automatiquement son portrait. La table est créée automatiquement de façon non destructive; aucun SQL manuel n’est requis.

'''

STATUS_INSERT = '''## JDR — finalisation V1.6.0 — 2026-09-14

- Base GitHub observée avant cette finalisation : `eb1d83b396d596319134be87a0e9b9d611a202d3` (`main`).
- JDR passe officiellement à **V1.6.0**; Finances reste **V1.13.5**.
- Le **portrait du personnage** est maintenant intégré directement à gauche du nom dans la bannière de la fiche.
- Le portrait peut être ajouté, remplacé, agrandi ou supprimé sans supprimer le personnage.
- Formats acceptés : JPEG, PNG et WEBP; orientation EXIF appliquée, réduction à 1000 × 1000 px maximum, transparence aplatie sur fond blanc et conversion JPEG qualité 86.
- Les fichiers de départ sont limités à 8 Mo et 25 mégapixels.
- Le portrait est conservé dans PostgreSQL dans `rpg_character_portraits`, une ligne par personnage, avec `BYTEA`, contrôle de propriété utilisateur et `ON DELETE CASCADE`.
- La table est créée automatiquement de façon idempotente et non destructive; aucun SQL manuel.
- La dépendance **Pillow** a été ajoutée pour le traitement des images.
- L’utilisateur a validé en déploiement l’ajout, l’affichage et le fonctionnement du portrait et a confirmé : « parfait ca fonctionne ».
- PostgreSQL de production et Canner n’ont pas été testés indépendamment par ChatGPT; la validation fonctionnelle ci-dessus provient du test réel de l’utilisateur.
- Prochaine fonction JDR prévue : **armes détaillées et lien Équipement ↔ Attaques**. Les sorts pourront suivre après stabilisation des domaines.

'''


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: repère attendu une seule fois, trouvé {count} fois."
        )
    return text.replace(old, new, 1)


def _require_portrait_phase(root: Path) -> None:
    required = [
        "rpg_character.py",
        "rpg_character_ui.py",
        "rpg_character_portrait.py",
        "rpg_character_portrait_data.py",
        "rpg_character_portrait_images.py",
        "requirements.txt",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise RuntimeError(
            "La phase Portrait ne semble pas installée. Fichiers manquants : "
            + ", ".join(missing)
        )

    facade = _read(root / "rpg_character.py")
    shell = _read(root / "rpg_character_ui.py")
    requirements = _read(root / "requirements.txt").splitlines()

    if "_impl._portrait_block = _portrait_block" not in facade:
        raise RuntimeError(
            "rpg_character.py ne contient pas le raccordement du portrait."
        )
    if "_portrait_block(user_id, character)" not in shell:
        raise RuntimeError(
            "rpg_character_ui.py ne contient pas le portrait dans la bannière."
        )
    if "Pillow" not in requirements:
        raise RuntimeError(
            "requirements.txt ne contient pas Pillow."
        )


def patch_app_versions(text: str) -> str:
    already_version = '    "rpg": "1.6.0",' in text
    already_note = (
        '"app_key": "rpg",' in text
        and '"version": "1.6.0",' in text
        and '"title": "Personnages JDR — V1.6.0"' in text
    )
    if already_version and already_note:
        return text

    prefix, marker, suffix = text.partition("RELEASE_NOTES = [\n")
    if not marker:
        raise RuntimeError(
            "app_versions.py: RELEASE_NOTES introuvable."
        )

    if '    "rpg": "1.5.0",' not in prefix:
        raise RuntimeError(
            "app_versions.py: la version JDR attendue est 1.5.0."
        )

    prefix = _replace_once(
        prefix,
        '    "rpg": "1.5.0",',
        '    "rpg": "1.6.0",',
        "app_versions.py / version JDR",
    )
    return prefix + marker + RELEASE_NOTE + suffix


def patch_manual(text: str) -> str:
    if '"title": "Personnages JDR — V1.6.0"' not in text:
        text = _replace_once(
            text,
            '"title": "Personnages JDR — V1.5.0"',
            '"title": "Personnages JDR — V1.6.0"',
            "manual.py / titre JDR",
        )

    old_caption = (
        '"caption": "Dons, foi, progression, équipement et feuille '
        'Pathfinder / Ravenloft"'
    )
    new_caption = (
        '"caption": "Portrait, dons, foi, progression et feuille '
        'Pathfinder / Ravenloft"'
    )
    if old_caption in text:
        text = text.replace(old_caption, new_caption, 1)

    old_keywords = (
        '            "foi divinité iomedae guerre war soleil sun sous-domaine "\n'
        '            "combat casting selective channeling"\n'
    )
    new_keywords = (
        '            "foi divinité iomedae guerre war soleil sun sous-domaine "\n'
        '            "combat casting selective channeling portrait photo image "\n'
        '            "jpeg jpg png webp"\n'
    )
    if old_keywords in text:
        text = text.replace(old_keywords, new_keywords, 1)
    elif "portrait photo image" not in text:
        raise RuntimeError(
            "manual.py: repère des mots-clés JDR V1.5.0 introuvable."
        )

    if "### V1.6.0 — portrait / photo du personnage" not in text:
        anchor = (
            '        "content": """\n'
            "### V1.5.0 — dons structurés et foi / domaines\n"
        )
        replacement = (
            '        "content": """\n'
            + MANUAL_INSERT
            + "### V1.5.0 — dons structurés et foi / domaines\n"
        )
        text = _replace_once(
            text,
            anchor,
            replacement,
            "manual.py / insertion V1.6.0",
        )

    old_limits = (
        "Les dons et la foi sont maintenant structurés. Le portrait du personnage, "
        "les armes détaillées liées entre Équipement et Attaques, les capacités "
        "spéciales avancées, les sorts, l’impression PDF et les groupes de campagne "
        "restent prévus pour des versions ultérieures."
    )
    new_limits = (
        "Les dons, la foi et le portrait sont maintenant structurés. Les armes "
        "détaillées liées entre Équipement et Attaques, les capacités spéciales "
        "avancées, les sorts, l’impression PDF et les groupes de campagne restent "
        "prévus pour des versions ultérieures."
    )
    if old_limits in text:
        text = text.replace(old_limits, new_limits, 1)

    return text


def patch_status(text: str) -> str:
    if "| Personnages JDR | 1.6.0 |" not in text:
        text = _replace_once(
            text,
            "| Personnages JDR | 1.5.0 |",
            "| Personnages JDR | 1.6.0 |",
            "PROJECT_STATUS.md / version JDR",
        )

    if "## JDR — finalisation V1.6.0 — 2026-09-14" not in text:
        anchor = "## Finances — état actuel\n"
        text = _replace_once(
            text,
            anchor,
            STATUS_INSERT + anchor,
            "PROJECT_STATUS.md / insertion V1.6.0",
        )

    old_next = (
        "- Prochaine fonction JDR prévue : **portrait / photo du personnage**, "
        "puis armes détaillées liées aux Attaques, puis sorts après "
        "stabilisation des domaines.\n"
    )
    if old_next in text:
        text = text.replace(
            old_next,
            "- Cette étape a ensuite été complétée par la V1.6.0, qui ajoute "
            "le portrait du personnage.\n",
            1,
        )

    return text


def patch_integration_test(text: str) -> str:
    text = text.replace(
        '"""Raccordements structuraux JDR — V1.5.0."""',
        '"""Raccordements structuraux JDR — V1.6.0."""',
        1,
    )

    if '"_impl._portrait_block = _portrait_block"' not in text:
        marker = '            "_impl._identity_panel = _identity_panel",\n'
        if marker not in text:
            raise RuntimeError(
                "test d’intégration: repère des panneaux introuvable."
            )
        text = text.replace(
            marker,
            '            "_impl._portrait_block = _portrait_block",\n'
            + marker,
            1,
        )

    text = text.replace(
        'self.assertEqual(APP_VERSIONS["rpg"], "1.5.0")',
        'self.assertEqual(APP_VERSIONS["rpg"], "1.6.0")',
        1,
    )

    # Le test actuel vérifie que la première note JDR correspond à la version.
    text = text.replace(
        'self.assertEqual(rpg_notes[0]["version"], "1.5.0")',
        'self.assertEqual(rpg_notes[0]["version"], "1.6.0")',
        1,
    )

    return text


def validate_outputs(root: Path) -> None:
    app_versions = _read(root / "app_versions.py")
    manual = _read(root / "manual.py")
    status = _read(root / "PROJECT_STATUS.md")
    integration = _read(
        root / "tests" / "test_rpg_character_integration.py"
    )

    required_checks = [
        (
            '    "rpg": "1.6.0",',
            app_versions,
            "app_versions.py / version",
        ),
        (
            '"version": "1.6.0"',
            app_versions,
            "app_versions.py / note",
        ),
        (
            '"title": "Personnages JDR — V1.6.0"',
            manual,
            "manual.py / titre",
        ),
        (
            "### V1.6.0 — portrait / photo du personnage",
            manual,
            "manual.py / section portrait",
        ),
        (
            "| Personnages JDR | 1.6.0 |",
            status,
            "PROJECT_STATUS.md / version",
        ),
        (
            "## JDR — finalisation V1.6.0 — 2026-09-14",
            status,
            "PROJECT_STATUS.md / section",
        ),
        (
            "_impl._portrait_block = _portrait_block",
            integration,
            "test intégration / portrait",
        ),
        (
            'APP_VERSIONS["rpg"], "1.6.0"',
            integration,
            "test intégration / version",
        ),
    ]
    for needle, haystack, label in required_checks:
        if needle not in haystack:
            raise RuntimeError(f"Validation échouée : {label}.")

    # Compilation Python des fichiers touchés.
    for relative in [
        "app_versions.py",
        "manual.py",
        "tests/test_rpg_character_integration.py",
    ]:
        py_compile.compile(
            str(root / relative),
            doraise=True,
        )

    # Charger app_versions.py sans importer le reste de l'application.
    spec = importlib.util.spec_from_file_location(
        "_jdr_v160_app_versions",
        root / "app_versions.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Impossible de charger app_versions.py pour la validation."
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if module.APP_VERSIONS["rpg"] != "1.6.0":
        raise RuntimeError(
            "APP_VERSIONS ne retourne pas JDR 1.6.0."
        )

    rpg_notes = [
        note
        for note in module.RELEASE_NOTES
        if note.get("app_key") == "rpg"
    ]
    if not rpg_notes or rpg_notes[0].get("version") != "1.6.0":
        raise RuntimeError(
            "La première note de version JDR n’est pas 1.6.0."
        )


def build_output_zip(root: Path) -> Path:
    output = root / "JDR_V160_FINAL_FICHIERS_A_UPLOADER.zip"
    files = [
        "app_versions.py",
        "manual.py",
        "PROJECT_STATUS.md",
        "tests/test_rpg_character_integration.py",
    ]
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for relative in files:
            archive.write(root / relative, relative)
    return output


def finalize(root: Path) -> Path:
    root = root.resolve()
    required_metadata = [
        root / "app_versions.py",
        root / "manual.py",
        root / "PROJECT_STATUS.md",
        root / "tests" / "test_rpg_character_integration.py",
    ]
    missing = [str(path) for path in required_metadata if not path.exists()]
    if missing:
        raise RuntimeError(
            "Fichiers de finalisation manquants :\n- "
            + "\n- ".join(missing)
        )

    _require_portrait_phase(root)

    backup = root / "_backup_avant_JDR_V160"
    if backup.exists():
        shutil.rmtree(backup)
    (backup / "tests").mkdir(parents=True)

    for relative in [
        "app_versions.py",
        "manual.py",
        "PROJECT_STATUS.md",
        "tests/test_rpg_character_integration.py",
    ]:
        source = root / relative
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    try:
        app_versions_path = root / "app_versions.py"
        manual_path = root / "manual.py"
        status_path = root / "PROJECT_STATUS.md"
        integration_path = (
            root / "tests" / "test_rpg_character_integration.py"
        )

        _write(
            app_versions_path,
            patch_app_versions(_read(app_versions_path)),
        )
        _write(
            manual_path,
            patch_manual(_read(manual_path)),
        )
        _write(
            status_path,
            patch_status(_read(status_path)),
        )
        _write(
            integration_path,
            patch_integration_test(_read(integration_path)),
        )

        validate_outputs(root)
        return build_output_zip(root)

    except Exception:
        for relative in [
            "app_versions.py",
            "manual.py",
            "PROJECT_STATUS.md",
            "tests/test_rpg_character_integration.py",
        ]:
            original = backup / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Finalise le module JDR en V1.6.0 après validation "
            "du portrait du personnage."
        )
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Racine du dépôt décompressé (défaut : dossier courant).",
    )
    args = parser.parse_args()

    root = Path(args.root)

    try:
        output = finalize(root)
    except Exception as error:
        print()
        print("ÉCHEC DE LA FINALISATION JDR V1.6.0")
        print("-----------------------------------")
        print(error)
        print()
        print(
            "Les quatre fichiers de métadonnées ont été restaurés "
            "à partir de la sauvegarde."
        )
        return 1

    print()
    print("FINALISATION JDR V1.6.0 RÉUSSIE")
    print("--------------------------------")
    print(f"ZIP créé : {output.name}")
    print()
    print("À téléverser dans GitHub en conservant les chemins :")
    print("- app_versions.py")
    print("- manual.py")
    print("- PROJECT_STATUS.md")
    print("- tests/test_rpg_character_integration.py")
    print()
    print(
        "Aucun changement de schéma PostgreSQL supplémentaire "
        "n'est effectué par cette finalisation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
