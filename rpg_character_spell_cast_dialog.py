"""Dialogue réutilisable de lancement guidé d'un sort — JDR Phase 15B."""
from __future__ import annotations

from rpg_character_spell_casting import (
    SpellCastError,
    build_cast_reference,
    spontaneous_cast_options,
)


def open_spell_cast_dialog(
    *,
    ui,
    user_id,
    character,
    profile,
    prepared_spell,
    cast_prepared_spell,
    catalog_by_key,
    notify_error,
    on_cast=None,
):
    """Affiche la référence du sort puis consomme l'emplacement sur confirmation."""
    row = dict(prepared_spell or {})
    domain = row.get("domain_source")
    try:
        catalog = catalog_by_key(
            max_spell_level=max(9, int(row.get("spell_level") or 0)),
            domains=[domain] if domain else [],
        )
    except Exception:
        catalog = {}
    catalog_entry = dict(catalog.get(str(row.get("catalog_key") or "")) or {})

    conversions = spontaneous_cast_options(profile, row)
    use_options = {"": f"Lancer {row.get('spell_name') or 'le sort préparé'}"}
    for option in conversions:
        use_options[option["key"]] = (
            f"Conversion spontanée — {option['name']} "
            f"(niveau {option['spell_level']})"
        )

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-3xl p-5 max-h-[92vh] overflow-auto"):
            with ui.row().classes("w-full items-start justify-between gap-3"):
                with ui.column().classes("gap-0"):
                    ui.label("Lancer un sort").classes("text-2xl font-bold")
                    ui.label(
                        "Vérifiez l’effet de référence avant de consommer l’emplacement."
                    ).classes("text-sm jf-muted")
                ui.button(icon="close", on_click=dialog.close).props("flat round")

            use_input = None
            if conversions:
                use_input = ui.select(
                    use_options,
                    label="Utilisation de l’emplacement",
                    value="",
                ).props("options-dense").classes("w-full mt-2")

            @ui.refreshable
            def render_reference():
                spontaneous_key = str(use_input.value or "") if use_input else ""
                try:
                    reference = build_cast_reference(
                        character=character,
                        profile=profile,
                        prepared_row=row,
                        catalog_entry=catalog_entry,
                        spontaneous_key=spontaneous_key or None,
                    )
                except SpellCastError as error:
                    ui.label(str(error)).classes("text-negative font-bold mt-3")
                    return

                with ui.card().classes("w-full p-4 mt-3"):
                    with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
                        ui.label(reference["name"]).classes("text-xl font-bold")
                        if reference["reusable"]:
                            ui.badge("Oraison — réutilisable", color="primary").classes(
                                "text-sm font-bold px-2 py-1"
                            )
                        else:
                            ui.badge(
                                f"Restant après : {reference['remaining_after']}"
                            ).props(
                                "color=positive" if reference["remaining_after"] > 0 else "color=negative"
                            ).classes("text-sm font-bold px-2 py-1")

                    if reference["is_spontaneous"]:
                        ui.label(
                            f"Conversion de : {reference['source_spell_name']} "
                            f"(emplacement niveau {reference['source_spell_level']})"
                        ).classes("text-xs text-primary font-bold")

                    with ui.element("div").classes("jf-rpg-grid mt-3"):
                        for label, value in (
                            ("Niveau du sort", reference["spell_level"]),
                            ("Niveau de lanceur", reference["caster_level"]),
                            ("DD de référence", reference["save_dc"]),
                            ("Portée", reference["range_text"] or "À vérifier"),
                            ("Cible / zone", reference["target_text"] or "À vérifier"),
                            ("Durée", reference["duration_text"] or "À vérifier"),
                        ):
                            with ui.column().classes("gap-0"):
                                ui.label(label).classes("text-xs jf-muted")
                                ui.label(str(value)).classes("font-bold")

                    if reference["saving_throw_text"]:
                        ui.label(
                            "Jet de sauvegarde : " + reference["saving_throw_text"]
                        ).classes("text-sm mt-2")
                    if reference["roll_text"]:
                        ui.label(
                            "Jet / formule : " + reference["roll_text"]
                        ).classes("text-sm text-primary font-bold mt-2")
                    if reference["summary"]:
                        ui.label(reference["summary"]).classes("text-sm mt-2 whitespace-pre-wrap")
                    if reference["notes"]:
                        ui.label("Notes : " + reference["notes"]).classes("text-sm jf-muted mt-2 whitespace-pre-wrap")
                    if reference["source_text"]:
                        ui.label("Source : " + reference["source_text"]).classes("text-xs jf-muted mt-2")

                ui.label(
                    "Phase 15B : le lancement consomme l’emplacement, mais n’applique pas "
                    "automatiquement les dégâts, soins ou états à une cible."
                ).classes("text-xs jf-muted mt-2")

            if use_input:
                use_input.on_value_change(lambda _event=None: render_reference.refresh())
            render_reference()

            def confirm_cast():
                spontaneous_key = str(use_input.value or "") if use_input else ""
                try:
                    reference = build_cast_reference(
                        character=character,
                        profile=profile,
                        prepared_row=row,
                        catalog_entry=catalog_entry,
                        spontaneous_key=spontaneous_key or None,
                    )
                    result = cast_prepared_spell(
                        user_id,
                        character["id"],
                        row["id"],
                    )
                except Exception as error:
                    notify_error(error, "Le sort n’a pas pu être lancé.")
                    return

                dialog.close()
                if callable(on_cast):
                    on_cast()
                if result.get("reusable"):
                    message = f"{reference['name']} lancé — oraison réutilisable."
                else:
                    message = (
                        f"{reference['name']} lancé — "
                        f"{result.get('remaining', reference['remaining_after'])} restant(s)."
                    )
                ui.notify(message, type="positive")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Annuler", on_click=dialog.close).props("flat")
                ui.button(
                    "Confirmer le lancement",
                    icon="auto_fix_high",
                    on_click=confirm_cast,
                ).props("color=primary")
    dialog.open()
