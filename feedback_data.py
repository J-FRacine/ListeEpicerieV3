from __future__ import annotations

from db import get_connection


FEEDBACK_APP_LABELS = {
    "portal": "Portail JF Apps",
    "grocery": "Liste d’épicerie",
    "blood_pressure": "Journal de pression",
    "finances": "Finances",
    "rpg": "Personnages JDR",
    "help": "Manuel et aide",
    "other": "Autre",
}

FEEDBACK_STATUS_LABELS = {
    "new": "Nouveau",
    "study": "À l’étude",
    "planned": "Planifié",
    "in_progress": "En cours",
    "completed": "Terminé",
    "rejected": "Refusé",
}

CLOSED_FEEDBACK_STATUSES = {
    "completed",
    "rejected",
}

MAX_SUBJECT_LENGTH = 160
MAX_DETAIL_LENGTH = 5000
MAX_REPLY_LENGTH = 5000


def _normalize_text(
    value,
    *,
    label,
    maximum,
    required=False,
):
    text = str(
        value
        or ""
    ).strip()

    if required and not text:
        raise ValueError(
            f"{label} est obligatoire."
        )

    if len(text) > maximum:
        raise ValueError(
            f"{label} ne peut pas dépasser "
            f"{maximum} caractères."
        )

    return text or None


def _normalize_app_key(
    value,
):
    key = str(
        value
        or ""
    ).strip().lower()

    if key not in FEEDBACK_APP_LABELS:
        raise ValueError(
            "Choisissez l’application concernée."
        )

    return key


def _normalize_status(
    value,
):
    status = str(
        value
        or ""
    ).strip().lower()

    if status not in FEEDBACK_STATUS_LABELS:
        raise ValueError(
            "Le statut sélectionné est invalide."
        )

    return status


def _record_feedback_event(
    cur,
    *,
    feedback_id,
    actor_user_id,
    event_type,
    summary,
):
    cur.execute(
        """
        INSERT INTO user_feedback_events (
            feedback_id,
            actor_user_id,
            event_type,
            summary
        )
        VALUES (
            %s,
            %s,
            %s,
            %s
        );
        """,
        (
            feedback_id,
            actor_user_id,
            event_type,
            summary,
        ),
    )


def init_feedback_schema():
    """Crée les tables de commentaires et de suivi."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                user_feedback (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    app_key TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    status TEXT NOT NULL
                        DEFAULT 'new'
                        CHECK (
                            status IN (
                                'new',
                                'study',
                                'planned',
                                'in_progress',
                                'completed',
                                'rejected'
                            )
                        ),
                    manager_reply TEXT,
                    manager_user_id INTEGER
                        REFERENCES users(id)
                        ON DELETE SET NULL,
                    user_reply_unread BOOLEAN
                        NOT NULL DEFAULT FALSE,
                    manager_unread BOOLEAN
                        NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    replied_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ,
                    CHECK (
                        CHAR_LENGTH(subject)
                        BETWEEN 1 AND 160
                    ),
                    CHECK (
                        CHAR_LENGTH(detail)
                        BETWEEN 1 AND 5000
                    ),
                    CHECK (
                        manager_reply IS NULL
                        OR CHAR_LENGTH(manager_reply)
                        <= 5000
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                user_feedback_user_idx
                ON user_feedback (
                    user_id,
                    updated_at DESC,
                    id DESC
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                user_feedback_admin_idx
                ON user_feedback (
                    status,
                    manager_unread,
                    updated_at DESC
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                user_feedback_events (
                    id BIGSERIAL PRIMARY KEY,
                    feedback_id BIGINT NOT NULL
                        REFERENCES user_feedback(id)
                        ON DELETE CASCADE,
                    actor_user_id INTEGER
                        REFERENCES users(id)
                        ON DELETE SET NULL,
                    event_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                user_feedback_events_feedback_idx
                ON user_feedback_events (
                    feedback_id,
                    created_at,
                    id
                );
                """
            )

            conn.commit()


def create_feedback(
    user_id,
    *,
    app_key,
    subject,
    detail,
):
    normalized_app = _normalize_app_key(
        app_key
    )
    normalized_subject = _normalize_text(
        subject,
        label="Le sujet",
        maximum=MAX_SUBJECT_LENGTH,
        required=True,
    )
    normalized_detail = _normalize_text(
        detail,
        label="Le commentaire",
        maximum=MAX_DETAIL_LENGTH,
        required=True,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_feedback (
                    user_id,
                    app_key,
                    subject,
                    detail
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id;
                """,
                (
                    user_id,
                    normalized_app,
                    normalized_subject,
                    normalized_detail,
                ),
            )

            feedback_id = cur.fetchone()[
                "id"
            ]

            _record_feedback_event(
                cur,
                feedback_id=feedback_id,
                actor_user_id=user_id,
                event_type="created",
                summary=(
                    "Commentaire créé par l’utilisateur."
                ),
            )

            conn.commit()

    return feedback_id


def list_user_feedback(
    user_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    feedback.*,
                    manager.display_name
                        AS manager_name
                FROM user_feedback AS feedback
                LEFT JOIN users AS manager
                    ON manager.id =
                        feedback.manager_user_id
                WHERE feedback.user_id = %s
                ORDER BY
                    feedback.user_reply_unread DESC,
                    feedback.updated_at DESC,
                    feedback.id DESC;
                """,
                (user_id,),
            )

            return cur.fetchall()


def get_user_feedback(
    user_id,
    feedback_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    feedback.*,
                    manager.display_name
                        AS manager_name
                FROM user_feedback AS feedback
                LEFT JOIN users AS manager
                    ON manager.id =
                        feedback.manager_user_id
                WHERE feedback.id = %s
                  AND feedback.user_id = %s;
                """,
                (
                    feedback_id,
                    user_id,
                ),
            )

            row = cur.fetchone()

    if row is None:
        raise ValueError(
            "Ce commentaire n’existe plus "
            "ou ne vous appartient pas."
        )

    return row


def update_user_feedback(
    user_id,
    feedback_id,
    *,
    app_key,
    subject,
    detail,
):
    normalized_app = _normalize_app_key(
        app_key
    )
    normalized_subject = _normalize_text(
        subject,
        label="Le sujet",
        maximum=MAX_SUBJECT_LENGTH,
        required=True,
    )
    normalized_detail = _normalize_text(
        detail,
        label="Le commentaire",
        maximum=MAX_DETAIL_LENGTH,
        required=True,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM user_feedback
                WHERE id = %s
                  AND user_id = %s
                FOR UPDATE;
                """,
                (
                    feedback_id,
                    user_id,
                ),
            )

            current = cur.fetchone()

            if current is None:
                raise ValueError(
                    "Ce commentaire n’existe plus "
                    "ou ne vous appartient pas."
                )

            if (
                current["status"]
                in CLOSED_FEEDBACK_STATUSES
            ):
                raise ValueError(
                    "Un commentaire terminé ou refusé "
                    "ne peut plus être modifié."
                )

            cur.execute(
                """
                UPDATE user_feedback
                SET
                    app_key = %s,
                    subject = %s,
                    detail = %s,
                    manager_unread = TRUE,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                (
                    normalized_app,
                    normalized_subject,
                    normalized_detail,
                    feedback_id,
                    user_id,
                ),
            )

            _record_feedback_event(
                cur,
                feedback_id=feedback_id,
                actor_user_id=user_id,
                event_type="user_edit",
                summary=(
                    "Commentaire modifié par l’utilisateur."
                ),
            )

            conn.commit()


def mark_feedback_user_read(
    user_id,
    feedback_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_feedback
                SET user_reply_unread = FALSE
                WHERE id = %s
                  AND user_id = %s;
                """,
                (
                    feedback_id,
                    user_id,
                ),
            )
            conn.commit()


def count_user_unread_feedback(
    user_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM user_feedback
                WHERE user_id = %s
                  AND user_reply_unread = TRUE;
                """,
                (user_id,),
            )

            return int(
                cur.fetchone()["total"]
            )


def list_feedback_for_admin(
    *,
    status=None,
    app_key=None,
    query=None,
):
    conditions = []
    params = []

    if status:
        conditions.append(
            "feedback.status = %s"
        )
        params.append(
            _normalize_status(
                status
            )
        )

    if app_key:
        conditions.append(
            "feedback.app_key = %s"
        )
        params.append(
            _normalize_app_key(
                app_key
            )
        )

    normalized_query = str(
        query
        or ""
    ).strip()

    if normalized_query:
        conditions.append(
            """
            (
                LOWER(feedback.subject)
                    LIKE LOWER(%s)
                OR LOWER(feedback.detail)
                    LIKE LOWER(%s)
                OR LOWER(author.display_name)
                    LIKE LOWER(%s)
                OR LOWER(author.email)
                    LIKE LOWER(%s)
            )
            """
        )
        pattern = (
            f"%{normalized_query}%"
        )
        params.extend(
            [
                pattern,
                pattern,
                pattern,
                pattern,
            ]
        )

    where_sql = (
        "WHERE "
        + " AND ".join(
            conditions
        )
        if conditions
        else ""
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    feedback.*,
                    author.display_name
                        AS author_name,
                    author.email
                        AS author_email,
                    manager.display_name
                        AS manager_name
                FROM user_feedback AS feedback
                JOIN users AS author
                    ON author.id =
                        feedback.user_id
                LEFT JOIN users AS manager
                    ON manager.id =
                        feedback.manager_user_id
                {where_sql}
                ORDER BY
                    feedback.manager_unread DESC,
                    CASE feedback.status
                        WHEN 'new' THEN 1
                        WHEN 'study' THEN 2
                        WHEN 'planned' THEN 3
                        WHEN 'in_progress' THEN 4
                        WHEN 'completed' THEN 5
                        WHEN 'rejected' THEN 6
                        ELSE 7
                    END,
                    feedback.updated_at DESC,
                    feedback.id DESC;
                """,
                params,
            )

            return cur.fetchall()


def get_feedback_for_admin(
    feedback_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    feedback.*,
                    author.display_name
                        AS author_name,
                    author.email
                        AS author_email,
                    manager.display_name
                        AS manager_name
                FROM user_feedback AS feedback
                JOIN users AS author
                    ON author.id =
                        feedback.user_id
                LEFT JOIN users AS manager
                    ON manager.id =
                        feedback.manager_user_id
                WHERE feedback.id = %s;
                """,
                (feedback_id,),
            )

            row = cur.fetchone()

    if row is None:
        raise ValueError(
            "Ce commentaire n’existe plus."
        )

    return row


def mark_feedback_manager_read(
    feedback_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_feedback
                SET manager_unread = FALSE
                WHERE id = %s;
                """,
                (feedback_id,),
            )
            conn.commit()


def update_feedback_by_manager(
    feedback_id,
    *,
    manager_user_id,
    status,
    manager_reply,
):
    normalized_status = _normalize_status(
        status
    )
    normalized_reply = _normalize_text(
        manager_reply,
        label="La réponse",
        maximum=MAX_REPLY_LENGTH,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    status,
                    manager_reply
                FROM user_feedback
                WHERE id = %s
                FOR UPDATE;
                """,
                (feedback_id,),
            )

            current = cur.fetchone()

            if current is None:
                raise ValueError(
                    "Ce commentaire n’existe plus."
                )

            status_changed = (
                current["status"]
                != normalized_status
            )
            reply_changed = (
                (
                    current[
                        "manager_reply"
                    ]
                    or ""
                )
                != (
                    normalized_reply
                    or ""
                )
            )
            user_has_update = (
                status_changed
                or reply_changed
            )

            cur.execute(
                """
                UPDATE user_feedback
                SET
                    status = %s,
                    manager_reply = %s,
                    manager_user_id = %s,
                    manager_unread = FALSE,
                    user_reply_unread = (
                        CASE
                            WHEN %s
                            THEN TRUE
                            ELSE user_reply_unread
                        END
                    ),
                    replied_at = (
                        CASE
                            WHEN %s
                                 AND %s IS NOT NULL
                            THEN NOW()
                            ELSE replied_at
                        END
                    ),
                    completed_at = (
                        CASE
                            WHEN %s = 'completed'
                            THEN COALESCE(
                                completed_at,
                                NOW()
                            )
                            ELSE NULL
                        END
                    ),
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (
                    normalized_status,
                    normalized_reply,
                    manager_user_id,
                    user_has_update,
                    reply_changed,
                    normalized_reply,
                    normalized_status,
                    feedback_id,
                ),
            )

            event_parts = []

            if status_changed:
                event_parts.append(
                    (
                        "statut : "
                        f"{FEEDBACK_STATUS_LABELS[current['status']]} "
                        "→ "
                        f"{FEEDBACK_STATUS_LABELS[normalized_status]}"
                    )
                )

            if reply_changed:
                event_parts.append(
                    "réponse du gestionnaire mise à jour"
                )

            summary = (
                "Mise à jour par le gestionnaire"
                + (
                    " — "
                    + "; ".join(
                        event_parts
                    )
                    if event_parts
                    else ""
                )
                + "."
            )

            _record_feedback_event(
                cur,
                feedback_id=feedback_id,
                actor_user_id=manager_user_id,
                event_type="manager_update",
                summary=summary,
            )

            conn.commit()


def count_feedback_attention():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM user_feedback
                WHERE manager_unread = TRUE
                   OR status = 'new';
                """
            )

            return int(
                cur.fetchone()["total"]
            )


def list_feedback_events(
    feedback_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    event.id,
                    event.event_type,
                    event.summary,
                    event.created_at,
                    actor.display_name
                        AS actor_name
                FROM user_feedback_events AS event
                LEFT JOIN users AS actor
                    ON actor.id =
                        event.actor_user_id
                WHERE event.feedback_id = %s
                ORDER BY
                    event.created_at,
                    event.id;
                """,
                (feedback_id,),
            )

            return cur.fetchall()
