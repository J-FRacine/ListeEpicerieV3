from nicegui import ui

from auth import hash_password, validate_password, verify_password
from db import (
    create_user_for_admin,
    get_accessible_families,
    get_user_by_id,
    list_users_for_admin,
    reset_user_password_for_admin,
    set_user_active_for_admin,
    set_user_memberships_for_admin,
    update_own_password_hash,
    update_own_profile,
)


def users_panel(current_user):
    actor_user_id = current_user["id"]

    if not current_user["is_admin"]:
        ui.label("Accès refusé.").classes("text-negative font-bold")
        return

    families = get_accessible_families(actor_user_id)
    family_options = {
        family["id"]: family["name"]
        for family in families
    }
    users = list_users_for_admin(actor_user_id)

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Utilisateurs").classes("text-2xl font-bold")
            ui.label(
                "Créez les comptes et choisissez leurs familles."
            ).classes("text-sm text-gray-500")

        ui.label(
            f"{len(users)} utilisateur"
            if len(users) == 1
            else f"{len(users)} utilisateurs"
        ).classes("text-sm bg-gray-100 rounded-full px-3 py-1")

    with ui.card().classes("w-full p-5"):
        ui.label("Créer un utilisateur").classes("text-xl font-bold")

        name_input = ui.input(label="Nom affiché").classes("w-full")
        email_input = ui.input(
            label="Adresse courriel"
        ).props("type=email").classes("w-full")

        with ui.row().classes("w-full gap-3 flex-wrap"):
            password_input = ui.input(
                label="Mot de passe temporaire",
                password=True,
                password_toggle_button=True,
            ).classes("grow min-w-[220px]")
            confirmation_input = ui.input(
                label="Confirmer le mot de passe",
                password=True,
                password_toggle_button=True,
            ).classes("grow min-w-[220px]")

        family_input = ui.select(
            family_options,
            value=[],
            multiple=True,
            label="Familles accessibles",
        ).props("use-chips").classes("w-full")

        admin_input = ui.checkbox(
            "Administrateur du portail — accès à toutes les familles"
        )

        def create_account():
            if password_input.value != confirmation_input.value:
                ui.notify(
                    "Les deux mots de passe ne correspondent pas.",
                    type="warning",
                )
                return

            try:
                validate_password(password_input.value or "")
                password_hash = hash_password(password_input.value)
                create_user_for_admin(
                    actor_user_id,
                    name_input.value,
                    email_input.value,
                    password_hash,
                    family_input.value or [],
                    is_admin=admin_input.value,
                )
            except (ValueError, PermissionError) as error:
                ui.notify(str(error), type="warning")
                return

            ui.notify("Utilisateur créé.", type="positive")
            ui.navigate.to("/?tab=utilisateurs")

        ui.button(
            "Créer le compte",
            icon="person_add",
            on_click=create_account,
        ).props("color=primary").classes("w-full mt-2")

    def open_memberships_dialog(user):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-lg p-5"):
                ui.label("Familles accessibles").classes(
                    "text-xl font-bold"
                )
                ui.label(user["display_name"]).classes("font-bold")
                ui.label(
                    "Les familles créées par cet utilisateur peuvent "
                    "demeurer protégées comme propriétaire."
                ).classes("text-sm text-gray-500")

                memberships_input = ui.select(
                    family_options,
                    value=list(user["family_ids"] or []),
                    multiple=True,
                    label="Familles",
                ).props("use-chips").classes("w-full")

                def save_memberships():
                    try:
                        set_user_memberships_for_admin(
                            actor_user_id,
                            user["id"],
                            memberships_input.value or [],
                        )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    ui.notify("Accès aux familles mis à jour.", type="positive")
                    ui.navigate.to("/?tab=utilisateurs")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save_memberships,
                    ).props("color=primary")

        dialog.open()

    def open_password_dialog(user):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Réinitialiser le mot de passe").classes(
                    "text-xl font-bold"
                )
                ui.label(user["display_name"]).classes("font-bold")

                password_input = ui.input(
                    label="Nouveau mot de passe",
                    password=True,
                    password_toggle_button=True,
                ).classes("w-full")
                confirmation_input = ui.input(
                    label="Confirmer le mot de passe",
                    password=True,
                    password_toggle_button=True,
                ).classes("w-full")

                def save_password():
                    if password_input.value != confirmation_input.value:
                        ui.notify(
                            "Les deux mots de passe ne correspondent pas.",
                            type="warning",
                        )
                        return

                    try:
                        password_hash = hash_password(password_input.value or "")
                        reset_user_password_for_admin(
                            actor_user_id,
                            user["id"],
                            password_hash,
                        )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    ui.notify("Mot de passe modifié.", type="positive")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="password",
                        on_click=save_password,
                    ).props("color=primary")

        dialog.open()

    ui.label("Comptes existants").classes("text-lg font-bold")

    with ui.column().classes("w-full gap-2"):
        for user in users:
            with ui.card().classes("w-full p-4"):
                with ui.row().classes(
                    "w-full items-center justify-between gap-3 flex-wrap"
                ):
                    with ui.row().classes(
                        "items-center gap-3 grow min-w-[210px]"
                    ):
                        ui.icon("person").classes("text-2xl text-primary")

                        with ui.column().classes("gap-0"):
                            with ui.row().classes("items-center gap-2 flex-wrap"):
                                ui.label(user["display_name"]).classes(
                                    "font-bold text-base"
                                )
                                if user["is_admin"]:
                                    ui.badge("Administrateur").props(
                                        "color=primary"
                                    )
                                if not user["is_active"]:
                                    ui.badge("Désactivé").props(
                                        "color=negative"
                                    )

                            ui.label(user["email"]).classes(
                                "text-sm text-gray-500"
                            )
                            family_names = list(user["family_names"] or [])
                            ui.label(
                                ", ".join(family_names)
                                if family_names
                                else "Aucune famille attribuée"
                            ).classes("text-sm text-gray-500")

                    with ui.row().classes("items-center gap-0"):
                        ui.button(
                            icon="groups",
                            on_click=lambda selected=user: (
                                open_memberships_dialog(selected)
                            ),
                        ).props("flat round color=primary").tooltip(
                            "Gérer les familles"
                        )
                        ui.button(
                            icon="password",
                            on_click=lambda selected=user: (
                                open_password_dialog(selected)
                            ),
                        ).props("flat round color=primary").tooltip(
                            "Réinitialiser le mot de passe"
                        )

                        def toggle_active(selected=user):
                            try:
                                set_user_active_for_admin(
                                    actor_user_id,
                                    selected["id"],
                                    not selected["is_active"],
                                )
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                return

                            ui.navigate.to("/?tab=utilisateurs")

                        ui.button(
                            icon="person_off"
                            if user["is_active"]
                            else "person_add",
                            on_click=toggle_active,
                        ).props(
                            "flat round color=negative"
                            if user["is_active"]
                            else "flat round color=positive"
                        ).tooltip(
                            "Désactiver"
                            if user["is_active"]
                            else "Réactiver"
                        )


def account_panel(current_user):
    user_id = current_user["id"]

    ui.label("Mon compte").classes("text-2xl font-bold")

    with ui.card().classes("w-full p-5"):
        ui.label("Profil").classes("text-xl font-bold")
        name_input = ui.input(
            label="Nom affiché",
            value=current_user["display_name"],
        ).classes("w-full")
        ui.input(
            label="Adresse courriel",
            value=current_user["email"],
        ).props("readonly").classes("w-full")

        def save_profile():
            try:
                update_own_profile(user_id, name_input.value)
            except (ValueError, PermissionError) as error:
                ui.notify(str(error), type="warning")
                return

            ui.notify("Profil mis à jour.", type="positive")
            ui.navigate.to("/?tab=compte")

        ui.button(
            "Enregistrer le profil",
            icon="save",
            on_click=save_profile,
        ).props("color=primary").classes("w-full mt-2")

    with ui.card().classes("w-full p-5"):
        ui.label("Changer mon mot de passe").classes("text-xl font-bold")
        current_password_input = ui.input(
            label="Mot de passe actuel",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        new_password_input = ui.input(
            label="Nouveau mot de passe",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        confirmation_input = ui.input(
            label="Confirmer le nouveau mot de passe",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")

        def save_password():
            fresh_user = get_user_by_id(user_id)

            if fresh_user is None or not verify_password(
                current_password_input.value or "",
                fresh_user["password_hash"],
            ):
                ui.notify(
                    "Le mot de passe actuel est incorrect.",
                    type="warning",
                )
                return

            if new_password_input.value != confirmation_input.value:
                ui.notify(
                    "Les deux nouveaux mots de passe ne correspondent pas.",
                    type="warning",
                )
                return

            try:
                password_hash = hash_password(new_password_input.value or "")
                update_own_password_hash(user_id, password_hash)
            except (ValueError, PermissionError) as error:
                ui.notify(str(error), type="warning")
                return

            current_password_input.value = ""
            new_password_input.value = ""
            confirmation_input.value = ""
            ui.notify("Mot de passe modifié.", type="positive")

        ui.button(
            "Changer le mot de passe",
            icon="password",
            on_click=save_password,
        ).props("color=primary").classes("w-full mt-2")
