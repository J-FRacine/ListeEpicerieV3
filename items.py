from nicegui import app, ui

from auth import get_current_user_id
from db import (
    add_item,
    delete_item,
    get_accessible_families,
    get_barcode_match,
    get_categories,
    get_frequent_items,
    get_items,
    get_stores,
    set_item_barcode,
    set_item_needed,
    toggle_needed,
    update_item,
)
from state import (
    get_current_family_id,
    get_tri_mode_items,
    set_current_family_id,
    set_tri_mode_items,
)
from grocery_preferences import (
    categories_are_enabled,
    get_or_create_default_category_id,
    normalized_text,
)
from utils import ensure_categories_exist, ensure_family_selected


def items_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

    if user_id is None or not ensure_family_selected(family_id):
        return

    families = get_accessible_families(user_id)
    if not families:
        ui.label("Aucune famille accessible.").classes("text-orange-700")
        return

    family_by_name = {
        family["name"]: family["id"]
        for family in families
    }
    current_name = next(
        (
            name
            for name, accessible_id in family_by_name.items()
            if accessible_id == family_id
        ),
        list(family_by_name)[0],
    )

    ui.select(
        list(family_by_name),
        value=current_name,
        label="Famille",
        on_change=lambda event: (
            set_current_family_id(
                family_by_name[event.value]
            ),
            ui.navigate.to("/?tab=items"),
        ),
    ).classes("w-full")

    categories_enabled = categories_are_enabled(
        user_id,
        family_id,
    )

    if categories_enabled:
        if not ensure_categories_exist(user_id, family_id):
            return
    else:
        get_or_create_default_category_id(
            user_id,
            family_id,
        )

    categories = get_categories(user_id, family_id)
    stores = get_stores(user_id, family_id)

    if not stores:
        ui.label(
            "Créez d’abord un magasin dans Catégories et magasins."
        ).classes("text-orange-700")
        return

    category_by_name = {
        row["name"]: row["id"]
        for row in categories
    }
    category_id_by_normalized_name = {
        normalized_text(row["name"]): row["id"]
        for row in categories
    }
    default_category_id = (
        get_or_create_default_category_id(
            user_id,
            family_id,
        )
        if not categories_enabled
        else None
    )
    store_by_name = {
        row["name"]: row["id"]
        for row in stores
    }


    def open_barcode_product(barcode):
        try:
            match = get_barcode_match(
                user_id,
                family_id,
                barcode,
            )
        except (ValueError, PermissionError) as error:
            ui.notify(str(error), type="warning")
            return

        code = match["barcode"]
        family_item = match.get("family_item")

        if family_item:
            if family_item["needed"]:
                ui.notify(
                    f"« {family_item['name']} » est déjà dans les besoins.",
                    type="info",
                )
                return
            try:
                set_item_needed(
                    user_id,
                    family_item["id"],
                    True,
                )
            except (ValueError, PermissionError) as error:
                ui.notify(str(error), type="warning")
                return
            ui.notify(
                f"« {family_item['name']} » ajouté aux besoins.",
                type="positive",
            )
            ui.navigate.to("/?tab=items")
            return

        catalog = match.get("catalog") or {}

        with ui.dialog() as barcode_dialog:
            with ui.card().classes("w-full max-w-xl p-4"):
                ui.label("Produit scanné").classes(
                    "text-xl font-bold"
                )
                ui.label(code).classes(
                    "text-sm font-mono text-gray-500"
                )

                product_name = ui.input(
                    label="Nom de l’item",
                    value=catalog.get("generic_name") or "",
                ).props(
                    "dense outlined autofocus maxlength=160"
                ).classes("w-full")

                with ui.row().classes(
                    "w-full gap-2 flex-wrap"
                ):
                    product_brand = ui.input(
                        label="Marque — facultatif",
                        value=catalog.get("brand") or "",
                    ).props(
                        "dense outlined maxlength=120"
                    ).classes("grow min-w-40")

                    product_format = ui.input(
                        label="Format — facultatif",
                        value=catalog.get("format_text") or "",
                    ).props(
                        "dense outlined maxlength=120"
                    ).classes("grow min-w-40")

                product_quantity = ui.number(
                    label="Quantité",
                    value=1,
                    min=1,
                    step=1,
                ).props("dense outlined").classes("w-full")

                product_category = None
                if categories_enabled:
                    product_category = ui.select(
                        list(category_by_name),
                        value=list(category_by_name)[0],
                        label="Catégorie",
                    ).props(
                        "dense outlined options-dense"
                    ).classes("w-full")

                product_store = ui.select(
                    list(store_by_name),
                    value=list(store_by_name)[0],
                    label="Magasin",
                ).props(
                    "dense outlined options-dense"
                ).classes("w-full")

                product_needed = ui.checkbox(
                    "Ajouter directement aux besoins",
                    value=True,
                )

                ui.label(
                    "Le catalogue partagé conserve seulement le code, "
                    "le nom générique, la marque et le format. "
                    "Magasin, catégorie, quantité, note et état "
                    "restent privés à votre famille."
                ).classes("text-xs text-gray-500")

                def create_scanned_item():
                    name = (
                        product_name.value or ""
                    ).strip()
                    if not name:
                        ui.notify(
                            "Inscrivez le nom du produit.",
                            type="warning",
                        )
                        return

                    try:
                        item_id = add_item(
                            user_id,
                            family_id,
                            (
                                category_by_name[
                                    product_category.value
                                ]
                                if categories_enabled
                                else default_category_id
                            ),
                            name,
                            int(product_quantity.value or 1),
                            bool(product_needed.value),
                            store_id=store_by_name[
                                product_store.value
                            ],
                        )
                        set_item_barcode(
                            user_id,
                            item_id,
                            code,
                            generic_name=name,
                            brand=product_brand.value,
                            format_text=product_format.value,
                        )
                    except (
                        ValueError,
                        PermissionError,
                        KeyError,
                    ) as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return

                    barcode_dialog.close()
                    ui.notify(
                        f"« {name} » ajouté avec son code-barres.",
                        type="positive",
                    )
                    ui.navigate.to("/?tab=items")

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-2"
                ):
                    ui.button(
                        "Annuler",
                        on_click=barcode_dialog.close,
                    ).props("flat")
                    ui.button(
                        "Créer l’item",
                        icon="add_shopping_cart",
                        on_click=create_scanned_item,
                    ).props("color=primary")

        barcode_dialog.open()

    async def scan_barcode_camera():
        javascript = r"""
        return await (async () => {
            if (!navigator.mediaDevices ||
                !navigator.mediaDevices.getUserMedia) {
                return {
                    error: "La caméra n’est pas accessible dans ce navigateur."
                };
            }
            if (!("BarcodeDetector" in window)) {
                return {
                    error: "La détection UPC/EAN par caméra n’est pas disponible ici. Utilisez la saisie manuelle."
                };
            }

            const wanted = ["ean_13", "ean_8", "upc_a", "upc_e"];
            const supported =
                await BarcodeDetector.getSupportedFormats();
            const usable =
                wanted.filter(x => supported.includes(x));

            if (!usable.length) {
                return {
                    error: "Aucun format UPC/EAN compatible n’est disponible."
                };
            }

            let stream = null;
            let overlay = null;

            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: {ideal: "environment"}
                    },
                    audio: false
                });

                overlay = document.createElement("div");
                overlay.style.cssText =
                    "position:fixed;inset:0;z-index:99999;" +
                    "background:rgba(0,0,0,.88);display:flex;" +
                    "flex-direction:column;align-items:center;" +
                    "justify-content:center;gap:14px;padding:20px;";

                const video = document.createElement("video");
                video.autoplay = true;
                video.playsInline = true;
                video.srcObject = stream;
                video.style.cssText =
                    "width:min(92vw,720px);max-height:70vh;" +
                    "border-radius:14px;background:black;";

                const label = document.createElement("div");
                label.textContent =
                    "Placez le code-barres au centre de l’image";
                label.style.cssText =
                    "color:white;font:600 16px sans-serif;" +
                    "text-align:center;";

                const cancel = document.createElement("button");
                cancel.textContent = "Annuler";
                cancel.style.cssText =
                    "padding:10px 18px;border:0;border-radius:9px;" +
                    "font:600 15px sans-serif;cursor:pointer;";

                overlay.append(video, label, cancel);
                document.body.appendChild(overlay);

                const detector =
                    new BarcodeDetector({formats: usable});
                let cancelled = false;
                cancel.onclick = () => { cancelled = true; };

                await video.play();

                const started = Date.now();
                while (
                    !cancelled &&
                    Date.now() - started < 30000
                ) {
                    const codes = await detector.detect(video);
                    if (codes && codes.length) {
                        return {
                            value: codes[0].rawValue || ""
                        };
                    }
                    await new Promise(
                        resolve => setTimeout(resolve, 180)
                    );
                }

                return cancelled
                    ? {cancelled: true}
                    : {
                        error:
                            "Aucun code détecté après 30 secondes."
                    };
            } catch (error) {
                return {
                    error:
                        error && error.message
                        ? error.message
                        : String(error)
                };
            } finally {
                if (stream) {
                    stream.getTracks().forEach(
                        track => track.stop()
                    );
                }
                if (
                    overlay &&
                    overlay.parentNode
                ) {
                    overlay.parentNode.removeChild(overlay);
                }
            }
        })();
        """

        try:
            result = await ui.run_javascript(
                javascript,
                timeout=40.0,
            )
        except Exception as error:
            ui.notify(
                f"Scanner indisponible : {error}",
                type="warning",
            )
            return

        if not result or result.get("cancelled"):
            return
        if result.get("error"):
            ui.notify(
                result["error"],
                type="warning",
            )
            return

        scanned = str(
            result.get("value") or ""
        ).strip()
        if scanned:
            barcode_input.value = scanned
            barcode_input.update()
            open_barcode_product(scanned)

    # ---------------------------------------------------------
    # AJOUT
    # ---------------------------------------------------------

    ui.separator()
    ui.label("Ajouter un item").classes("text-xl font-bold")


    with ui.card().classes(
        "w-full p-3 border-l-4 border-primary"
    ):
        with ui.row().classes(
            "w-full items-end gap-2 flex-wrap"
        ):
            barcode_input = ui.input(
                label="Code-barres UPC / EAN",
                placeholder="Scanner ou saisir le numéro",
            ).props(
                "dense outlined inputmode=numeric autocomplete=off"
            ).classes("grow min-w-[210px]")

            ui.button(
                "Rechercher",
                icon="search",
                on_click=lambda: open_barcode_product(
                    barcode_input.value
                ),
            ).props("outline color=primary")

            ui.button(
                "Scanner",
                icon="qr_code_scanner",
                on_click=scan_barcode_camera,
            ).props("color=primary")

        barcode_input.on(
            "keydown.enter",
            lambda: open_barcode_product(
                barcode_input.value
            ),
        )

        ui.label(
            "La caméra est utilisée seulement pendant le scan. "
            "La saisie manuelle reste disponible si le navigateur "
            "ne prend pas en charge UPC/EAN."
        ).classes("text-xs text-gray-500 mt-1")

    with ui.card().classes("w-full p-4"):
        with ui.row().classes(
            "w-full items-end gap-3 flex-wrap"
        ):
            name_input = ui.input(
                label="Nom"
            ).props(
                "autocomplete=off autofocus"
            ).classes("grow min-w-[210px]")

            quantity_input = ui.number(
                label="Quantité",
                value=1,
                min=1,
                step=1,
            ).classes("w-28")

            category_input = None
            if categories_enabled:
                category_input = ui.select(
                    list(category_by_name),
                    value=list(category_by_name)[0],
                    label="Catégorie",
                ).classes("grow min-w-[170px]")

            store_input = ui.select(
                list(store_by_name),
                value=list(store_by_name)[0],
                label="Magasin",
            ).classes("grow min-w-[170px]")

        note_input = ui.textarea(
            label="Note facultative",
            placeholder=(
                "Ex. Sans sel et sans sucre, idéalement IGA"
            ),
        ).props(
            "autogrow maxlength=500"
        ).classes("w-full")

        needed_input = ui.checkbox(
            "Ajouter directement aux besoins"
        )

        def add_new_item():
            item_name = (
                name_input.value or ""
            ).strip()

            try:
                add_item(
                    user_id,
                    family_id,
                    (
                        category_by_name[
                            category_input.value
                        ]
                        if categories_enabled
                        else default_category_id
                    ),
                    item_name,
                    int(quantity_input.value or 1),
                    bool(needed_input.value),
                    note=(
                        note_input.value or ""
                    ).strip(),
                    store_id=store_by_name[
                        store_input.value
                    ],
                )
            except (
                ValueError,
                PermissionError,
                KeyError,
            ) as error:
                ui.notify(
                    str(error),
                    type="warning",
                )
                return

            ui.notify(
                f"« {item_name} » ajouté.",
                type="positive",
            )
            ui.navigate.to("/?tab=items")

        name_input.on(
            "keydown.enter",
            add_new_item,
        )

        ui.button(
            "Ajouter",
            icon="add",
            on_click=add_new_item,
        ).props(
            "color=primary"
        ).classes("w-full mt-2")

    # ---------------------------------------------------------
    # ITEMS FRÉQUENTS
    # ---------------------------------------------------------

    frequent_items = get_frequent_items(
        user_id,
        family_id,
        limit=10,
    )

    if frequent_items:
        ui.label("Souvent ajoutés").classes(
            "text-lg font-bold mt-1"
        )
        ui.label(
            "Jusqu’à 10 items choisis. Le crochet indique un item déjà "
            "présent dans les besoins."
        ).classes("text-sm text-gray-500")

        with ui.row().classes(
            "w-full gap-2 flex-wrap"
        ):
            for frequent in frequent_items:

                def add_frequent(item=frequent):
                    if item["needed"] == 1:
                        ui.notify(
                            f"« {item['name']} » est déjà dans les besoins.",
                            type="info",
                        )
                        return

                    try:
                        set_item_needed(
                            user_id,
                            item["id"],
                            True,
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

                    ui.notify(
                        f"« {item['name']} » ajouté aux besoins.",
                        type="positive",
                    )
                    ui.navigate.to("/?tab=items")

                already_needed = frequent["needed"] == 1
                ui.button(
                    frequent["name"],
                    icon=(
                        "check_circle"
                        if already_needed
                        else "add_shopping_cart"
                    ),
                    on_click=add_frequent,
                ).props(
                    (
                        "outline color=positive no-caps"
                        if already_needed
                        else "outline color=primary no-caps"
                    )
                ).tooltip(
                    (
                        "Déjà présent dans les besoins"
                        if already_needed
                        else (
                            "Ajouté "
                            f"{frequent['times_needed']} fois "
                            "aux besoins"
                        )
                    )
                )

    # ---------------------------------------------------------
    # RECHERCHE ET TRI
    # ---------------------------------------------------------

    ui.separator()

    search_key = f"items_search_{family_id}"
    search_state = {
        "value": app.storage.user.get(
            search_key,
            "",
        )
    }

    with ui.row().classes(
        "w-full items-center justify-between "
        "gap-3 flex-wrap"
    ):
        ui.label("Tous les items").classes(
            "text-xl font-bold"
        )

        sort_options = [
            "Alphabétique",
            "Ordre d’ajout",
            "Magasin",
        ]
        if categories_enabled:
            sort_options.insert(2, "Catégorie")

        current_sort = get_tri_mode_items()
        if current_sort not in sort_options:
            current_sort = "Alphabétique"
            set_tri_mode_items(current_sort)

        sort_input = ui.select(
            sort_options,
            value=current_sort,
            label="Trier",
        ).props(
            "dense options-dense"
        ).classes("w-44")

    search_input = ui.input(
        label="Rechercher un item",
        value=search_state["value"],
        placeholder=(
            "Nom, note, catégorie ou magasin"
            if categories_enabled
            else "Nom, note ou magasin"
        ),
    ).props(
        "clearable debounce=150 autocomplete=off"
    ).classes("w-full")

    with search_input.add_slot("prepend"):
        ui.icon("search")

    # ---------------------------------------------------------
    # MODIFICATION
    # ---------------------------------------------------------

    def open_edit_dialog(item):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-lg p-5"
            ):
                ui.label("Modifier l’item").classes(
                    "text-xl font-bold"
                )

                edit_name = ui.input(
                    label="Nom",
                    value=item["name"],
                ).classes("w-full")

                edit_note = ui.textarea(
                    label="Note facultative",
                    value=item.get("note") or "",
                ).props(
                    "autogrow maxlength=500"
                ).classes("w-full")

                edit_quantity = ui.number(
                    label="Quantité",
                    value=item["quantity"],
                    min=1,
                    step=1,
                ).classes("w-full")

                edit_barcode = ui.input(
                    label="Code-barres UPC / EAN",
                    value=item.get("barcode") or "",
                ).props(
                    "dense outlined inputmode=numeric"
                ).classes("w-full")

                edit_category = None
                if categories_enabled:
                    edit_category = ui.select(
                        list(category_by_name),
                        value=item["category"],
                        label="Catégorie",
                    ).classes("w-full")

                edit_store = ui.select(
                    list(store_by_name),
                    value=item["store"],
                    label="Magasin",
                ).classes("w-full")

                with ui.row().classes(
                    "w-full items-center gap-6 flex-wrap"
                ):
                    edit_needed = ui.checkbox(
                        "Présent dans les besoins",
                        value=item["needed"] == 1,
                    )
                    edit_frequent = ui.checkbox(
                        "Dans « Souvent ajoutés »",
                        value=bool(
                            item.get("frequent_selected")
                        ),
                    ).tooltip(
                        "Maximum 10 items dans cette section"
                    )

                def save_item():
                    try:
                        update_item(
                            user_id,
                            item["id"],
                            (
                                category_by_name[
                                    edit_category.value
                                ]
                                if categories_enabled
                                else (
                                    item.get("category_id")
                                    or category_id_by_normalized_name.get(
                                        normalized_text(
                                            item.get("category")
                                        )
                                    )
                                    or default_category_id
                                )
                            ),
                            (
                                edit_name.value or ""
                            ).strip(),
                            int(
                                edit_quantity.value or 1
                            ),
                            bool(edit_needed.value),
                            note=(
                                edit_note.value or ""
                            ).strip(),
                            store_id=store_by_name[
                                edit_store.value
                            ],
                            frequent_selected=bool(
                                edit_frequent.value
                            ),
                        )
                        set_item_barcode(
                            user_id,
                            item["id"],
                            edit_barcode.value,
                            generic_name=(
                                edit_name.value or ""
                            ).strip(),
                        )
                    except (
                        ValueError,
                        PermissionError,
                        KeyError,
                    ) as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return

                    dialog.close()
                    ui.notify(
                        "Item modifié.",
                        type="positive",
                    )
                    ui.navigate.to("/?tab=items")

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-3"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save_item,
                    ).props("color=primary")

        dialog.open()

    # ---------------------------------------------------------
    # LISTE
    # ---------------------------------------------------------

    @ui.refreshable
    def render_items():
        all_items = get_items(
            user_id,
            family_id,
        )
        tri_mode = get_tri_mode_items()

        if tri_mode == "Alphabétique":
            all_items.sort(
                key=lambda item: normalized_text(
                    item["name"]
                )
            )
        elif tri_mode == "Catégorie":
            all_items.sort(
                key=lambda item: (
                    item["category_order"],
                    normalized_text(item["category"]),
                    normalized_text(item["name"]),
                )
            )
        elif tri_mode == "Magasin":
            all_items.sort(
                key=lambda item: (
                    item["store_order"],
                    normalized_text(item["store"]),
                    (
                        item["category_order"]
                        if categories_enabled
                        else 0
                    ),
                    normalized_text(item["name"]),
                )
            )

        query = normalized_text(
            search_state["value"]
        )
        visible = all_items

        if query:
            visible = [
                item
                for item in all_items
                if any(
                    query in normalized_text(value)
                    for value in (
                        item["name"],
                        item.get("note"),
                        (
                            item["category"]
                            if categories_enabled
                            else ""
                        ),
                        item["store"],
                    )
                )
            ]

        ui.label(
            (
                f"{len(visible)} sur "
                f"{len(all_items)} items"
            )
            if query
            else (
                f"{len(all_items)} item"
                if len(all_items) == 1
                else f"{len(all_items)} items"
            )
        ).classes("text-sm text-gray-500")

        if not visible:
            with ui.card().classes(
                "w-full p-6 items-center text-center"
            ):
                ui.icon("search_off").classes(
                    "text-4xl text-gray-400"
                )
                ui.label("Aucun item trouvé").classes(
                    "text-lg font-bold"
                )
            return


        for item in visible:

            def change_needed(selected=item):
                try:
                    toggle_needed(
                        user_id,
                        selected["id"],
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

                ui.navigate.to("/?tab=items")

            def move_to_trash(selected=item):
                try:
                    delete_item(
                        user_id,
                        selected["id"],
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

                ui.notify(
                    f"« {selected['name']} » déplacé dans la corbeille.",
                    type="positive",
                )
                ui.navigate.to("/?tab=items")

            with ui.element("div").classes(
                "w-full border-b border-gray-200 "
                "hover:bg-blue-50 transition-colors"
            ):
                with ui.row().classes(
                    "w-full min-h-[48px] items-center "
                    "flex-nowrap gap-1 px-2"
                ):
                    ui.button(
                        icon=(
                            "check_circle"
                            if item["needed"]
                            else "radio_button_unchecked"
                        ),
                        on_click=change_needed,
                    ).props(
                        (
                            "flat round dense color=positive"
                            if item["needed"]
                            else "flat round dense color=grey-6"
                        )
                    ).tooltip(
                        (
                            "Retirer des besoins"
                            if item["needed"]
                            else "Ajouter aux besoins"
                        )
                    )

                    touch_area = ui.row().classes(
                        "grow min-w-0 items-center gap-3 "
                        "px-1 py-2 cursor-pointer"
                    )
                    touch_area.on(
                        "click",
                        change_needed,
                    )

                    with touch_area:
                        with ui.column().classes(
                            "gap-0 min-w-0 grow"
                        ):
                            title = item["name"]
                            if item["quantity"] != 1:
                                title += (
                                    f" ({item['quantity']})"
                                )

                            ui.label(title).classes(
                                "font-semibold leading-tight "
                                "whitespace-normal break-words"
                            ).style(
                                "overflow-wrap:anywhere;"
                            )

                            details = (
                                f"{item['store']} · "
                                f"{item['category']}"
                                if categories_enabled
                                else item["store"]
                            )
                            if item.get("barcode"):
                                details += (
                                    f" · {item['barcode']}"
                                )

                            ui.label(details).classes(
                                "text-xs text-gray-500 "
                                "leading-tight"
                            )

                            if item.get("note"):
                                ui.label(
                                    item["note"]
                                ).classes(
                                    "text-xs text-gray-400 "
                                    "whitespace-normal leading-tight"
                                ).style(
                                    "overflow-wrap:anywhere;"
                                )

                    ui.button(
                        icon="edit",
                        on_click=lambda selected=item: (
                            open_edit_dialog(selected)
                        ),
                    ).props(
                        "flat round dense color=primary"
                    ).tooltip("Modifier")

                    ui.button(
                        icon="delete",
                        on_click=move_to_trash,
                    ).props(
                        "flat round dense color=negative"
                    ).tooltip(
                        "Mettre à la corbeille"
                    )

    def search_changed(event):
        search_state["value"] = event.value or ""
        app.storage.user[
            search_key
        ] = search_state["value"]
        render_items.refresh()

    def sort_changed(event):
        set_tri_mode_items(event.value)
        render_items.refresh()

    search_input.on_value_change(search_changed)
    sort_input.on_value_change(sort_changed)
    render_items()

    ui.label(
        "Astuce : touchez la partie principale d’un item "
        "pour changer son état de besoin."
    ).classes("text-xs text-gray-500 mt-2")
