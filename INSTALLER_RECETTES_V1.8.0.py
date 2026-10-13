from __future__ import annotations

from datetime import datetime
from pathlib import Path
import ast
import compileall
import json
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "payload"
MANIFEST = ROOT / "patch_manifest.json"
LOG = ROOT / "tests-resultats-recettes-v1.8.0.log"
BACKUP = ROOT / (
    "_backup_recettes_v1.8.0_"
    + datetime.now().strftime("%Y%m%d_%H%M%S")
)

PATCHED_FILES = [
    "recipes_extras.py",
    "recipes.py",
    "recipes_reader.py",
    "app_versions.py",
    "manual.py",
    "PROJECT_STATUS.md",
    "tests/test_recipes_batch_import.py",
    "tests/test_recipes_v1.py",
    "tests/test_recipes_v120.py",
    "tests/test_recipes_v130.py",
    "tests/test_recipes_v131.py",
    "tests/test_recipes_v140.py",
    "tests/test_recipes_v141.py",
    "tests/test_recipes_v142.py",
    "tests/test_recipes_v150.py",
    "tests/test_recipes_v160.py",
]

REPLACEMENT_FILES = [
    "recipes_extras_ui.py",
]

NEW_FILES = [
    "recipes_food_catalog.py",
    "recipes_ingredient_analysis.py",
    "recipes_ingredient_tools_ui.py",
    "recipes_pdf.py",
    "recipes_export_ui.py",
    "tests/test_recipes_v180.py",
]

BACKUP_FILES = PATCHED_FILES + REPLACEMENT_FILES
PUBLISH_FILES = PATCHED_FILES + REPLACEMENT_FILES + NEW_FILES


def say(message=""):
    print(message)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def operations_by_file():
    operations = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = {}
    for operation in operations:
        result.setdefault(operation["file"], []).append(operation)
    return result


def apply_to_text(text, operations, relative):
    for operation in operations:
        label = operation.get("label") or relative

        if operation["op"] == "replace":
            old = operation["old"]
            count = text.count(old)
            if count != 1:
                raise RuntimeError(
                    f"{label}: motif attendu exactement 1 fois, "
                    f"trouvé {count} fois."
                )
            text = text.replace(old, operation["new"], 1)
            continue

        if operation["op"] == "insert_before":
            marker = operation["marker"]
            count = text.count(marker)
            if count != 1:
                raise RuntimeError(
                    f"{label}: repère attendu exactement 1 fois, "
                    f"trouvé {count} fois."
                )
            text = text.replace(
                marker,
                operation["addition"] + marker,
                1,
            )
            continue

        raise RuntimeError(f"Opération inconnue : {operation['op']}")

    return text


def verify_base():
    versions = read(ROOT / "app_versions.py")
    if '"recipes": "1.7.0"' not in versions:
        if '"recipes": "1.8.0"' in versions:
            raise RuntimeError("Recettes V1.8.0 semble déjà installée.")
        raise RuntimeError(
            "Base inattendue : l’installateur attend Recettes V1.7.0."
        )

    recipes_source = read(ROOT / "recipes.py")
    for expected in (
        '"Parcourir par catégorie"',
        '"Relier à un item de la liste d’épicerie"',
        'open_chatgpt_recipe_import_dialog',
    ):
        if expected not in recipes_source:
            raise RuntimeError(
                "La structure Recettes V1.7.0 attendue n’est pas présente : "
                + expected
            )

    extras_source = read(ROOT / "recipes_extras.py")
    if '"nutrition": None' not in extras_source:
        raise RuntimeError(
            "Le stockage nutritionnel Recettes attendu n’est pas présent."
        )


def preflight():
    """Valide tous les motifs et la syntaxe avant toute écriture."""
    for relative, operations in operations_by_file().items():
        path = ROOT / relative
        if not path.exists():
            raise RuntimeError(f"Fichier de base manquant : {relative}")

        patched = apply_to_text(read(path), operations, relative)
        if relative.endswith(".py"):
            try:
                ast.parse(patched, filename=relative)
            except SyntaxError as error:
                raise RuntimeError(
                    f"Prévalidation Python échouée pour {relative}, "
                    f"ligne {error.lineno}: {error.msg}"
                ) from error

    for relative in REPLACEMENT_FILES + NEW_FILES:
        source = PAYLOAD / relative
        if not source.exists():
            raise RuntimeError(f"Fichier du paquet manquant : {relative}")
        if relative.endswith(".py"):
            try:
                ast.parse(
                    source.read_text(encoding="utf-8"),
                    filename=relative,
                )
            except SyntaxError as error:
                raise RuntimeError(
                    f"Fichier Python invalide : {relative}, "
                    f"ligne {error.lineno}: {error.msg}"
                ) from error


def backup_files():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for relative in BACKUP_FILES:
        source = ROOT / relative
        if not source.exists():
            raise RuntimeError(f"Fichier de base manquant : {relative}")
        target = BACKUP / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def restore_files():
    for relative in BACKUP_FILES:
        source = BACKUP / relative
        if source.exists():
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    for relative in NEW_FILES:
        target = ROOT / relative
        if target.exists():
            target.unlink()


def apply_changes():
    for relative, operations in operations_by_file().items():
        path = ROOT / relative
        write(path, apply_to_text(read(path), operations, relative))

    for relative in REPLACEMENT_FILES + NEW_FILES:
        source = PAYLOAD / relative
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def run_command(title, command):
    say("")
    say(f"=== {title} ===")
    process = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if process.stdout:
        say(process.stdout.rstrip())
    if process.stderr:
        say(process.stderr.rstrip())
    if process.returncode != 0:
        raise RuntimeError(f"Échec : {title}")


def validate():
    say("")
    say("=== Compilation Python ===")
    if not compileall.compile_dir(ROOT, quiet=1, force=True):
        raise RuntimeError("Échec de compilation Python.")
    say("Compilation Python : OK")

    run_command(
        "Tests ciblés Recettes",
        [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_recipes*.py",
        ],
    )

    run_command(
        "Suite complète JF Apps",
        [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
        ],
    )


def build_publish_zip():
    target = ROOT / "A_PUBLIER_GITHUB_RECETTES_V1.8.0_MESURES_NUTRITION_PDF.zip"
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in PUBLISH_FILES:
            source = ROOT / relative
            if source.exists():
                archive.write(source, relative)
    return target


def main():
    LOG.write_text("", encoding="utf-8")

    say("Installation Recettes V1.8.0")
    say("Base attendue : Recettes V1.7.0")
    say("Base GitHub vérifiée : 6959e611d03775f93410ee70abaa1a223ea236ca")
    say("")
    say("Fonctions : conversions en grammes, nutrition estimée, PDF/impression/courriel.")
    say("Stockage : recipe_extra JSONB existant.")
    say("Aucune migration PostgreSQL.")
    say("Aucun SQL manuel.")
    say("Aucune nouvelle dépendance : reportlab est déjà présent.")

    try:
        verify_base()
        say("Prévalidation des modifications et de la syntaxe Python...")
        preflight()
        say("Prévalidation : OK")

        backup_files()
        say(f"Sauvegarde locale : {BACKUP.name}")

        apply_changes()
        validate()
        publish_zip = build_publish_zip()

        say("")
        say("SUCCES - Recettes V1.8.0 installée et validée localement.")
        say(f"Paquet GitHub : {publish_zip.name}")
        say(f"Journal : {LOG.name}")
        say("Fichiers à publier :")
        for relative in PUBLISH_FILES:
            say(f" - {relative}")
        say("")
        say(
            "Validation navigateur/Canner à faire après publication. "
            "Le script ne teste pas PostgreSQL de production."
        )
        return 0

    except Exception as error:
        say("")
        say(f"ECHEC - {error}")
        if BACKUP.exists():
            try:
                restore_files()
                say("Les fichiers d’origine ont été restaurés lorsque possible.")
            except Exception as restore_error:
                say("ATTENTION - restauration incomplète : " + str(restore_error))
        say(f"Consultez {LOG.name}.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
