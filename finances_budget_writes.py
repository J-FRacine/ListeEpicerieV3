"""Écritures Budget avec connexion, validateurs et source de date injectés.

Les façades historiques résolvent ces dépendances à chaque appel.
Le SQL, son ordre et les frontières de transaction restent inchangés.
"""
from decimal import Decimal

from finances_calculations import month_start as _month_start


def toggle_budget_item(
    user_id, budget_item_id, is_active, *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_budget_items
                SET is_active=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (bool(is_active), budget_item_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Poste budgétaire introuvable.")
            conn.commit()


def move_budget_item(
    user_id, budget_item_id, direction, *,
    get_connection,
):
    if direction not in {"up", "down"}:
        raise ValueError("Direction invalide.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, item_type, sort_order
                FROM finance_budget_items
                WHERE user_id=%s
                ORDER BY item_type, sort_order, id
                FOR UPDATE;
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            current = next(
                (row for row in rows if int(row["id"]) == int(budget_item_id)),
                None,
            )
            if not current:
                raise ValueError("Poste budgétaire introuvable.")
            same_type = [row for row in rows if row["item_type"] == current["item_type"]]
            ids = [int(row["id"]) for row in same_type]
            index = ids.index(int(budget_item_id))
            target_index = index - 1 if direction == "up" else index + 1
            if target_index < 0 or target_index >= len(same_type):
                return
            target = same_type[target_index]
            current_order = int(current["sort_order"])
            target_order = int(target["sort_order"])
            if current_order == target_order:
                current_order = index + 1
                target_order = target_index + 1
            cur.execute(
                "UPDATE finance_budget_items SET sort_order=%s,updated_at=NOW() WHERE id=%s;",
                (target_order, current["id"]),
            )
            cur.execute(
                "UPDATE finance_budget_items SET sort_order=%s,updated_at=NOW() WHERE id=%s;",
                (current_order, target["id"]),
            )
            conn.commit()


def _create_budget_recurrence_cursor(
    cur, user_id, *, transaction_type, fallback_description, fallback_amount, fallback_start, fallback_end, payload,
    _text, _money, _optional_date_value, _normalize_reminder_time, _validate_links, _validate_payment_method, FREQUENCY_UNITS, CONFIRMATION_MODES, date,
):
    """Crée une récurrence dans la transaction SQL du poste Budget."""

    payload = dict(payload or {})
    description = _text(
        payload.get("description") or fallback_description,
        "La description de la récurrence",
        160,
        True,
    )
    amount = _money(
        payload.get("amount")
        if payload.get("amount") not in (None, "")
        else fallback_amount
    )
    frequency_unit = payload.get("frequency_unit") or "month"
    if frequency_unit not in FREQUENCY_UNITS:
        raise ValueError("Fréquence de récurrence invalide.")
    interval = int(payload.get("frequency_interval") or 1)
    if interval < 1 or interval > 365:
        raise ValueError("L’intervalle de récurrence doit être compris entre 1 et 365.")

    start_source = payload.get("start_date") or fallback_start or date.today()
    parsed_start = _optional_date_value(
        start_source,
        "La date de début de la récurrence",
    )
    end_source = (
        payload.get("end_date")
        if payload.get("end_date") not in (None, "")
        else fallback_end
    )
    parsed_end = _optional_date_value(
        end_source,
        "La date de fin de la récurrence",
    )
    if parsed_end and parsed_end < parsed_start:
        raise ValueError("La date de fin de la récurrence précède sa date de début.")

    confirmation_mode = payload.get("confirmation_mode") or "confirm"
    if confirmation_mode not in CONFIRMATION_MODES:
        raise ValueError("Mode de confirmation de la récurrence invalide.")

    category_id = payload.get("category_id") or None
    tag_ids = payload.get("tag_ids") or []
    tags = _validate_links(cur, user_id, category_id, tag_ids)
    payment_method_id = _validate_payment_method(
        cur,
        user_id,
        payload.get("payment_method_id"),
    )
    recurrence_note = _text(
        payload.get("note"),
        "La note de la récurrence",
        1000,
    )
    reminder_time = _normalize_reminder_time(
        payload.get("reminder_time") or "09:00"
    )

    cur.execute(
        """
        INSERT INTO finance_recurrences (
            user_id,
            transaction_type,
            description,
            amount,
            category_id,
            payment_method_id,
            note,
            frequency_unit,
            frequency_interval,
            start_date,
            end_date,
            next_date,
            confirmation_mode,
            budget_excluded,
            bank_programmed,
            reminder_enabled,
            reminder_time
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        RETURNING id;
        """,
        (
            user_id,
            transaction_type,
            description,
            amount,
            category_id,
            payment_method_id,
            recurrence_note,
            frequency_unit,
            interval,
            parsed_start,
            parsed_end,
            parsed_start,
            confirmation_mode,
            bool(payload.get("budget_excluded", False)),
            bool(payload.get("bank_programmed", False)),
            bool(payload.get("reminder_enabled", False)),
            reminder_time,
        ),
    )
    recurrence_id = int(cur.fetchone()["id"])
    for tag_id in tags:
        cur.execute(
            """
            INSERT INTO finance_recurrence_tags (recurrence_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (recurrence_id, tag_id),
        )
    return recurrence_id


def save_budget_item(
    user_id, item_type, description, input_frequency, input_amount, biweekly_override=None, note=None, recurrence_id=None, sync_from_recurrence=True, budget_item_id=None, effective_start=None, effective_end=None, allow_overlap=False, new_recurrence=None, *,
    get_connection, TRANSACTION_TYPES, BUDGET_INPUT_FREQUENCIES, _text, _money, _optional_date_value, _create_budget_recurrence_cursor, _budget_values_from_recurrence, _periods_overlap,
):
    """Enregistre un poste Budget V1.10.1.

    Corrige le NULL PostgreSQL des validations, permet la création atomique
    d'une récurrence et synchronise la date de fin vers la récurrence liée.
    """

    if item_type not in TRANSACTION_TYPES:
        raise ValueError("Type de poste budgétaire invalide.")
    if input_frequency not in BUDGET_INPUT_FREQUENCIES:
        raise ValueError("Fréquence budgétaire invalide.")

    description = _text(description, "La description", 160, True)
    amount = _money(input_amount)
    override = (
        _money(biweekly_override)
        if biweekly_override not in (None, "")
        else None
    )
    note = _text(note, "La note", 1000)
    start_value = _optional_date_value(effective_start, "La date de début")
    end_value = _optional_date_value(effective_end, "La date de fin")
    if start_value and end_value and end_value < start_value:
        raise ValueError(
            "La date de fin doit être égale ou postérieure à la date de début."
        )
    if input_frequency == "biweekly":
        override = None

    normalized_recurrence_id = (
        int(recurrence_id)
        if recurrence_id not in (None, "")
        else None
    )
    if new_recurrence and normalized_recurrence_id is not None:
        raise ValueError(
            "Choisissez une récurrence existante ou créez-en une nouvelle, pas les deux."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            if new_recurrence:
                normalized_recurrence_id = _create_budget_recurrence_cursor(
                    cur,
                    user_id,
                    transaction_type=item_type,
                    fallback_description=description,
                    fallback_amount=amount,
                    fallback_start=start_value,
                    fallback_end=end_value,
                    payload=new_recurrence,
                )

            linked = None
            if normalized_recurrence_id is not None:
                cur.execute(
                    """
                    SELECT id, transaction_type, amount,
                           frequency_unit, frequency_interval,
                           start_date, end_date
                    FROM finance_recurrences
                    WHERE id=%s AND user_id=%s;
                    """,
                    (normalized_recurrence_id, user_id),
                )
                linked = cur.fetchone()
                if not linked:
                    raise ValueError("La récurrence sélectionnée est invalide.")
                if sync_from_recurrence:
                    item_type = linked["transaction_type"]
                    input_frequency, amount = _budget_values_from_recurrence(linked)
                    if input_frequency == "biweekly":
                        override = None
                    if end_value and end_value < linked["start_date"]:
                        raise ValueError(
                            "La date de fin du poste Budget précède le début de la récurrence."
                        )

                # Ne pas envoyer un NULL non typé dans « %s IS NULL » : pour
                # un nouveau poste, la condition d'exclusion n'est simplement
                # pas ajoutée à la requête.
                duplicate_sql = """
                    SELECT id
                    FROM finance_budget_items
                    WHERE user_id=%s AND recurrence_id=%s
                """
                duplicate_params = [user_id, normalized_recurrence_id]
                if budget_item_id is not None:
                    duplicate_sql += " AND id<>%s"
                    duplicate_params.append(int(budget_item_id))
                duplicate_sql += " LIMIT 1;"
                cur.execute(duplicate_sql, duplicate_params)
                if cur.fetchone():
                    raise ValueError(
                        "Cette récurrence est déjà liée à un autre poste du Budget."
                    )

            if not allow_overlap:
                overlap_sql = """
                    SELECT id, effective_start, effective_end
                    FROM finance_budget_items
                    WHERE user_id=%s
                      AND item_type=%s
                      AND LOWER(TRIM(description))=LOWER(TRIM(%s))
                """
                overlap_params = [user_id, item_type, description]
                if budget_item_id is not None:
                    overlap_sql += " AND id<>%s"
                    overlap_params.append(int(budget_item_id))
                overlap_sql += ";"
                cur.execute(overlap_sql, overlap_params)
                for other in cur.fetchall():
                    if _periods_overlap(
                        start_value,
                        end_value,
                        other.get("effective_start"),
                        other.get("effective_end"),
                    ):
                        raise ValueError(
                            "Une autre période de ce poste budgétaire se chevauche. "
                            "Ajustez les dates ou autorisez explicitement le chevauchement."
                        )

            if budget_item_id:
                cur.execute(
                    """
                    UPDATE finance_budget_items
                    SET item_type=%s,
                        description=%s,
                        input_frequency=%s,
                        input_amount=%s,
                        biweekly_override=%s,
                        note=%s,
                        recurrence_id=%s,
                        sync_from_recurrence=%s,
                        effective_start=%s,
                        effective_end=%s,
                        is_active=TRUE,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (
                        item_type,
                        description,
                        input_frequency,
                        amount,
                        override,
                        note,
                        normalized_recurrence_id,
                        bool(sync_from_recurrence),
                        start_value,
                        end_value,
                        budget_item_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Poste budgétaire introuvable.")
                saved_id = int(budget_item_id)
            else:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(sort_order),0)+1 AS next_order
                    FROM finance_budget_items
                    WHERE user_id=%s AND item_type=%s;
                    """,
                    (user_id, item_type),
                )
                next_order = int(cur.fetchone()["next_order"])
                cur.execute(
                    """
                    INSERT INTO finance_budget_items (
                        user_id,
                        item_type,
                        description,
                        input_frequency,
                        input_amount,
                        biweekly_override,
                        note,
                        sort_order,
                        recurrence_id,
                        sync_from_recurrence,
                        effective_start,
                        effective_end
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                    """,
                    (
                        user_id,
                        item_type,
                        description,
                        input_frequency,
                        amount,
                        override,
                        note,
                        next_order,
                        normalized_recurrence_id,
                        bool(sync_from_recurrence),
                        start_value,
                        end_value,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            # Synchronisation explicite demandée : lorsque le lien est actif,
            # la date de fin du Budget devient aussi la date de fin de la règle.
            # Les transactions confirmées restent intactes; seules les
            # occurrences prévues postérieures sont retirées.
            if normalized_recurrence_id is not None and sync_from_recurrence:
                cur.execute(
                    """
                    UPDATE finance_recurrences
                    SET end_date=%s,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (end_value, normalized_recurrence_id, user_id),
                )
                if end_value is not None:
                    cur.execute(
                        """
                        DELETE FROM finance_transactions
                        WHERE user_id=%s
                          AND recurrence_id=%s
                          AND status='planned'
                          AND transaction_date>%s;
                        """,
                        (user_id, normalized_recurrence_id, end_value),
                    )

            conn.commit()
            return saved_id


def save_financing_budget_group(
    user_id, *, description, plan_ids, budget_item_id=None, effective_start=None, effective_end=None, note=None,
    get_connection, _text, _optional_date_value, _financing_group_amount_for_month, date,
):
    description = _text(description, "Le nom du groupe", 160, True)
    selected = sorted({int(value) for value in (plan_ids or [])})
    if not selected:
        raise ValueError("Sélectionnez au moins un financement.")
    start_value = _optional_date_value(effective_start, "La date de début")
    end_value = _optional_date_value(effective_end, "La date de fin")
    if start_value and end_value and end_value < start_value:
        raise ValueError("La date de fin doit être après la date de début.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM finance_installment_plans
                WHERE user_id=%s AND id=ANY(%s);
                """,
                (user_id, selected),
            )
            valid = {int(row["id"]) for row in cur.fetchall()}
            if valid != set(selected):
                raise ValueError("Un financement sélectionné est introuvable.")

            cur.execute(
                """
                SELECT link.plan_id, budget.description
                FROM finance_budget_financing_group_plans AS link
                JOIN finance_budget_financing_groups AS group_row
                  ON group_row.budget_item_id=link.budget_item_id
                JOIN finance_budget_items AS budget
                  ON budget.id=link.budget_item_id
                WHERE group_row.user_id=%s
                  AND link.plan_id=ANY(%s)
                  AND (%s::BIGINT IS NULL OR link.budget_item_id<>%s::BIGINT);
                """,
                (user_id, selected, budget_item_id, budget_item_id),
            )
            conflicts = cur.fetchall()
            if conflicts:
                names = ", ".join(str(row["description"]) for row in conflicts)
                raise ValueError(
                    "Un financement est déjà associé à un autre groupe Budget : " + names
                )

            # Le montant stocké sert uniquement de valeur de repli; list_budget_items
            # le remplace dynamiquement selon les échéances du mois consulté.
            month = _month_start(start_value or date.today())
            fallback_amount = _financing_group_amount_for_month(
                cur, user_id, selected, month
            )
            if fallback_amount <= 0:
                fallback_amount = Decimal("0.01")

            if budget_item_id:
                cur.execute(
                    """
                    UPDATE finance_budget_items
                    SET description=%s, item_type='expense', input_frequency='monthly',
                        input_amount=%s, biweekly_override=NULL, note=%s,
                        recurrence_id=NULL, sync_from_recurrence=FALSE,
                        effective_start=%s, effective_end=%s,
                        is_active=TRUE, updated_at=NOW()
                    WHERE id=%s AND user_id=%s
                    RETURNING id;
                    """,
                    (
                        description,
                        fallback_amount,
                        _text(note, "La note", 1000),
                        start_value,
                        end_value,
                        int(budget_item_id),
                        user_id,
                    ),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Groupe Budget introuvable.")
                saved_id = int(row["id"])
            else:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(sort_order),0)+1 AS next_order
                    FROM finance_budget_items
                    WHERE user_id=%s AND item_type='expense';
                    """,
                    (user_id,),
                )
                next_order = int(cur.fetchone()["next_order"])
                cur.execute(
                    """
                    INSERT INTO finance_budget_items (
                        user_id,item_type,description,input_frequency,input_amount,
                        note,sort_order,effective_start,effective_end,is_active
                    )
                    VALUES (%s,'expense',%s,'monthly',%s,%s,%s,%s,%s,TRUE)
                    RETURNING id;
                    """,
                    (
                        user_id,
                        description,
                        fallback_amount,
                        _text(note, "La note", 1000),
                        next_order,
                        start_value,
                        end_value,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            cur.execute(
                """
                INSERT INTO finance_budget_financing_groups (budget_item_id,user_id)
                VALUES (%s,%s)
                ON CONFLICT (budget_item_id) DO UPDATE SET
                    user_id=EXCLUDED.user_id, updated_at=NOW();
                """,
                (saved_id, user_id),
            )
            cur.execute(
                "DELETE FROM finance_budget_financing_group_plans WHERE budget_item_id=%s;",
                (saved_id,),
            )
            for plan_id in selected:
                cur.execute(
                    """
                    INSERT INTO finance_budget_financing_group_plans (budget_item_id,plan_id)
                    VALUES (%s,%s);
                    """,
                    (saved_id, plan_id),
                )
            conn.commit()
            return saved_id


def delete_financing_budget_group(
    user_id, budget_item_id, *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM finance_budget_items
                WHERE id=%s AND user_id=%s
                  AND EXISTS (
                    SELECT 1 FROM finance_budget_financing_groups AS group_row
                    WHERE group_row.budget_item_id=finance_budget_items.id
                  );
                """,
                (int(budget_item_id), user_id),
            )
            count = cur.rowcount
            conn.commit()
            return count
