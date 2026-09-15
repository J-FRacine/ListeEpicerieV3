"""Migration automatique des objets magiques JDR — Phase 14."""
from __future__ import annotations

_schema_ready = False


def ensure_magic_item_schema(*, get_connection):
    global _schema_ready
    if _schema_ready:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rpg_character_magic_item_details (
                    equipment_id BIGINT PRIMARY KEY
                        REFERENCES rpg_character_equipment(id)
                        ON DELETE CASCADE,
                    magic_template_key TEXT,
                    magic_kind TEXT NOT NULL DEFAULT 'other'
                        CHECK (magic_kind IN (
                            'passive','charges','activatable','container','other'
                        )),
                    requires_equipped BOOLEAN NOT NULL DEFAULT FALSE,
                    resistance_bonus INTEGER NOT NULL DEFAULT 0
                        CHECK (resistance_bonus BETWEEN 0 AND 20),
                    charges_current INTEGER,
                    charges_max INTEGER,
                    contained_spell_name TEXT,
                    caster_level INTEGER,
                    activation_text TEXT,
                    capacity_weight NUMERIC(10, 3),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (
                        charges_current IS NULL
                        OR charges_current BETWEEN 0 AND 100000
                    ),
                    CHECK (
                        charges_max IS NULL
                        OR charges_max BETWEEN 0 AND 100000
                    ),
                    CHECK (
                        charges_current IS NULL
                        OR charges_max IS NULL
                        OR charges_current <= charges_max
                    ),
                    CHECK (
                        caster_level IS NULL
                        OR caster_level BETWEEN 0 AND 100
                    ),
                    CHECK (
                        capacity_weight IS NULL
                        OR capacity_weight BETWEEN 0 AND 100000
                    )
                );

                CREATE TABLE IF NOT EXISTS rpg_character_equipment_containment (
                    equipment_id BIGINT PRIMARY KEY
                        REFERENCES rpg_character_equipment(id)
                        ON DELETE CASCADE,
                    container_equipment_id BIGINT NOT NULL
                        REFERENCES rpg_character_equipment(id)
                        ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (equipment_id <> container_equipment_id)
                );

                CREATE INDEX IF NOT EXISTS
                    rpg_equipment_containment_container_idx
                ON rpg_character_equipment_containment (
                    container_equipment_id, equipment_id
                );
                """
            )
            conn.commit()

    _schema_ready = True
