"""Panneau Importer/Exporter avec interface et services injectés."""
from datetime import date
from pathlib import Path
import tempfile


def build_import_export_panel(
    *,
    ui,
    user_id,
    export_tab,
    prepare_finance_import,
    import_finance_rows,
    export_finances,
    _signed,
    refresh_all,
) -> None:
    # IMPORTER ET EXPORTER
    with ui.tab_panel(export_tab).classes("px-0"):
        with ui.card().classes("w-full max-w-3xl p-4"):
            ui.label("Importer des transactions").classes(
                "text-xl font-bold"
            )
            ui.label(
                "Formats reconnus : CSV de Spendee, CSV de JF Apps "
                "et sauvegarde JSON de JF Apps. Une prévisualisation "
                "est toujours affichée avant l’importation."
            ).classes("text-sm jf-muted")

            async def receive_import(event):
                try:
                    text = await event.file.text()
                    filename = getattr(event.file, "name", "import.csv")
                    preview = prepare_finance_import(
                        user_id,
                        filename,
                        text,
                    )
                except Exception as error:
                    ui.notify(str(error), type="negative")
                    return

                with ui.dialog() as dialog:
                    with ui.card().classes("w-full max-w-4xl p-4"):
                        ui.label("Prévisualisation de l’importation").classes(
                            "text-xl font-bold"
                        )
                        ui.label(
                            f"Format reconnu : {preview['format']}"
                        ).classes("text-sm jf-muted")

                        with ui.element("div").classes(
                            "jf-finance-summary-grid mt-2"
                        ):
                            for label, value in (
                                ("Valides", preview["valid_rows"]),
                                ("Déjà importées", preview["already_imported"]),
                                ("Doublons possibles", preview["possible_duplicates"]),
                            ):
                                with ui.element("div").classes(
                                    "jf-finance-summary"
                                ):
                                    ui.label(label).classes(
                                        "jf-finance-summary-label"
                                    )
                                    ui.label(str(value)).classes(
                                        "jf-finance-summary-value"
                                    )

                        ui.label(
                            (
                                "Catégories détectées : "
                                f"{len(preview['categories'])} — "
                                "Étiquettes détectées : "
                                f"{len(preview['tags'])} — "
                                "Modes de paiement détectés : "
                                f"{len(preview['payment_methods'])} — "
                                "Postes de budget détectés : "
                                f"{len(preview.get('budget_items') or [])}"
                            )
                        ).classes(
                            "text-xs jf-muted"
                        )

                        skip_possible = ui.checkbox(
                            "Ignorer les transactions identiques déjà présentes",
                            value=True,
                        ).classes("mt-2")

                        if preview["errors"]:
                            with ui.expansion(
                                f"Erreurs ignorées ({len(preview['errors'])})",
                                icon="warning",
                            ).classes("w-full"):
                                for message in preview["errors"][:30]:
                                    ui.label(message).classes(
                                        "text-xs text-negative"
                                    )

                        ui.label("Aperçu").classes("font-bold mt-2")
                        with ui.column().classes("w-full gap-1"):
                            visible_rows = [
                                row for row in preview["rows"]
                                if row.get("duplicate_reason") != "already_imported"
                            ][:8]
                            for row in visible_rows:
                                with ui.element("div").classes(
                                    "jf-finance-card"
                                ):
                                    with ui.row().classes(
                                        "w-full items-center justify-between gap-2"
                                    ):
                                        with ui.column().classes(
                                            "gap-0 min-w-0"
                                        ):
                                            ui.label(row["description"]).classes(
                                                "text-sm font-bold"
                                            )
                                            details = [
                                                row["transaction_date"].strftime("%d/%m/%Y"),
                                                row.get("category_name") or "Sans catégorie",
                                            ]
                                            if row.get("tag_names"):
                                                details.append(
                                                    " • ".join(row["tag_names"])
                                                )
                                            if row.get(
                                                "payment_method_name"
                                            ):
                                                details.append(
                                                    row[
                                                        "payment_method_name"
                                                    ]
                                                )
                                            ui.label(" — ".join(details)).classes(
                                                "text-xs jf-muted"
                                            )
                                        css = (
                                            "jf-finance-expense"
                                            if row["transaction_type"] == "expense"
                                            else "jf-finance-income"
                                        )
                                        ui.label(
                                            _signed(
                                                row["amount"],
                                                row["transaction_type"],
                                            )
                                        ).classes(f"text-sm font-bold {css}")

                        def confirm_import():
                            try:
                                result = import_finance_rows(
                                    user_id,
                                    preview["rows"],
                                    skip_possible_duplicates=(
                                        skip_possible.value
                                    ),
                                    budget_items=preview.get("budget_items") or [],
                                )
                            except Exception as error:
                                ui.notify(str(error), type="negative")
                                return

                            dialog.close()
                            message = (
                                f"Importation terminée : {result['imported']} ajoutée(s), "
                                f"{result['skipped']} ignorée(s), "
                                f"{result['categories_created']} catégorie(s) créée(s), "
                                f"{result['tags_created']} étiquette(s) créée(s), "
                                f"{result['payment_methods_created']} "
                                "mode(s) de paiement créé(s), "
                                f"{result.get('budget_items_imported', 0)} "
                                "poste(s) de budget restauré(s)."
                            )
                            ui.notify(message, type="positive", timeout=10000)
                            if result["failures"]:
                                ui.notify(
                                    f"{len(result['failures'])} ligne(s) n’ont pas pu être importées.",
                                    type="warning",
                                    timeout=10000,
                                )
                            refresh_all()

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-3"
                        ):
                            ui.button(
                                "Annuler",
                                on_click=dialog.close,
                            ).props("flat")
                            ui.button(
                                "Importer",
                                icon="upload",
                                on_click=confirm_import,
                            ).props("color=primary")
                dialog.open()

            ui.upload(
                label="Choisir un fichier CSV ou JSON",
                on_upload=receive_import,
                auto_upload=True,
                max_files=1,
            ).props(
                "accept=.csv,.json,text/csv,application/json"
            ).classes("w-full mt-3")

        with ui.card().classes("w-full max-w-3xl p-4 mt-3"):
            ui.label("Exporter les données").classes("text-xl font-bold")
            ui.label(
                "Le CSV convient à Excel. Le JSON constitue "
                "une sauvegarde complète de sécurité. Les modes "
                "de paiement, les statuts de conciliation, l’indicateur Hors budget, "
                "les postes du budget global et les clés d’importation sont conservés."
            ).classes("text-sm jf-muted")

            def do_export(kind):
                try:
                    csv_bytes, json_bytes = export_finances(user_id)
                    content = csv_bytes if kind == "csv" else json_bytes
                    filename = f"finances_{date.today().isoformat()}.{kind}"
                    path = Path(tempfile.gettempdir()) / (
                        f"{user_id}_{filename}"
                    )
                    path.write_bytes(content)
                    ui.download(str(path), filename=filename)
                except Exception as error:
                    ui.notify(str(error), type="negative")

            with ui.row().classes("gap-2 flex-wrap"):
                ui.button(
                    "Exporter CSV",
                    icon="table_view",
                    on_click=lambda: do_export("csv"),
                ).props("outline color=primary")
                ui.button(
                    "Exporter JSON",
                    icon="data_object",
                    on_click=lambda: do_export("json"),
                ).props("outline color=primary")
