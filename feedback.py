from __future__ import annotations

from datetime import datetime

from nicegui import ui

from app_access import (
    get_user_app_access,
)
from feedback_data import (
    CLOSED_FEEDBACK_STATUSES,
    FEEDBACK_APP_LABELS,
    FEEDBACK_STATUS_LABELS,
    count_feedback_attention,
    create_feedback,
    get_feedback_for_admin,
    get_user_feedback,
    list_feedback_events,
    list_feedback_for_admin,
    list_user_feedback,
    mark_feedback_manager_read,
    mark_feedback_user_read,
    update_feedback_by_manager,
    update_user_feedback,
)


FEEDBACK_CSS = r"""
.jf-feedback-private {
    width: 100%;
    padding: 0.75rem 0.9rem;
    border-left: 4px solid #218f5c;
    border-radius: 12px;
    background: rgba(33, 143, 92, 0.08);
}

.jf-feedback-filter {
    display: grid;
    grid-template-columns:
        minmax(10rem, 0.8fr)
        minmax(10rem, 0.8fr)
        minmax(14rem, 1.4fr)
        auto;
    align-items: end;
    gap: 0.65rem;
    width: 100%;
}

.jf-feedback-list {
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    width: 100%;
}

.jf-feedback-card {
    width: 100%;
    padding: 0.8rem 0.9rem;
    border: 1px solid var(--jf-border);
    border-radius: 14px;
    background: var(--jf-surface);
}

.jf-feedback-card-unread {
    border-left: 5px solid var(--jf-gold);
}

.jf-feedback-subject {
    color: var(--jf-navy);
    font-size: 1rem;
    font-weight: 800;
}

.body--dark .jf-feedback-subject {
    color: #dceaf6;
}

.jf-feedback-meta {
    color: var(--jf-muted);
    font-size: 0.76rem;
}

.jf-feedback-status {
    display: inline-flex;
    width: fit-content;
    padding: 0.18rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 800;
    background: var(--jf-blue-soft);
}

.jf-feedback-status-new {
    color: #8c4c0b;
    background: rgba(191, 120, 18, 0.16);
}

.jf-feedback-status-study {
    color: #174f7b;
    background: rgba(42, 117, 167, 0.14);
}

.jf-feedback-status-planned {
    color: #5f408d;
    background: rgba(113, 74, 165, 0.14);
}

.jf-feedback-status-in-progress {
    color: #1b6173;
    background: rgba(30, 132, 151, 0.14);
}

.jf-feedback-status-completed {
    color: #156c47;
    background: rgba(33, 145, 92, 0.14);
}

.jf-feedback-status-rejected {
    color: #8b3440;
    background: rgba(183, 64, 82, 0.13);
}

.jf-feedback-unread {
    display: inline-flex;
    width: fit-content;
    padding: 0.17rem 0.46rem;
    border-radius: 999px;
    color: #70480c;
    background: rgba(189, 149, 85, 0.19);
    font-size: 0.7rem;
    font-weight: 800;
}

.jf-feedback-detail {
    width: 100%;
    padding: 0.75rem 0.85rem;
    border-radius: 12px;
    white-space: pre-wrap;
    background: rgba(34, 70, 122, 0.055);
}

.jf-feedback-reply {
    width: 100%;
    padding: 0.8rem 0.9rem;
    border-left: 4px solid var(--jf-blue);
    border-radius: 12px;
    white-space: pre-wrap;
    background: var(--jf-blue-soft);
}

.jf-feedback-event {
    width: 100%;
    padding: 0.45rem 0.6rem;
    border-left: 3px solid var(--jf-border);
    font-size: 0.78rem;
}

@media (max-width: 760px) {
    .jf-feedback-filter {
        grid-template-columns: 1fr 1fr;
    }

    .jf-feedback-filter-search {
        grid-column: 1 / -1;
    }

    .jf-feedback-filter-button {
        justify-self: start;
    }
}

@media (max-width: 480px) {
    .jf-feedback-filter {
        grid-template-columns: 1fr;
    }

    .jf-feedback-filter-search {
        grid-column: auto;
    }
}
"""

ui.add_css(
    FEEDBACK_CSS,
    shared=True,
)


def _date_time_text(
    value,
) -> str:
    if not value:
        return "—"

    if isinstance(
        value,
        datetime,
    ):
        return value.strftime(
            "%d/%m/%Y à %H:%M"
        )

    return str(value)


def _status_class(
    status,
) -> str:
    return (
        "jf-feedback-status "
        "jf-feedback-status-"
        + str(
            status
            or "new"
        ).replace(
            "_",
            "-"
        )
    )


def _app_options_for_user(
    current_user,
):
    if current_user[
        "is_admin"
    ]:
        return dict(
            FEEDBACK_APP_LABELS
        )

    allowed = set(
        get_user_app_access(
            current_user[
                "id"
            ]
        )
    )

    options = {
        "portal": (
            FEEDBACK_APP_LABELS[
                "portal"
            ]
        ),
    }

    for app_key in (
        "grocery",
        "blood_pressure",
        "finances",
        "rpg",
    ):
        if app_key in allowed:
            options[
                app_key
            ] = (
                FEEDBACK_APP_LABELS[
                    app_key
                ]
            )

    options[
        "help"
    ] = FEEDBACK_APP_LABELS[
        "help"
    ]
    options[
        "other"
    ] = FEEDBACK_APP_LABELS[
        "other"
    ]

    return options


def _render_status(
    status,
):
    ui.label(
        FEEDBACK_STATUS_LABELS.get(
            status,
            status,
        )
    ).classes(
        _status_class(
            status
        )
    )


def _render_events(
    feedback_id,
):
    events = list_feedback_events(
        feedback_id
    )

    if not events:
        return

    ui.label(
        "Historique du suivi"
    ).classes(
        "font-bold mt-3"
    )

    with ui.column().classes(
        "w-full gap-1"
    ):
        for event in events:
            actor = (
                event[
                    "actor_name"
                ]
                or "Compte supprimé"
            )
            with ui.element(
                "div"
            ).classes(
                "jf-feedback-event"
            ):
                ui.label(
                    event[
                        "summary"
                    ]
                )
                ui.label(
                    (
                        f"{actor} — "
                        f"{_date_time_text(event['created_at'])}"
                    )
                ).classes(
                    "text-xs jf-muted"
                )


def feedback_panel(
    current_user,
    *,
    initial_section=None,
):
    user_id = current_user[
        "id"
    ]
    app_options = (
        _app_options_for_user(
            current_user
        )
    )

    with ui.row().classes(
        "w-full items-center "
        "justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes(
            "gap-0"
        ):
            ui.label(
                "Commentaires et suggestions"
            ).classes(
                "text-2xl font-bold"
            )
            ui.label(
                "Signalez un problème, proposez une amélioration "
                "ou consultez les réponses reçues."
            ).classes(
                "text-sm jf-muted"
            )

        if current_user[
            "is_admin"
        ]:
            try:
                attention_count = (
                    count_feedback_attention()
                )
            except Exception:
                attention_count = 0

            if attention_count:
                ui.label(
                    (
                        f"{attention_count} "
                        "à examiner"
                    )
                ).classes(
                    "jf-feedback-unread"
                )

    with ui.element("div").classes(
        "jf-feedback-private"
    ):
        with ui.row().classes(
            "items-start gap-2 flex-nowrap"
        ):
            ui.icon(
                "lock"
            ).classes(
                "text-xl text-positive shrink-0"
            )
            ui.label(
                "Un utilisateur voit seulement ses propres commentaires "
                "et les réponses qui lui sont destinées. "
                "Les administrateurs peuvent gérer tous les commentaires."
            ).classes(
                "text-sm"
            )

    with ui.tabs().classes(
        "w-full"
    ) as tabs:
        my_tab = ui.tab(
            "Mes commentaires",
            icon="forum",
        )
        new_tab = ui.tab(
            "Nouveau",
            icon="add_comment",
        )
        admin_tab = None

        if current_user[
            "is_admin"
        ]:
            admin_tab = ui.tab(
                "Gestion",
                icon="admin_panel_settings",
            )

    normalized_section = str(
        initial_section
        or ""
    ).strip().lower()

    initial_tab = my_tab

    if normalized_section in {
        "nouveau",
        "new",
        "creer",
        "créer",
    }:
        initial_tab = new_tab
    elif (
        admin_tab is not None
        and normalized_section
        in {
            "gestion",
            "admin",
            "manager",
        }
    ):
        initial_tab = admin_tab

    with ui.tab_panels(
        tabs,
        value=initial_tab,
    ).classes(
        "w-full bg-transparent"
    ):
        # -------------------------------------------------
        # MES COMMENTAIRES
        # -------------------------------------------------
        with ui.tab_panel(
            my_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full p-4"
            ):
                with ui.element(
                    "div"
                ).classes(
                    "jf-feedback-filter"
                ):
                    own_status_filter = ui.select(
                        {
                            "": "Tous les statuts",
                            **FEEDBACK_STATUS_LABELS,
                        },
                        label="Statut",
                        value="",
                    ).props(
                        "dense outlined options-dense"
                    )

                    own_app_filter = ui.select(
                        {
                            "": "Toutes les applications",
                            **app_options,
                        },
                        label="Application",
                        value="",
                    ).props(
                        "dense outlined options-dense"
                    )

                    own_search = ui.input(
                        label="Rechercher",
                        placeholder="Sujet ou texte",
                    ).props(
                        "dense outlined clearable"
                    ).classes(
                        "jf-feedback-filter-search"
                    )

                    own_refresh_button = ui.button(
                        "Actualiser",
                        icon="refresh",
                    ).props(
                        "outline dense color=primary"
                    ).classes(
                        "jf-feedback-filter-button"
                    )

            own_list = ui.column().classes(
                "jf-feedback-list"
            )

            def open_user_detail(
                feedback_id,
            ):
                try:
                    feedback = (
                        get_user_feedback(
                            user_id,
                            feedback_id,
                        )
                    )
                    mark_feedback_user_read(
                        user_id,
                        feedback_id,
                    )
                except Exception as error:
                    ui.notify(
                        str(error),
                        type="negative",
                    )
                    return

                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-3xl p-5"
                    ):
                        with ui.row().classes(
                            "w-full items-start "
                            "justify-between gap-2"
                        ):
                            with ui.column().classes(
                                "gap-1"
                            ):
                                ui.label(
                                    feedback[
                                        "subject"
                                    ]
                                ).classes(
                                    "text-xl font-bold"
                                )
                                ui.label(
                                    (
                                        FEEDBACK_APP_LABELS.get(
                                            feedback[
                                                "app_key"
                                            ],
                                            feedback[
                                                "app_key"
                                            ],
                                        )
                                        + " — créé le "
                                        + _date_time_text(
                                            feedback[
                                                "created_at"
                                            ]
                                        )
                                    )
                                ).classes(
                                    "text-xs jf-muted"
                                )

                            _render_status(
                                feedback[
                                    "status"
                                ]
                            )

                        ui.label(
                            "Votre commentaire"
                        ).classes(
                            "font-bold mt-2"
                        )
                        ui.label(
                            feedback[
                                "detail"
                            ]
                        ).classes(
                            "jf-feedback-detail"
                        )

                        ui.label(
                            "Réponse du gestionnaire"
                        ).classes(
                            "font-bold mt-3"
                        )

                        if feedback[
                            "manager_reply"
                        ]:
                            with ui.element(
                                "div"
                            ).classes(
                                "jf-feedback-reply"
                            ):
                                ui.label(
                                    feedback[
                                        "manager_reply"
                                    ]
                                )
                                if feedback[
                                    "manager_name"
                                ]:
                                    ui.label(
                                        (
                                            "Réponse de "
                                            f"{feedback['manager_name']}"
                                            + (
                                                " — "
                                                + _date_time_text(
                                                    feedback[
                                                        "replied_at"
                                                    ]
                                                )
                                                if feedback[
                                                    "replied_at"
                                                ]
                                                else ""
                                            )
                                        )
                                    ).classes(
                                        "text-xs jf-muted mt-1"
                                    )
                        else:
                            ui.label(
                                "Aucune réponse pour le moment."
                            ).classes(
                                "text-sm jf-muted"
                            )

                        _render_events(
                            feedback_id
                        )

                        with ui.row().classes(
                            "w-full justify-end mt-3"
                        ):
                            ui.button(
                                "Fermer",
                                on_click=dialog.close,
                            ).props(
                                "color=primary"
                            )

                dialog.open()
                render_own_feedback.refresh()

            def open_user_edit(
                feedback_id,
            ):
                try:
                    feedback = (
                        get_user_feedback(
                            user_id,
                            feedback_id,
                        )
                    )
                except Exception as error:
                    ui.notify(
                        str(error),
                        type="negative",
                    )
                    return

                if (
                    feedback[
                        "status"
                    ]
                    in CLOSED_FEEDBACK_STATUSES
                ):
                    ui.notify(
                        "Ce commentaire est fermé "
                        "et ne peut plus être modifié.",
                        type="warning",
                    )
                    return

                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-2xl p-5"
                    ):
                        ui.label(
                            "Modifier le commentaire"
                        ).classes(
                            "text-xl font-bold"
                        )

                        edit_app = ui.select(
                            app_options,
                            label="Application concernée",
                            value=feedback[
                                "app_key"
                            ],
                        ).props(
                            "outlined options-dense"
                        ).classes(
                            "w-full"
                        )

                        edit_subject = ui.input(
                            label="Sujet",
                            value=feedback[
                                "subject"
                            ],
                        ).props(
                            "maxlength=160"
                        ).classes(
                            "w-full"
                        )

                        edit_detail = ui.textarea(
                            label="Commentaire",
                            value=feedback[
                                "detail"
                            ],
                        ).props(
                            "maxlength=5000 autogrow"
                        ).classes(
                            "w-full"
                        )

                        def save_edit():
                            try:
                                update_user_feedback(
                                    user_id,
                                    feedback_id,
                                    app_key=(
                                        edit_app.value
                                    ),
                                    subject=(
                                        edit_subject.value
                                    ),
                                    detail=(
                                        edit_detail.value
                                    ),
                                )
                            except Exception as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return

                            dialog.close()
                            ui.notify(
                                "Commentaire modifié.",
                                type="positive",
                            )
                            render_own_feedback.refresh()

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-3"
                        ):
                            ui.button(
                                "Annuler",
                                on_click=dialog.close,
                            ).props(
                                "flat"
                            )
                            ui.button(
                                "Enregistrer",
                                icon="save",
                                on_click=save_edit,
                            ).props(
                                "color=primary"
                            )

                dialog.open()

            @ui.refreshable
            def render_own_feedback():
                own_list.clear()

                try:
                    rows = list_user_feedback(
                        user_id
                    )
                except Exception:
                    with own_list:
                        ui.label(
                            "Les commentaires n’ont pas "
                            "pu être chargés."
                        ).classes(
                            "text-negative"
                        )
                    return

                selected_status = str(
                    own_status_filter.value
                    or ""
                )
                selected_app = str(
                    own_app_filter.value
                    or ""
                )
                query = str(
                    own_search.value
                    or ""
                ).strip().lower()

                filtered = []

                for row in rows:
                    if (
                        selected_status
                        and row[
                            "status"
                        ]
                        != selected_status
                    ):
                        continue

                    if (
                        selected_app
                        and row[
                            "app_key"
                        ]
                        != selected_app
                    ):
                        continue

                    searchable = (
                        str(
                            row[
                                "subject"
                            ]
                            or ""
                        )
                        + " "
                        + str(
                            row[
                                "detail"
                            ]
                            or ""
                        )
                    ).lower()

                    if (
                        query
                        and query
                        not in searchable
                    ):
                        continue

                    filtered.append(
                        row
                    )

                with own_list:
                    if not filtered:
                        with ui.card().classes(
                            "w-full p-6 items-center "
                            "text-center"
                        ):
                            ui.icon(
                                "chat_bubble_outline"
                            ).classes(
                                "text-4xl text-gray-400"
                            )
                            ui.label(
                                "Aucun commentaire à afficher"
                            ).classes(
                                "text-lg font-bold"
                            )
                            ui.label(
                                "Utilisez l’onglet Nouveau "
                                "pour transmettre une suggestion."
                            ).classes(
                                "text-sm jf-muted"
                            )
                        return

                    for row in filtered:
                        card_classes = (
                            "jf-feedback-card "
                            "jf-feedback-card-unread"
                            if row[
                                "user_reply_unread"
                            ]
                            else "jf-feedback-card"
                        )

                        with ui.element(
                            "article"
                        ).classes(
                            card_classes
                        ):
                            with ui.row().classes(
                                "w-full items-start "
                                "justify-between gap-3"
                            ):
                                with ui.column().classes(
                                    "gap-1 grow min-w-0"
                                ):
                                    with ui.row().classes(
                                        "items-center gap-2 flex-wrap"
                                    ):
                                        ui.label(
                                            row[
                                                "subject"
                                            ]
                                        ).classes(
                                            "jf-feedback-subject"
                                        )
                                        _render_status(
                                            row[
                                                "status"
                                            ]
                                        )
                                        if row[
                                            "user_reply_unread"
                                        ]:
                                            ui.label(
                                                "Nouvelle réponse"
                                            ).classes(
                                                "jf-feedback-unread"
                                            )

                                    ui.label(
                                        (
                                            FEEDBACK_APP_LABELS.get(
                                                row[
                                                    "app_key"
                                                ],
                                                row[
                                                    "app_key"
                                                ],
                                            )
                                            + " — modifié le "
                                            + _date_time_text(
                                                row[
                                                    "updated_at"
                                                ]
                                            )
                                        )
                                    ).classes(
                                        "jf-feedback-meta"
                                    )

                                    detail = str(
                                        row[
                                            "detail"
                                        ]
                                        or ""
                                    )
                                    preview = (
                                        detail
                                        if len(detail) <= 220
                                        else (
                                            detail[:217]
                                            + "…"
                                        )
                                    )
                                    ui.label(
                                        preview
                                    ).classes(
                                        "text-sm"
                                    )

                                with ui.row().classes(
                                    "gap-1 shrink-0"
                                ):
                                    ui.button(
                                        "Consulter",
                                        icon="visibility",
                                        on_click=(
                                            lambda _event,
                                            selected=row[
                                                "id"
                                            ]:
                                            open_user_detail(
                                                selected
                                            )
                                        ),
                                    ).props(
                                        "flat dense color=primary"
                                    )

                                    if (
                                        row[
                                            "status"
                                        ]
                                        not in CLOSED_FEEDBACK_STATUSES
                                    ):
                                        ui.button(
                                            icon="edit",
                                            on_click=(
                                                lambda _event,
                                                selected=row[
                                                    "id"
                                                ]:
                                                open_user_edit(
                                                    selected
                                                )
                                            ),
                                        ).props(
                                            "flat dense round "
                                            "color=primary"
                                        ).tooltip(
                                            "Modifier"
                                        )

            own_refresh_button.on(
                "click",
                lambda: (
                    render_own_feedback.refresh()
                ),
            )
            own_status_filter.on_value_change(
                lambda event: (
                    render_own_feedback.refresh()
                )
            )
            own_app_filter.on_value_change(
                lambda event: (
                    render_own_feedback.refresh()
                )
            )
            own_search.on_value_change(
                lambda event: (
                    render_own_feedback.refresh()
                )
            )

            render_own_feedback()

        # -------------------------------------------------
        # NOUVEAU COMMENTAIRE
        # -------------------------------------------------
        with ui.tab_panel(
            new_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full max-w-3xl p-5"
            ):
                ui.label(
                    "Nouveau commentaire"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Décrivez précisément le problème observé "
                    "ou l’amélioration souhaitée."
                ).classes(
                    "text-sm jf-muted"
                )

                default_app = next(
                    iter(
                        app_options
                    )
                )

                new_app = ui.select(
                    app_options,
                    label="Application concernée",
                    value=default_app,
                ).props(
                    "outlined options-dense"
                ).classes(
                    "w-full"
                )

                new_subject = ui.input(
                    label="Sujet",
                    placeholder=(
                        "Ex. Affichage trop espacé "
                        "dans l’historique"
                    ),
                ).props(
                    "maxlength=160"
                ).classes(
                    "w-full"
                )

                new_detail = ui.textarea(
                    label="Détail",
                    placeholder=(
                        "Expliquez ce que vous avez fait, "
                        "ce que vous avez observé et ce que "
                        "vous aimeriez améliorer."
                    ),
                ).props(
                    "maxlength=5000 autogrow"
                ).classes(
                    "w-full"
                )

                def submit_feedback():
                    try:
                        create_feedback(
                            user_id,
                            app_key=new_app.value,
                            subject=(
                                new_subject.value
                            ),
                            detail=(
                                new_detail.value
                            ),
                        )
                    except Exception as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return

                    ui.notify(
                        "Commentaire transmis.",
                        type="positive",
                    )
                    ui.navigate.to(
                        "/?tab=commentaires"
                        "&section=mes"
                    )

                ui.button(
                    "Transmettre le commentaire",
                    icon="send",
                    on_click=submit_feedback,
                ).props(
                    "color=primary"
                ).classes(
                    "mt-2"
                )

        # -------------------------------------------------
        # GESTION ADMINISTRATIVE
        # -------------------------------------------------
        if admin_tab is not None:
            with ui.tab_panel(
                admin_tab
            ).classes(
                "px-0"
            ):
                with ui.card().classes(
                    "w-full p-4"
                ):
                    ui.label(
                        "Gestion des commentaires"
                    ).classes(
                        "text-xl font-bold"
                    )
                    ui.label(
                        "Filtrez les demandes, attribuez un statut "
                        "et répondez à l’utilisateur."
                    ).classes(
                        "text-sm jf-muted"
                    )

                    with ui.element(
                        "div"
                    ).classes(
                        "jf-feedback-filter mt-3"
                    ):
                        admin_status_filter = ui.select(
                            {
                                "": "Tous les statuts",
                                **FEEDBACK_STATUS_LABELS,
                            },
                            label="Statut",
                            value="",
                        ).props(
                            "dense outlined options-dense"
                        )

                        admin_app_filter = ui.select(
                            {
                                "": "Toutes les applications",
                                **FEEDBACK_APP_LABELS,
                            },
                            label="Application",
                            value="",
                        ).props(
                            "dense outlined options-dense"
                        )

                        admin_search = ui.input(
                            label="Utilisateur, sujet ou texte",
                        ).props(
                            "dense outlined clearable"
                        ).classes(
                            "jf-feedback-filter-search"
                        )

                        admin_refresh_button = ui.button(
                            "Actualiser",
                            icon="refresh",
                        ).props(
                            "outline dense color=primary"
                        ).classes(
                            "jf-feedback-filter-button"
                        )

                admin_list = ui.column().classes(
                    "jf-feedback-list"
                )

                def open_admin_detail(
                    feedback_id,
                ):
                    try:
                        mark_feedback_manager_read(
                            feedback_id
                        )
                        feedback = (
                            get_feedback_for_admin(
                                feedback_id
                            )
                        )
                    except Exception as error:
                        ui.notify(
                            str(error),
                            type="negative",
                        )
                        return

                    with ui.dialog() as dialog:
                        with ui.card().classes(
                            "w-full max-w-4xl p-5"
                        ):
                            with ui.row().classes(
                                "w-full items-start "
                                "justify-between gap-3"
                            ):
                                with ui.column().classes(
                                    "gap-1"
                                ):
                                    ui.label(
                                        feedback[
                                            "subject"
                                        ]
                                    ).classes(
                                        "text-xl font-bold"
                                    )
                                    ui.label(
                                        (
                                            f"{feedback['author_name']} "
                                            f"— {feedback['author_email']}"
                                        )
                                    ).classes(
                                        "text-sm"
                                    )
                                    ui.label(
                                        (
                                            FEEDBACK_APP_LABELS.get(
                                                feedback[
                                                    "app_key"
                                                ],
                                                feedback[
                                                    "app_key"
                                                ],
                                            )
                                            + " — créé le "
                                            + _date_time_text(
                                                feedback[
                                                    "created_at"
                                                ]
                                            )
                                        )
                                    ).classes(
                                        "text-xs jf-muted"
                                    )

                                _render_status(
                                    feedback[
                                        "status"
                                    ]
                                )

                            ui.label(
                                "Commentaire de l’utilisateur"
                            ).classes(
                                "font-bold mt-2"
                            )
                            ui.label(
                                feedback[
                                    "detail"
                                ]
                            ).classes(
                                "jf-feedback-detail"
                            )

                            with ui.element(
                                "div"
                            ).classes(
                                "jf-feedback-filter mt-3"
                            ):
                                manager_status = ui.select(
                                    FEEDBACK_STATUS_LABELS,
                                    label="Statut",
                                    value=feedback[
                                        "status"
                                    ],
                                ).props(
                                    "outlined options-dense"
                                )

                            manager_reply = ui.textarea(
                                label="Réponse au commentaire",
                                value=(
                                    feedback[
                                        "manager_reply"
                                    ]
                                    or ""
                                ),
                                placeholder=(
                                    "Expliquez la décision, "
                                    "la correction prévue ou "
                                    "la solution apportée."
                                ),
                            ).props(
                                "maxlength=5000 autogrow"
                            ).classes(
                                "w-full"
                            )

                            _render_events(
                                feedback_id
                            )

                            def save_manager_update():
                                try:
                                    update_feedback_by_manager(
                                        feedback_id,
                                        manager_user_id=(
                                            current_user[
                                                "id"
                                            ]
                                        ),
                                        status=(
                                            manager_status.value
                                        ),
                                        manager_reply=(
                                            manager_reply.value
                                        ),
                                    )
                                except Exception as error:
                                    ui.notify(
                                        str(error),
                                        type="warning",
                                    )
                                    return

                                dialog.close()
                                ui.notify(
                                    "Commentaire mis à jour.",
                                    type="positive",
                                )
                                render_admin_feedback.refresh()

                            with ui.row().classes(
                                "w-full justify-end gap-2 mt-3"
                            ):
                                ui.button(
                                    "Fermer",
                                    on_click=dialog.close,
                                ).props(
                                    "flat"
                                )
                                ui.button(
                                    "Enregistrer et répondre",
                                    icon="send",
                                    on_click=save_manager_update,
                                ).props(
                                    "color=primary"
                                )

                    dialog.open()
                    render_admin_feedback.refresh()

                @ui.refreshable
                def render_admin_feedback():
                    admin_list.clear()

                    try:
                        rows = (
                            list_feedback_for_admin(
                                status=(
                                    admin_status_filter.value
                                    or None
                                ),
                                app_key=(
                                    admin_app_filter.value
                                    or None
                                ),
                                query=(
                                    admin_search.value
                                    or None
                                ),
                            )
                        )
                    except Exception:
                        with admin_list:
                            ui.label(
                                "Les commentaires n’ont pas "
                                "pu être chargés."
                            ).classes(
                                "text-negative"
                            )
                        return

                    with admin_list:
                        if not rows:
                            with ui.card().classes(
                                "w-full p-6 items-center "
                                "text-center"
                            ):
                                ui.icon(
                                    "task_alt"
                                ).classes(
                                    "text-4xl text-positive"
                                )
                                ui.label(
                                    "Aucun commentaire "
                                    "dans ce filtre"
                                ).classes(
                                    "text-lg font-bold"
                                )
                            return

                        for row in rows:
                            card_classes = (
                                "jf-feedback-card "
                                "jf-feedback-card-unread"
                                if row[
                                    "manager_unread"
                                ]
                                else "jf-feedback-card"
                            )

                            with ui.element(
                                "article"
                            ).classes(
                                card_classes
                            ):
                                with ui.row().classes(
                                    "w-full items-start "
                                    "justify-between gap-3"
                                ):
                                    with ui.column().classes(
                                        "gap-1 grow min-w-0"
                                    ):
                                        with ui.row().classes(
                                            "items-center gap-2 flex-wrap"
                                        ):
                                            ui.label(
                                                row[
                                                    "subject"
                                                ]
                                            ).classes(
                                                "jf-feedback-subject"
                                            )
                                            _render_status(
                                                row[
                                                    "status"
                                                ]
                                            )
                                            if row[
                                                "manager_unread"
                                            ]:
                                                ui.label(
                                                    "À lire"
                                                ).classes(
                                                    "jf-feedback-unread"
                                                )

                                        ui.label(
                                            (
                                                f"{row['author_name']} "
                                                f"— {row['author_email']}"
                                            )
                                        ).classes(
                                            "text-sm font-bold"
                                        )

                                        ui.label(
                                            (
                                                FEEDBACK_APP_LABELS.get(
                                                    row[
                                                        "app_key"
                                                    ],
                                                    row[
                                                        "app_key"
                                                    ],
                                                )
                                                + " — modifié le "
                                                + _date_time_text(
                                                    row[
                                                        "updated_at"
                                                    ]
                                                )
                                            )
                                        ).classes(
                                            "jf-feedback-meta"
                                        )

                                        detail = str(
                                            row[
                                                "detail"
                                            ]
                                            or ""
                                        )
                                        preview = (
                                            detail
                                            if len(detail) <= 220
                                            else (
                                                detail[:217]
                                                + "…"
                                            )
                                        )
                                        ui.label(
                                            preview
                                        ).classes(
                                            "text-sm"
                                        )

                                    ui.button(
                                        "Gérer",
                                        icon="edit_note",
                                        on_click=(
                                            lambda _event,
                                            selected=row[
                                                "id"
                                            ]:
                                            open_admin_detail(
                                                selected
                                            )
                                        ),
                                    ).props(
                                        "outline dense color=primary"
                                    ).classes(
                                        "shrink-0"
                                    )

                admin_refresh_button.on(
                    "click",
                    lambda: (
                        render_admin_feedback.refresh()
                    ),
                )
                admin_status_filter.on_value_change(
                    lambda event: (
                        render_admin_feedback.refresh()
                    )
                )
                admin_app_filter.on_value_change(
                    lambda event: (
                        render_admin_feedback.refresh()
                    )
                )
                admin_search.on_value_change(
                    lambda event: (
                        render_admin_feedback.refresh()
                    )
                )

                render_admin_feedback()
