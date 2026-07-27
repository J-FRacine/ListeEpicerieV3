from nicegui import ui

from app_access import (
    ALL_APP_KEYS,
    APP_DEFINITIONS,
    app_labels,
    list_user_app_access_for_admin,
    set_user_app_access_for_admin,
)

from auth import (
    hash_password,
    normalize_email,
    validate_password,
    verify_password,
)
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
    access_by_user = (
        list_user_app_access_for_admin(
            actor_user_id
        )
    )
    app_options = {
        app_key: definition["label"]
        for app_key, definition
        in APP_DEFINITIONS.items()
    }

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Utilisateurs").classes("text-2xl font-bold")
            ui.label(
                "Créez les comptes et choisissez leurs "
                "familles et applications."
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

        app_input = ui.select(
            app_options,
            value=["grocery"],
            multiple=True,
            label="Applications accessibles",
        ).props(
            "use-chips options-dense"
        ).classes("w-full")

        ui.label(
            "Le Journal de pression est disponible. "
            "Les applications Finances et Personnages JDR "
            "restent affichées avec la mention « Bientôt »."
        ).classes(
            "text-xs text-gray-500"
        )

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
                new_user_id = (
                    create_user_for_admin(
                        actor_user_id,
                        name_input.value,
                        email_input.value,
                        password_hash,
                        family_input.value or [],
                        is_admin=admin_input.value,
                    )
                )

                if not admin_input.value:
                    set_user_app_access_for_admin(
                        actor_user_id,
                        new_user_id,
                        app_input.value or [],
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

    def open_app_access_dialog(user):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-lg p-5"
            ):
                ui.label(
                    "Applications accessibles"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    user["display_name"]
                ).classes(
                    "font-bold"
                )

                if user["is_admin"]:
                    ui.label(
                        "Un administrateur du portail "
                        "a automatiquement accès à "
                        "toutes les applications."
                    ).classes(
                        "text-sm text-gray-500"
                    )

                    with ui.row().classes(
                        "w-full justify-end mt-3"
                    ):
                        ui.button(
                            "Fermer",
                            on_click=dialog.close,
                        ).props("flat")
                else:
                    current_keys = sorted(
                        access_by_user.get(
                            user["id"],
                            set(),
                        )
                    )

                    applications_input = ui.select(
                        app_options,
                        value=current_keys,
                        multiple=True,
                        label="Applications",
                    ).props(
                        "use-chips options-dense"
                    ).classes(
                        "w-full"
                    )

                    ui.label(
                        "Une application retirée disparaît "
                        "du portail et ses routes deviennent "
                        "inaccessibles pour ce compte."
                    ).classes(
                        "text-sm text-gray-500"
                    )

                    def save_app_access():
                        try:
                            set_user_app_access_for_admin(
                                actor_user_id,
                                user["id"],
                                (
                                    applications_input.value
                                    or []
                                ),
                            )
                        except (
                            ValueError,
                            PermissionError,
                        ) as error:
                            ui.notify(
                                str(error),
                                type="warning",
                            )
                            return

                        dialog.close()
                        ui.notify(
                            "Accès aux applications "
                            "mis à jour.",
                            type="positive",
                        )
                        ui.navigate.to(
                            "/?tab=utilisateurs"
                        )

                    with ui.row().classes(
                        "w-full justify-end "
                        "gap-2 mt-3"
                    ):
                        ui.button(
                            "Annuler",
                            on_click=dialog.close,
                        ).props("flat")
                        ui.button(
                            "Enregistrer",
                            icon="save",
                            on_click=save_app_access,
                        ).props(
                            "color=primary"
                        )

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

                            user_app_keys = (
                                set(ALL_APP_KEYS)
                                if user["is_admin"]
                                else access_by_user.get(
                                    user["id"],
                                    set(),
                                )
                            )
                            user_app_names = app_labels(
                                user_app_keys
                            )

                            ui.label(
                                (
                                    "Applications : "
                                    + ", ".join(
                                        user_app_names
                                    )
                                )
                                if user_app_names
                                else (
                                    "Applications : aucune"
                                )
                            ).classes(
                                "text-sm text-gray-500"
                            )

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
                            icon="apps",
                            on_click=lambda selected=user: (
                                open_app_access_dialog(
                                    selected
                                )
                            ),
                        ).props(
                            "flat round color=primary"
                        ).tooltip(
                            "Gérer les applications"
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

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Mon compte").classes("text-2xl font-bold")
            ui.label(
                "Modifiez vos informations personnelles "
                "et votre mot de passe."
            ).classes("text-sm text-gray-500")

        if current_user["is_admin"]:
            ui.badge("Administrateur").props("color=primary")

    # ---------------------------------------------------------
    # INFORMATIONS PERSONNELLES
    # ---------------------------------------------------------

    with ui.card().classes("w-full p-5"):
        with ui.row().classes("w-full items-center gap-3"):
            ui.icon("person").classes("text-3xl text-primary")

            with ui.column().classes("gap-0 grow"):
                ui.label("Informations personnelles").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Votre courriel sert aussi à vous connecter."
                ).classes("text-sm text-gray-500")

        name_input = ui.input(
            label="Nom affiché",
            value=current_user["display_name"],
        ).props("autocomplete=name").classes("w-full mt-2")

        email_input = ui.input(
            label="Adresse courriel",
            value=current_user["email"],
        ).props(
            "type=email autocomplete=email"
        ).classes("w-full")

        current_password_for_profile = ui.input(
            label="Mot de passe actuel",
            password=True,
            password_toggle_button=True,
        ).props(
            "autocomplete=current-password"
        ).classes("w-full")

        ui.label(
            "Le mot de passe actuel est demandé seulement "
            "si vous changez votre adresse courriel."
        ).classes("text-xs text-gray-500")

        profile_status = ui.label("").classes(
            "text-sm min-h-[22px]"
        )

        def save_profile():
            profile_status.set_text("")

            fresh_user = get_user_by_id(user_id)

            if fresh_user is None:
                profile_status.set_text(
                    "Ce compte n’existe plus."
                )
                profile_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                return

            new_name = (name_input.value or "").strip()
            new_email = normalize_email(email_input.value)
            old_email = normalize_email(fresh_user["email"])
            email_changed = new_email != old_email

            if not new_name:
                profile_status.set_text(
                    "Le nom est obligatoire."
                )
                profile_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                name_input.run_method("focus")
                return

            if (
                not new_email
                or "@" not in new_email
                or new_email.startswith("@")
                or new_email.endswith("@")
            ):
                profile_status.set_text(
                    "L’adresse courriel semble invalide."
                )
                profile_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                email_input.run_method("focus")
                return

            if email_changed and not verify_password(
                current_password_for_profile.value or "",
                fresh_user["password_hash"],
            ):
                profile_status.set_text(
                    "Le mot de passe actuel est requis "
                    "pour changer l’adresse courriel."
                )
                profile_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                current_password_for_profile.run_method("focus")
                return

            try:
                updated_user = update_own_profile(
                    user_id,
                    new_name,
                    new_email,
                )
            except (ValueError, PermissionError) as error:
                profile_status.set_text(str(error))
                profile_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                return

            current_password_for_profile.value = ""
            current_password_for_profile.update()

            profile_status.set_text(
                "Informations personnelles enregistrées."
            )
            profile_status.classes(
                replace="text-sm min-h-[22px] text-positive"
            )

            if email_changed:
                ui.notify(
                    "Adresse courriel modifiée. Utilisez-la "
                    "lors de votre prochaine connexion.",
                    type="positive",
                    timeout=7000,
                )
            else:
                ui.notify(
                    "Profil mis à jour.",
                    type="positive",
                )

            # Recharge la page afin que le portail utilise immédiatement
            # le nouveau nom et le nouveau courriel.
            ui.navigate.to("/?tab=compte")

        ui.button(
            "Enregistrer",
            icon="save",
            on_click=save_profile,
        ).props("color=primary").classes("w-full mt-2")

    # ---------------------------------------------------------
    # MOT DE PASSE
    # ---------------------------------------------------------

    with ui.card().classes("w-full p-5"):
        with ui.row().classes("w-full items-center gap-3"):
            ui.icon("password").classes(
                "text-3xl text-primary"
            )

            with ui.column().classes("gap-0 grow"):
                ui.label("Changer mon mot de passe").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Le nouveau mot de passe doit contenir "
                    "au moins 10 caractères."
                ).classes("text-sm text-gray-500")

        current_password_input = ui.input(
            label="Mot de passe actuel",
            password=True,
            password_toggle_button=True,
        ).props(
            "autocomplete=current-password"
        ).classes("w-full mt-2")

        new_password_input = ui.input(
            label="Nouveau mot de passe",
            password=True,
            password_toggle_button=True,
        ).props(
            "autocomplete=new-password"
        ).classes("w-full")

        confirmation_input = ui.input(
            label="Confirmer le nouveau mot de passe",
            password=True,
            password_toggle_button=True,
        ).props(
            "autocomplete=new-password"
        ).classes("w-full")

        password_status = ui.label("").classes(
            "text-sm min-h-[22px]"
        )

        def save_password():
            password_status.set_text("")

            fresh_user = get_user_by_id(user_id)

            if fresh_user is None or not verify_password(
                current_password_input.value or "",
                fresh_user["password_hash"],
            ):
                password_status.set_text(
                    "Le mot de passe actuel est incorrect."
                )
                password_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                current_password_input.run_method("focus")
                return

            new_password = new_password_input.value or ""
            confirmation = confirmation_input.value or ""

            if new_password != confirmation:
                password_status.set_text(
                    "Les deux nouveaux mots de passe "
                    "ne correspondent pas."
                )
                password_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                confirmation_input.run_method("focus")
                return

            if verify_password(
                new_password,
                fresh_user["password_hash"],
            ):
                password_status.set_text(
                    "Le nouveau mot de passe doit être différent "
                    "du mot de passe actuel."
                )
                password_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                new_password_input.run_method("focus")
                return

            try:
                validate_password(new_password)
                password_hash = hash_password(new_password)
                update_own_password_hash(
                    user_id,
                    password_hash,
                )
            except (ValueError, PermissionError) as error:
                password_status.set_text(str(error))
                password_status.classes(
                    replace="text-sm min-h-[22px] text-negative"
                )
                return

            for password_field in (
                current_password_input,
                new_password_input,
                confirmation_input,
            ):
                password_field.value = ""
                password_field.update()

            password_status.set_text(
                "Mot de passe modifié."
            )
            password_status.classes(
                replace="text-sm min-h-[22px] text-positive"
            )

            ui.notify(
                "Mot de passe modifié.",
                type="positive",
            )

        confirmation_input.on(
            "keydown.enter",
            save_password,
        )

        ui.button(
            "Changer le mot de passe",
            icon="password",
            on_click=save_password,
        ).props("color=primary").classes("w-full mt-2")

    # ---------------------------------------------------------
    # INFORMATIONS DU COMPTE
    # ---------------------------------------------------------

    with ui.card().classes("w-full p-5"):
        ui.label("Informations du compte").classes(
            "text-lg font-bold"
        )

        account_type = (
            "Administrateur du portail"
            if current_user["is_admin"]
            else "Utilisateur"
        )

        with ui.row().classes(
            "w-full items-center justify-between gap-3"
        ):
            ui.label("Type de compte").classes(
                "text-gray-600"
            )
            ui.label(account_type).classes("font-bold")

        with ui.row().classes(
            "w-full items-center justify-between gap-3"
        ):
            ui.label("État").classes("text-gray-600")
            ui.badge("Actif").props("color=positive")

