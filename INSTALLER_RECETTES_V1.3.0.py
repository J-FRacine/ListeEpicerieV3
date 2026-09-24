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
LOG = ROOT / "tests-resultats-recettes-v1.3.0.log"
BACKUP = ROOT / (
    "_backup_recettes_v1.3.0_"
    + datetime.now().strftime("%Y%m%d_%H%M%S")
)

PATCHED_FILES = [
    "grocery_schema.py",
    "recipes.py",
    "recipes_reader.py",
    "grocery_backup.py",
    "app_versions.py",
    "manual.py",
    "PROJECT_STATUS.md",
    "tests/test_recipes_v1.py",
    "tests/test_recipes_v120.py",
]
NEW_FILES = [
    "recipes_extras.py",
    "recipes_extras_ui.py",
    "recipes_chatgpt_import.py",
    "recipes_chatgpt_import_ui.py",
    "tests/test_recipes_v130.py",
]
PUBLISH_FILES = PATCHED_FILES + NEW_FILES


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


def _apply_operations_to_text(text, operations, relative):
    for operation in operations:
        label = operation.get("label") or relative
        op = operation["op"]

        if op == "replace":
            old = operation["old"]
            count = text.count(old)
            if count != 1:
                raise RuntimeError(
                    f"{label}: motif attendu exactement 1 fois, "
                    f"trouvé {count} fois."
                )
            text = text.replace(old, operation["new"], 1)
            continue

        if op == "insert_before":
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

        raise RuntimeError(f"Opération inconnue : {op}")

    return text


def verify_base():
    versions = read(ROOT / "app_versions.py")
    if '"recipes": "1.2.1"' not in versions:
        if '"recipes": "1.3.0"' in versions:
            raise RuntimeError(
                "Recettes V1.3.0 semble déjà installée."
            )
        raise RuntimeError(
            "Base inattendue : l’installateur attend Recettes V1.2.1."
        )


def preflight():
    """Valide tous les correctifs et leur syntaxe avant toute écriture."""
    for relative, operations in operations_by_file().items():
        path = ROOT / relative
        if not path.exists():
            raise RuntimeError(f"Fichier de base manquant : {relative}")
        patched = _apply_operations_to_text(
            read(path),
            operations,
            relative,
        )
        if relative.endswith(".py"):
            try:
                ast.parse(patched, filename=relative)
            except SyntaxError as error:
                raise RuntimeError(
                    f"Prévalidation Python échouée pour {relative}, "
                    f"ligne {error.lineno}: {error.msg}"
                ) from error

    for relative in NEW_FILES:
        source = PAYLOAD / relative
        if not source.exists():
            raise RuntimeError(f"Payload manquant : {relative}")
        if relative.endswith(".py"):
            try:
                ast.parse(
                    source.read_text(encoding="utf-8"),
                    filename=relative,
                )
            except SyntaxError as error:
                raise RuntimeError(
                    f"Nouveau fichier Python invalide : {relative}, "
                    f"ligne {error.lineno}: {error.msg}"
                ) from error


def backup_files():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for relative in PATCHED_FILES:
        source = ROOT / relative
        if not source.exists():
            raise RuntimeError(f"Fichier de base manquant : {relative}")
        target = BACKUP / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def restore_files():
    for relative in PATCHED_FILES:
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
        write(
            path,
            _apply_operations_to_text(
                read(path),
                operations,
                relative,
            ),
        )

    for relative in NEW_FILES:
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
    target = (
        ROOT
        / "A_PUBLIER_GITHUB_RECETTES_V1.3.0_CHATGPT_NUTRITION.zip"
    )
    if target.exists():
        target.unlink()

    with zipfile.ZipFile(
        target,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for relative in PUBLISH_FILES:
            source = ROOT / relative
            if source.exists():
                archive.write(source, relative)
    return target


def main():
    LOG.write_text("", encoding="utf-8")
    say("Installation Recettes V1.3.0")
    say("Base attendue : Recettes V1.2.1")
    say(
        "Migration PostgreSQL : ajout automatique et idempotent "
        "de grocery_recipes.recipe_extra JSONB."
    )
    say("Aucun SQL manuel requis.")

    try:
        verify_base()
        say("Prévalidation du correctif : motifs et syntaxe Python...")
        preflight()
        say("Prévalidation : OK")

        backup_files()
        say(f"Sauvegarde locale : {BACKUP.name}")

        apply_changes()
        validate()
        publish_zip = build_publish_zip()

        say("")
        say(
            "SUCCES - Recettes V1.3.0 installée et validée localement."
        )
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
                say(
                    "Les fichiers d’origine ont été restaurés lorsque possible."
                )
            except Exception as restore_error:
                say(
                    f"ATTENTION - restauration incomplète : {restore_error}"
                )
        say(f"Consultez {LOG.name}.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
