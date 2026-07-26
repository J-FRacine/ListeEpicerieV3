from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from nicegui import app, ui

from auth import get_current_user_id
from maintenance_data import (
    get_maintenance_families,
    get_maintenance_report,
)
from state import get_current_family_id


try:
    QUEBEC_TIME = ZoneInfo(
        "America/Toronto"
    )
except ZoneInfoNotFoundError:
    QUEBEC_TIME = timezone.utc


ENTITY_ICONS = {
    "Item": "inventory_2",
    "Catégorie": "category",
    "Magasin": "storefront",
}

TABLE_LABELS = {
    "families": "Familles",
    "family_members": "Accès aux familles",
    "users": "Utilisateurs",
    "categories": "Catégories",
    "stores": "Magasins",
    "items": "Items",
    "activity_log": "Historique",
}


def _format_integer(value):
    return f"{int(value or 0):,}".replace(
        ",",
        " ",
    )


def _format_bytes(value):
    size = float(value or 0)
    units = (
        "octets",
        "Ko",
        "Mo",
        "Go",
        "To",
    )

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "octets":
                return f"{int(size)} {unit}"
            return (
                f"{size:.1f} {unit}"
                .replace(".", ",")
            )
        size /= 1024

    return "0 octet"


def _format_time(value):
    if not isinstance(value, datetime):
        return ""

    return value.astimezone(
        QUEBEC_TIME
    ).strftime(
        "%Y-%m-%d à %H h %M"
    )


def _metric_card(
    icon,
    label,
    value,
    caption="",
):
    with ui.card().classes(
        "w-full p-4 min-h-[118px]"
    ):
        with ui.row().classes(
            "w-full items-start gap-3 flex-nowrap"
        ):
            ui.icon(icon).classes(
                "text-3xl text-primary shrink-0"
            )

            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label(label).classes(
                    "text-sm text-gray-500"
                )
                ui.label(
                    str(value)
                ).classes(
                    "text-2xl font-bold"
                )

                if caption:
                    ui.label(caption).classes(
                        "text-xs text-gray-500 "
                        "whitespace-normal"
                    )


def _empty_state(message):
    with ui.row().classes(
        "w-full items-center gap-2 "
        "rounded-lg bg-green-50 px-3 py-2"
    ):
        ui.icon("check_circle").classes(
            "text-positive text-xl"
        )
        ui.label(message).classes(
            "text-sm text-green-900"
        )


def _issue_card(
    *,
    title,
    subtitle="",
    details="",
    icon="warning_amber",
    icon_class="text-warning",
):
    with ui.card().classes(
        "w-full px-4 py-3 mt-2 shadow-none"
    ):
        with ui.row().classes(
            "w-full items-start gap-3 flex-nowrap"
        ):
            ui.icon(icon).classes(
                f"text-2xl {icon_class} shrink-0"
            )

            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label(title).classes(
                    "font-bold whitespace-normal"
                ).style(
                    "overflow-wrap:anywhere;"
                )

                if subtitle:
                    ui.label(subtitle).classes(
                        "text-sm text-gray-500 "
                        "whitespace-normal"
                    ).style(
                        "overflow-wrap:anywhere;"
                    )

                if details:
                    ui.label(details).classes(
                        "text-xs text-gray-500 "
                        "whitespace-normal mt-1"
                    ).style(
                        "overflow-wrap:anywhere;"
                    )


def _section_title(
    title,
    count,
    icon,
    severity="info",
):
    color = {
        "critical": "negative",
        "warning": "warning",
        "info": "primary",
        "ok": "positive",
    }.get(severity, "primary")

    with ui.row().classes(
        "items-center gap-2"
    ):
        ui.icon(icon).classes(
            f"text-{color} text-xl"
        )
        ui.label(title).classes(
            "font-bold"
        )
        ui.badge(
            str(count),
            color=color,
        )


def maintenance_panel():
    user_id = get_current_user_id()

    if user_id is None:
        return

    try:
        families = get_maintenance_families(
            user_id
        )
    except PermissionError as error:
        ui.label(str(error)).classes(
            "text-negative"
        )
        return
    except Exception as error:
        ui.label(
            "Impossible d’ouvrir le centre de maintenance : "
            f"{type(error).__name__}: {error}"
        ).classes("text-negative")
        return

    option_by_label = {
        "Toutes les familles": None,
    }

    for family in families:
        option_by_label[
            family["name"]
        ] = family["id"]

    valid_family_ids = {
        family["id"]
        for family in families
    }

    storage_key = (
        "maintenance_selected_family_id"
    )
    stored_value = app.storage.user.get(
        storage_key
    )
    current_family_id = (
        get_current_family_id()
    )

    if stored_value == "all":
        initial_family_id = None
    elif stored_value in valid_family_ids:
        initial_family_id = stored_value
    elif current_family_id in valid_family_ids:
        initial_family_id = current_family_id
    else:
        initial_family_id = None

    selected_state = {
        "family_id": initial_family_id,
    }

    selected_label = next(
        (
            label
            for label, family_id
            in option_by_label.items()
            if family_id == initial_family_id
        ),
        "Toutes les familles",
    )

    ui.label(
        "Centre de maintenance"
    ).classes("text-2xl font-bold")

    with ui.row().classes(
        "w-full items-center gap-2 "
        "rounded-xl bg-blue-50 px-4 py-3"
    ):
        ui.icon("visibility").classes(
            "text-primary text-2xl"
        )
        with ui.column().classes("gap-0"):
            ui.label(
                "Diagnostic en lecture seule"
            ).classes(
                "font-bold text-blue-950"
            )
            ui.label(
                "Cette première version n’effectue aucune "
                "modification dans PostgreSQL."
            ).classes(
                "text-sm text-blue-900"
            )

    family_select = ui.select(
        list(option_by_label.keys()),
        value=selected_label,
        label="Portée du diagnostic",
    ).classes("w-full")

    with ui.row().classes(
        "w-full justify-end gap-2"
    ):
        refresh_button = ui.button(
            "Actualiser",
            icon="refresh",
        ).props("flat color=primary")

    @ui.refreshable
    def render_report():
        try:
            report = get_maintenance_report(
                user_id,
                selected_state["family_id"],
            )
        except Exception as error:
            with ui.card().classes(
                "w-full p-5 border-l-4 "
                "border-negative"
            ):
                ui.label(
                    "Le diagnostic n’a pas pu être produit."
                ).classes(
                    "text-lg font-bold text-negative"
                )
                ui.label(
                    f"{type(error).__name__}: {error}"
                ).classes(
                    "text-sm text-gray-600"
                )
            return

        critical_count = report[
            "critical_count"
        ]
        warning_count = report[
            "warning_count"
        ]

        if critical_count > 0:
            status_icon = "error"
            status_class = (
                "border-negative bg-red-50"
            )
            status_title = (
                "Des anomalies importantes ont été détectées"
            )
            status_text = (
                f"{critical_count} anomalie(s) importante(s) "
                f"et {warning_count} avertissement(s)."
            )
        elif warning_count > 0:
            status_icon = "warning"
            status_class = (
                "border-warning bg-orange-50"
            )
            status_title = (
                "La base est fonctionnelle, avec des éléments à examiner"
            )
            status_text = (
                f"{warning_count} avertissement(s) ou "
                "possibilité(s) de nettoyage."
            )
        else:
            status_icon = "verified"
            status_class = (
                "border-positive bg-green-50"
            )
            status_title = (
                "Aucune anomalie détectée"
            )
            status_text = (
                "Les contrôles effectués n’ont trouvé "
                "aucun problème."
            )

        with ui.card().classes(
            f"w-full p-5 border-l-4 {status_class}"
        ):
            with ui.row().classes(
                "w-full items-start gap-3 flex-nowrap"
            ):
                ui.icon(status_icon).classes(
                    "text-3xl shrink-0"
                )
                with ui.column().classes(
                    "gap-0 grow min-w-0"
                ):
                    ui.label(status_title).classes(
                        "text-lg font-bold"
                    )
                    ui.label(status_text).classes(
                        "text-sm text-gray-700"
                    )
                    ui.label(
                        "Diagnostic généré le "
                        + _format_time(
                            report["generated_at"]
                        )
                    ).classes(
                        "text-xs text-gray-500 mt-1"
                    )

        scope_name = (
            report["selected_family_name"]
            or "Toutes les familles"
        )
        ui.label(
            f"Résumé — {scope_name}"
        ).classes(
            "text-xl font-bold mt-1"
        )

        counts = report["scope_counts"]
        with ui.element("div").classes(
            "w-full grid grid-cols-2 "
            "md:grid-cols-4 gap-3"
        ):
            _metric_card(
                "inventory_2",
                "Items actifs",
                _format_integer(
                    counts["items_active"]
                ),
                (
                    f"{_format_integer(counts['items_needed'])} "
                    "dans les besoins"
                ),
            )
            _metric_card(
                "category",
                "Catégories actives",
                _format_integer(
                    counts["categories_active"]
                ),
                (
                    f"{_format_integer(counts['categories_deleted'])} "
                    "dans la corbeille"
                ),
            )
            _metric_card(
                "storefront",
                "Magasins actifs",
                _format_integer(
                    counts["stores_active"]
                ),
                (
                    f"{_format_integer(counts['stores_deleted'])} "
                    "dans la corbeille"
                ),
            )
            _metric_card(
                "history",
                "Actions enregistrées",
                _format_integer(
                    counts["activity_entries"]
                ),
                (
                    f"{_format_integer(counts['items_deleted'])} "
                    "item(s) dans la corbeille"
                ),
            )

        if report["selected_family_id"] is None:
            global_counts = report[
                "global_counts"
            ]
            ui.label(
                "Portail complet"
            ).classes(
                "text-xl font-bold mt-2"
            )

            with ui.element("div").classes(
                "w-full grid grid-cols-2 "
                "md:grid-cols-4 gap-3"
            ):
                _metric_card(
                    "groups",
                    "Familles",
                    _format_integer(
                        global_counts[
                            "families_total"
                        ]
                    ),
                )
                _metric_card(
                    "person",
                    "Utilisateurs actifs",
                    _format_integer(
                        global_counts[
                            "users_active"
                        ]
                    ),
                    (
                        f"{_format_integer(global_counts['users_inactive'])} "
                        "inactif(s)"
                    ),
                )
                _metric_card(
                    "admin_panel_settings",
                    "Administrateurs actifs",
                    _format_integer(
                        global_counts[
                            "administrators_active"
                        ]
                    ),
                )
                _metric_card(
                    "group_add",
                    "Accès aux familles",
                    _format_integer(
                        global_counts[
                            "memberships_total"
                        ]
                    ),
                )

        invalid_items = report[
            "invalid_items"
        ]
        duplicate_references = report[
            "duplicate_reference_names"
        ]
        integrity_count = (
            len(invalid_items)
            + len(
                duplicate_references[
                    "categories"
                ]
            )
            + len(
                duplicate_references[
                    "stores"
                ]
            )
        )

        with ui.expansion(
            text="Intégrité des références",
            caption=(
                f"{integrity_count} anomalie(s)"
                if integrity_count
                else "Aucune anomalie"
            ),
            icon="shield",
            value=integrity_count > 0,
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200"
        ):
            _section_title(
                "Items invalides",
                len(invalid_items),
                "broken_image",
                (
                    "critical"
                    if invalid_items
                    else "ok"
                ),
            )

            if not invalid_items:
                _empty_state(
                    "Tous les items actifs sont liés à une "
                    "catégorie et à un magasin valides."
                )
            else:
                for item in invalid_items:
                    _issue_card(
                        title=(
                            item["name"]
                            or f"Item #{item['id']}"
                        ),
                        subtitle=(
                            f"{item['family_name']} · "
                            f"item #{item['id']}"
                        ),
                        details="; ".join(
                            item["issues"]
                        ),
                        icon="error",
                        icon_class="text-negative",
                    )

            for label, rows, icon in (
                (
                    "Catégories actives en double",
                    duplicate_references[
                        "categories"
                    ],
                    "category",
                ),
                (
                    "Magasins actifs en double",
                    duplicate_references[
                        "stores"
                    ],
                    "storefront",
                ),
            ):
                ui.separator().classes("my-3")
                _section_title(
                    label,
                    len(rows),
                    icon,
                    (
                        "critical"
                        if rows
                        else "ok"
                    ),
                )
                if not rows:
                    _empty_state(
                        "Aucun nom actif en double."
                    )
                else:
                    for row in rows:
                        _issue_card(
                            title=row[
                                "normalized_name"
                            ],
                            subtitle=row[
                                "family_name"
                            ],
                            details=row["entries"],
                            icon=icon,
                            icon_class="text-negative",
                        )

        duplicates = report[
            "duplicate_items"
        ]
        duplicate_count = (
            len(duplicates["exact"])
            + len(duplicates["probable"])
            + len(
                duplicates["cross_location"]
            )
        )

        with ui.expansion(
            text="Doublons d’items",
            caption=(
                f"{duplicate_count} groupe(s) à examiner"
                if duplicate_count
                else "Aucun doublon détecté"
            ),
            icon="content_copy",
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200"
        ):
            sections = (
                (
                    "Doublons exacts au même emplacement",
                    duplicates["exact"],
                    "content_copy",
                    "warning",
                ),
                (
                    "Doublons probables",
                    duplicates["probable"],
                    "rule",
                    "warning",
                ),
                (
                    "Même nom à plusieurs emplacements",
                    duplicates[
                        "cross_location"
                    ],
                    "multiple_stop",
                    "info",
                ),
            )

            for index, (
                label,
                rows,
                icon,
                severity,
            ) in enumerate(sections):
                if index:
                    ui.separator().classes(
                        "my-3"
                    )

                _section_title(
                    label,
                    len(rows),
                    icon,
                    (
                        severity
                        if rows
                        else "ok"
                    ),
                )

                if not rows:
                    _empty_state(
                        "Aucun groupe dans cette catégorie."
                    )
                    continue

                for row in rows:
                    if "entries" in row:
                        title = row["entries"]
                        subtitle = (
                            f"{row['family_name']} · "
                            f"{row['store_name']} · "
                            f"{row['category_name']}"
                        )
                        details = (
                            f"{row['item_count']} items"
                        )
                    else:
                        title = row[
                            "normalized_name"
                        ]
                        subtitle = row[
                            "family_name"
                        ]
                        details = (
                            f"{row['item_count']} items dans "
                            f"{row['location_count']} emplacements : "
                            f"{row['locations']}"
                        )

                    _issue_card(
                        title=title,
                        subtitle=subtitle,
                        details=details,
                        icon=icon,
                    )

        unused = report[
            "unused_entries"
        ]
        unused_count = (
            len(unused["categories"])
            + len(unused["stores"])
        )

        with ui.expansion(
            text="Éléments inutilisés",
            caption=(
                f"{unused_count} élément(s)"
                if unused_count
                else "Aucun élément inutilisé"
            ),
            icon="inventory",
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200"
        ):
            for index, (
                label,
                rows,
                icon,
            ) in enumerate(
                (
                    (
                        "Catégories sans item actif",
                        unused["categories"],
                        "category",
                    ),
                    (
                        "Magasins sans item actif",
                        unused["stores"],
                        "storefront",
                    ),
                )
            ):
                if index:
                    ui.separator().classes(
                        "my-3"
                    )

                _section_title(
                    label,
                    len(rows),
                    icon,
                    (
                        "warning"
                        if rows
                        else "ok"
                    ),
                )

                if not rows:
                    _empty_state(
                        "Aucun élément inutilisé."
                    )
                else:
                    for row in rows:
                        _issue_card(
                            title=row["name"],
                            subtitle=(
                                f"{row['family_name']} · "
                                f"identifiant #{row['id']}"
                            ),
                            icon=icon,
                        )

        naming_issues = report[
            "naming_issues"
        ]

        with ui.expansion(
            text="Qualité des noms",
            caption=(
                f"{len(naming_issues)} élément(s) à nettoyer"
                if naming_issues
                else "Noms uniformes"
            ),
            icon="spellcheck",
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200"
        ):
            if not naming_issues:
                _empty_state(
                    "Aucun nom vide ni espace superflu détecté."
                )
            else:
                for row in naming_issues:
                    _issue_card(
                        title=(
                            row["name"]
                            or f"{row['entity_type']} #{row['id']}"
                        ),
                        subtitle=(
                            f"{row['family_name']} · "
                            f"{row['entity_type']} #{row['id']}"
                        ),
                        details="; ".join(
                            row["issues"]
                        ),
                        icon=ENTITY_ICONS.get(
                            row["entity_type"],
                            "edit_note",
                        ),
                    )

        expired_trash = report[
            "expired_trash"
        ]

        with ui.expansion(
            text="Corbeille expirée",
            caption=(
                f"{len(expired_trash)} élément(s) de plus de 30 jours"
                if expired_trash
                else "Aucun élément expiré"
            ),
            icon="delete_sweep",
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200"
        ):
            if not expired_trash:
                _empty_state(
                    "Aucun élément supprimé depuis plus de 30 jours."
                )
            else:
                ui.label(
                    "Ces éléments sont encore conservés, souvent "
                    "parce qu’une référence les utilise toujours."
                ).classes(
                    "text-sm text-gray-500"
                )

                for row in expired_trash:
                    _issue_card(
                        title=row["name"],
                        subtitle=(
                            f"{row['family_name']} · "
                            f"{row['entity_type']} #{row['id']}"
                        ),
                        details=(
                            "Supprimé le "
                            + _format_time(
                                row["deleted_at"]
                            )
                        ),
                        icon="delete_clock",
                    )

        family_issues = report[
            "family_access_issues"
        ]

        with ui.expansion(
            text="Familles et accès",
            caption=(
                f"{len(family_issues)} famille(s) à examiner"
                if family_issues
                else "Accès cohérents"
            ),
            icon="groups",
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200"
        ):
            if not family_issues:
                _empty_state(
                    "Chaque famille possède un propriétaire "
                    "et au moins un membre actif."
                )
            else:
                for row in family_issues:
                    _issue_card(
                        title=row["name"],
                        subtitle=(
                            f"{row['active_members']} membre(s) actif(s) · "
                            f"{row['active_owners']} propriétaire(s) actif(s)"
                        ),
                        details="; ".join(
                            row["issues"]
                        ),
                        icon="group_off",
                    )

        sizes = report[
            "database_sizes"
        ]

        with ui.expansion(
            text="Espace occupé",
            caption=(
                "Base complète : "
                + _format_bytes(
                    sizes["database_bytes"]
                )
            ),
            icon="database",
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200"
        ):
            ui.label(
                "La taille comprend les tables, les index et "
                "l’espace interne géré par PostgreSQL."
            ).classes(
                "text-sm text-gray-500"
            )

            for table in sizes["tables"]:
                with ui.row().classes(
                    "w-full items-center justify-between "
                    "gap-3 border-b border-gray-100 py-2"
                ):
                    ui.label(
                        TABLE_LABELS.get(
                            table["table_name"],
                            table["table_name"],
                        )
                    ).classes("font-medium")
                    ui.label(
                        _format_bytes(
                            table["total_bytes"]
                        )
                    ).classes(
                        "text-sm text-gray-500"
                    )

        ui.label(
            "Cette page détecte les anomalies; les outils de "
            "fusion et de réparation seront ajoutés dans une "
            "phase distincte avec confirmation."
        ).classes(
            "text-xs text-gray-500 text-center "
            "w-full mt-2"
        )

    def family_changed(event):
        selected_family_id = option_by_label.get(
            event.value
        )
        selected_state[
            "family_id"
        ] = selected_family_id
        app.storage.user[
            storage_key
        ] = (
            selected_family_id
            if selected_family_id is not None
            else "all"
        )
        render_report.refresh()

    family_select.on_value_change(
        family_changed
    )
    refresh_button.on(
        "click",
        render_report.refresh,
    )

    render_report()
