from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import quote

from nicegui import run, ui

from recipes_extras import get_recipe_extras
from recipes_pdf import build_recipe_pdf
from recipes_photo_data import get_recipe_photo


REPORT_DIRECTORY = Path(tempfile.gettempdir()) / "jf_apps_recipe_reports"


def _safe_filename_part(value):
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
    return text.strip("_")[:80] or "recette"


def open_recipe_export_dialog(*, user_id, recipe):
    from db import get_recipe_ingredients

    extras = get_recipe_extras(user_id, recipe["id"])
    ingredients = get_recipe_ingredients(user_id, recipe["id"])
    try:
        photo = get_recipe_photo(user_id, recipe["id"])
    except Exception:
        photo = None

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-2xl p-5"):
            ui.label("Imprimer / PDF / courriel").classes("text-xl font-bold")
            ui.label(recipe["name"]).classes("text-sm text-gray-600")

            include_photo = ui.checkbox(
                "Inclure la photo",
                value=bool(photo),
            )
            include_photo.set_enabled(bool(photo))
            include_nutrition = ui.checkbox(
                "Inclure les valeurs nutritives",
                value=bool(extras.get("nutrition")),
            )
            include_nutrition.set_enabled(bool(extras.get("nutrition")))
            include_metric = ui.checkbox(
                "Afficher aussi les conversions en grammes",
                value=bool(extras.get("ingredient_metrics")),
            )
            include_metric.set_enabled(bool(extras.get("ingredient_metrics")))

            recipient = ui.input(
                label="Courriel du destinataire (facultatif)",
                placeholder="Ex. famille@exemple.ca",
            ).props("type=email autocomplete=email").classes("w-full")

            async def generate_pdf():
                try:
                    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
                    filename = (
                        "recette_"
                        + _safe_filename_part(recipe["name"])
                        + ".pdf"
                    )
                    output = REPORT_DIRECTORY / (
                        f"{user_id}_{int(time.time() * 1000)}_{filename}"
                    )
                    await run.io_bound(
                        build_recipe_pdf,
                        recipe=recipe,
                        ingredients=ingredients,
                        extras=extras,
                        output_path=output,
                        photo=photo,
                        include_photo=bool(include_photo.value),
                        include_nutrition=bool(include_nutrition.value),
                        include_metric=bool(include_metric.value),
                    )
                    ui.download(str(output), filename=filename)
                    ui.notify(
                        "Le PDF est prêt. Ouvrez-le pour l’imprimer.",
                        type="positive",
                    )
                except Exception:
                    ui.notify(
                        "Le PDF n’a pas pu être produit.",
                        type="negative",
                    )

            async def prepare_email():
                subject = f"Recette — {recipe['name']}"
                source = extras.get("source") or {}
                body = (
                    "Bonjour,\n\n"
                    f"Voici la recette « {recipe['name']} ».\n\n"
                    f"Portions : {recipe.get('servings') or 1}\n"
                )
                if source.get("url"):
                    body += f"Source : {source['url']}\n"
                body += (
                    "\nLe PDF généré par JF Apps doit être joint "
                    "manuellement à ce courriel.\n"
                )
                mailto = (
                    f"mailto:{quote(str(recipient.value or '').strip())}"
                    f"?subject={quote(subject)}"
                    f"&body={quote(body)}"
                )
                await ui.run_javascript(
                    "window.location.href = " + json.dumps(mailto) + ";",
                    timeout=5.0,
                )

            with ui.row().classes("w-full gap-2 flex-wrap mt-3"):
                ui.button(
                    "Générer le PDF",
                    icon="picture_as_pdf",
                    on_click=generate_pdf,
                ).props("color=primary")
                ui.button(
                    "Préparer le courriel",
                    icon="email",
                    on_click=prepare_email,
                ).props("outline color=primary")

            ui.label(
                "Pour l’impression, ouvrez le PDF généré puis utilisez la commande "
                "Imprimer de votre appareil. Les navigateurs ne permettent pas "
                "d’ajouter automatiquement une pièce jointe à un courriel : "
                "joignez le PDF après l’ouverture du message préparé."
            ).classes("text-xs text-gray-500 whitespace-normal")

            with ui.row().classes("w-full justify-end mt-2"):
                ui.button("Fermer", on_click=dialog.close).props("flat")

    dialog.open()
