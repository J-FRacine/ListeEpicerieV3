from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush

from blood_pressure_data import (
    count_blood_pressure_readings_on_date,
    get_blood_pressure_reminder_settings,
)
from db import get_connection


PUSH_CHECK_SECONDS = 300
DEFAULT_VAPID_SUBJECT = "mailto:notifications@jfapps.invalid"

_PUSH_TASK = None


def _base64url(data: bytes) -> str:
    return (
        base64.urlsafe_b64encode(data)
        .rstrip(b"=")
        .decode("ascii")
    )


def _generate_vapid_keys():
    private_key = ec.generate_private_key(
        ec.SECP256R1()
    )

    private_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_numbers = (
        private_key.public_key()
        .public_numbers()
    )
    public_raw = (
        b"\x04"
        + public_numbers.x.to_bytes(32, "big")
        + public_numbers.y.to_bytes(32, "big")
    )

    return (
        _base64url(private_der),
        _base64url(public_raw),
    )


def init_blood_pressure_push_schema():
    """Crée le stockage privé des abonnements Web Push."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                blood_pressure_push_config (
                    id SMALLINT PRIMARY KEY
                        DEFAULT 1
                        CHECK (id = 1),
                    vapid_private_key TEXT NOT NULL,
                    vapid_public_key TEXT NOT NULL,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                blood_pressure_push_subscriptions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    endpoint TEXT NOT NULL,
                    p256dh TEXT NOT NULL,
                    auth TEXT NOT NULL,
                    timezone_name TEXT NOT NULL
                        DEFAULT 'UTC',
                    user_agent TEXT,
                    is_active BOOLEAN NOT NULL
                        DEFAULT TRUE,
                    last_success_at TIMESTAMPTZ,
                    last_error TEXT,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    UNIQUE (endpoint)
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                blood_pressure_push_user_idx
                ON blood_pressure_push_subscriptions (
                    user_id,
                    is_active
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                blood_pressure_push_deliveries (
                    id BIGSERIAL PRIMARY KEY,
                    subscription_id BIGINT NOT NULL
                        REFERENCES blood_pressure_push_subscriptions(id)
                        ON DELETE CASCADE,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    reminder_date DATE NOT NULL,
                    slot_id BIGINT
                        REFERENCES blood_pressure_reminder_slots(id)
                        ON DELETE SET NULL,
                    slot_order SMALLINT NOT NULL,
                    status TEXT NOT NULL
                        DEFAULT 'sent'
                        CHECK (
                            status IN (
                                'sent',
                                'skipped_superseded'
                            )
                        ),
                    sent_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    UNIQUE (
                        subscription_id,
                        reminder_date,
                        slot_order
                    )
                );
                """
            )

            cur.execute(
                """
                SELECT
                    vapid_private_key,
                    vapid_public_key
                FROM blood_pressure_push_config
                WHERE id = 1;
                """
            )
            keys = cur.fetchone()

            if not keys:
                (
                    private_key,
                    public_key,
                ) = _generate_vapid_keys()

                cur.execute(
                    """
                    INSERT INTO blood_pressure_push_config (
                        id,
                        vapid_private_key,
                        vapid_public_key
                    )
                    VALUES (
                        1,
                        %s,
                        %s
                    )
                    ON CONFLICT (id)
                    DO NOTHING;
                    """,
                    (
                        private_key,
                        public_key,
                    ),
                )

            conn.commit()


def get_vapid_public_key() -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT vapid_public_key
                FROM blood_pressure_push_config
                WHERE id = 1;
                """
            )
            row = cur.fetchone()

    if not row:
        init_blood_pressure_push_schema()
        return get_vapid_public_key()

    return str(row["vapid_public_key"])


def _get_vapid_private_key() -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT vapid_private_key
                FROM blood_pressure_push_config
                WHERE id = 1;
                """
            )
            row = cur.fetchone()

    if not row:
        init_blood_pressure_push_schema()
        return _get_vapid_private_key()

    return str(row["vapid_private_key"])


def save_push_subscription(
    user_id,
    subscription,
    *,
    timezone_name="UTC",
    user_agent=None,
):
    endpoint = str(
        (subscription or {}).get("endpoint")
        or ""
    ).strip()
    keys = (
        (subscription or {}).get("keys")
        or {}
    )
    p256dh = str(
        keys.get("p256dh")
        or ""
    ).strip()
    auth = str(
        keys.get("auth")
        or ""
    ).strip()

    if not endpoint or not p256dh or not auth:
        raise ValueError(
            "L’abonnement de notification fourni par le navigateur est incomplet."
        )

    timezone_text = str(
        timezone_name
        or "UTC"
    ).strip()

    try:
        ZoneInfo(timezone_text)
    except ZoneInfoNotFoundError:
        timezone_text = "UTC"

    user_agent_text = str(
        user_agent
        or ""
    ).strip()[:500] or None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO
                blood_pressure_push_subscriptions (
                    user_id,
                    endpoint,
                    p256dh,
                    auth,
                    timezone_name,
                    user_agent,
                    is_active,
                    last_error,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE,
                    NULL,
                    NOW()
                )
                ON CONFLICT (endpoint)
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    p256dh = EXCLUDED.p256dh,
                    auth = EXCLUDED.auth,
                    timezone_name = EXCLUDED.timezone_name,
                    user_agent = EXCLUDED.user_agent,
                    is_active = TRUE,
                    last_error = NULL,
                    updated_at = NOW()
                RETURNING id;
                """,
                (
                    user_id,
                    endpoint,
                    p256dh,
                    auth,
                    timezone_text,
                    user_agent_text,
                ),
            )
            row = cur.fetchone()
            conn.commit()

    return int(row["id"])


def deactivate_push_subscription(
    user_id,
    endpoint,
):
    endpoint_text = str(
        endpoint
        or ""
    ).strip()

    if not endpoint_text:
        return False

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE blood_pressure_push_subscriptions
                SET
                    is_active = FALSE,
                    updated_at = NOW()
                WHERE user_id = %s
                  AND endpoint = %s
                RETURNING id;
                """,
                (
                    user_id,
                    endpoint_text,
                ),
            )
            row = cur.fetchone()
            conn.commit()

    return row is not None


def list_push_subscriptions(
    user_id,
    *,
    include_inactive=False,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    endpoint,
                    timezone_name,
                    user_agent,
                    is_active,
                    last_success_at,
                    last_error,
                    created_at,
                    updated_at
                FROM blood_pressure_push_subscriptions
                WHERE user_id = %s
                  AND (
                    %s
                    OR is_active = TRUE
                  )
                ORDER BY
                    is_active DESC,
                    updated_at DESC,
                    id DESC;
                """,
                (
                    user_id,
                    bool(include_inactive),
                ),
            )
            return cur.fetchall()


def count_active_push_subscriptions(
    user_id,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM blood_pressure_push_subscriptions
                WHERE user_id = %s
                  AND is_active = TRUE;
                """,
                (user_id,),
            )
            row = cur.fetchone()
    return int(row["total"] if row else 0)


def _active_subscriptions():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    user_id,
                    endpoint,
                    p256dh,
                    auth,
                    timezone_name,
                    user_agent
                FROM blood_pressure_push_subscriptions
                WHERE is_active = TRUE
                ORDER BY user_id, id;
                """
            )
            return cur.fetchall()


def _delivery_exists(
    subscription_id,
    reminder_date,
    slot_order,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM blood_pressure_push_deliveries
                WHERE subscription_id = %s
                  AND reminder_date = %s
                  AND slot_order = %s;
                """,
                (
                    subscription_id,
                    reminder_date,
                    slot_order,
                ),
            )
            return cur.fetchone() is not None


def _record_delivery(
    subscription_id,
    user_id,
    reminder_date,
    slot,
    status,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO blood_pressure_push_deliveries (
                    subscription_id,
                    user_id,
                    reminder_date,
                    slot_id,
                    slot_order,
                    status
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT (
                    subscription_id,
                    reminder_date,
                    slot_order
                )
                DO NOTHING;
                """,
                (
                    subscription_id,
                    user_id,
                    reminder_date,
                    slot.get("id"),
                    slot["sort_order"],
                    status,
                ),
            )
            conn.commit()


def _mark_subscription_success(
    subscription_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE blood_pressure_push_subscriptions
                SET
                    last_success_at = NOW(),
                    last_error = NULL,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (subscription_id,),
            )
            conn.commit()


def _mark_subscription_error(
    subscription_id,
    error,
    *,
    deactivate=False,
):
    message = str(error or "")[:1000]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE blood_pressure_push_subscriptions
                SET
                    last_error = %s,
                    is_active = CASE
                        WHEN %s
                        THEN FALSE
                        ELSE is_active
                    END,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (
                    message,
                    bool(deactivate),
                    subscription_id,
                ),
            )
            conn.commit()


def _due_slots_for_subscription(
    subscription,
    now_utc,
):
    timezone_name = (
        subscription.get("timezone_name")
        or "UTC"
    )
    try:
        local_zone = ZoneInfo(
            timezone_name
        )
    except ZoneInfoNotFoundError:
        local_zone = ZoneInfo("UTC")

    local_now = now_utc.astimezone(
        local_zone
    )
    local_date = local_now.date()
    local_time = local_now.time().replace(
        second=0,
        microsecond=0,
    )
    user_id = int(
        subscription["user_id"]
    )

    settings = get_blood_pressure_reminder_settings(
        user_id
    )

    if (
        not settings.get("configured")
        or not settings.get("enabled")
        or not settings.get("start_date")
        or not settings.get("end_date")
        or not (
            settings["start_date"]
            <= local_date
            <= settings["end_date"]
        )
    ):
        return (
            local_date,
            [],
        )

    completed_count = (
        count_blood_pressure_readings_on_date(
            user_id,
            local_date,
        )
    )

    due_slots = []

    for slot in settings.get("slots") or []:
        sort_order = int(
            slot.get("sort_order")
            or 0
        )
        if (
            sort_order <= completed_count
            or not bool(
                slot.get(
                    "notify_enabled",
                    True,
                )
            )
        ):
            continue

        notify_time = (
            slot.get("notify_time")
            or slot["end_time"]
        )
        if local_time < notify_time:
            continue

        if _delivery_exists(
            int(subscription["id"]),
            local_date,
            sort_order,
        ):
            continue

        due_slots.append(
            dict(slot)
        )

    return (
        local_date,
        due_slots,
    )


def process_due_push_notifications(
    now_utc=None,
):
    """Envoie au maximum un avis pertinent par appareil et par passage."""

    current_utc = (
        now_utc
        if isinstance(
            now_utc,
            datetime,
        )
        else datetime.now(
            timezone.utc
        )
    )

    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(
            tzinfo=timezone.utc
        )

    private_key = (
        _get_vapid_private_key()
    )
    vapid_subject = (
        os.getenv(
            "JF_APPS_VAPID_SUBJECT"
        )
        or DEFAULT_VAPID_SUBJECT
    )

    sent = 0
    skipped = 0
    failed = 0

    for subscription in _active_subscriptions():
        (
            local_date,
            due_slots,
        ) = _due_slots_for_subscription(
            subscription,
            current_utc,
        )

        if not due_slots:
            continue

        # Si le service a été interrompu longtemps, ne pas envoyer
        # plusieurs avis d’un coup. On conserve la prise la plus récente.
        due_slots.sort(
            key=lambda slot: (
                slot.get("notify_time")
                or slot["end_time"],
                int(slot["sort_order"]),
            )
        )
        selected = due_slots[-1]

        for old_slot in due_slots[:-1]:
            _record_delivery(
                int(subscription["id"]),
                int(subscription["user_id"]),
                local_date,
                old_slot,
                "skipped_superseded",
            )
            skipped += 1

        payload = json.dumps(
            {
                "title": (
                    "Journal de pression"
                ),
                "body": (
                    "Une mesure est prévue."
                ),
                "url": (
                    "/?tab=pression&section=saisie"
                ),
                "tag": (
                    "jf-pressure-"
                    f"{local_date.isoformat()}-"
                    f"{selected['sort_order']}"
                ),
            },
            ensure_ascii=False,
        )

        try:
            webpush(
                subscription_info={
                    "endpoint": subscription[
                        "endpoint"
                    ],
                    "keys": {
                        "p256dh": subscription[
                            "p256dh"
                        ],
                        "auth": subscription[
                            "auth"
                        ],
                    },
                },
                data=payload,
                vapid_private_key=(
                    private_key
                ),
                vapid_claims={
                    "sub": vapid_subject,
                },
                ttl=3600,
                timeout=15,
            )
        except WebPushException as error:
            response = getattr(
                error,
                "response",
                None,
            )
            status_code = getattr(
                response,
                "status_code",
                None,
            )
            _mark_subscription_error(
                int(subscription["id"]),
                error,
                deactivate=(
                    status_code
                    in {
                        404,
                        410,
                    }
                ),
            )
            failed += 1
            continue
        except Exception as error:
            _mark_subscription_error(
                int(subscription["id"]),
                error,
            )
            failed += 1
            continue

        _record_delivery(
            int(subscription["id"]),
            int(subscription["user_id"]),
            local_date,
            selected,
            "sent",
        )
        _mark_subscription_success(
            int(subscription["id"])
        )
        sent += 1

    return {
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
    }


async def _push_monitor_loop():
    while True:
        try:
            await asyncio.to_thread(
                process_due_push_notifications
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(
                "Journal de pression — "
                "vérification des notifications interrompue :",
                error,
            )

        await asyncio.sleep(
            PUSH_CHECK_SECONDS
        )


def start_blood_pressure_push_monitor():
    """Démarre une seule boucle de vérification dans le processus NiceGUI."""

    global _PUSH_TASK

    if (
        _PUSH_TASK is not None
        and not _PUSH_TASK.done()
    ):
        return _PUSH_TASK

    _PUSH_TASK = asyncio.create_task(
        _push_monitor_loop()
    )
    return _PUSH_TASK
