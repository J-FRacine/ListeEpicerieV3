"""Migration automatique pour les armes détaillées et leurs liens."""
from __future__ import annotations

_schema_ready = False

def ensure_weapon_schema(*, get_connection):
    global _schema_ready
    if _schema_ready:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rpg_character_weapon_details (
                    equipment_id BIGINT PRIMARY KEY
                        REFERENCES rpg_character_equipment(id)
                        ON DELETE CASCADE,
                    weapon_template_key TEXT,
                    weapon_damage TEXT,
                    weapon_critical TEXT,
                    weapon_damage_type TEXT,
                    weapon_range TEXT,
                    weapon_handedness TEXT NOT NULL DEFAULT 'one_handed'
                        CHECK (weapon_handedness IN (
                            'light','one_handed','two_handed','ranged','other'
                        )),
                    weapon_masterwork BOOLEAN NOT NULL DEFAULT FALSE,
                    weapon_enhancement_bonus INTEGER NOT NULL DEFAULT 0
                        CHECK (weapon_enhancement_bonus BETWEEN 0 AND 20),
                    weapon_ammunition_type TEXT,
                    weapon_ammunition_current INTEGER,
                    weapon_ammunition_max INTEGER,
                    weapon_proficiency_required TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (
                        weapon_ammunition_current IS NULL
                        OR weapon_ammunition_current BETWEEN 0 AND 100000
                    ),
                    CHECK (
                        weapon_ammunition_max IS NULL
                        OR weapon_ammunition_max BETWEEN 0 AND 100000
                    )
                );

                CREATE TABLE IF NOT EXISTS rpg_character_attack_weapon_links (
                    attack_id BIGINT PRIMARY KEY
                        REFERENCES rpg_character_attacks(id)
                        ON DELETE CASCADE,
                    equipment_id BIGINT NOT NULL
                        REFERENCES rpg_character_equipment(id)
                        ON DELETE CASCADE,
                    grip_mode TEXT NOT NULL DEFAULT 'default'
                        CHECK (grip_mode IN (
                            'default','one_handed','two_handed'
                        )),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS
                    rpg_attack_weapon_links_equipment_idx
                ON rpg_character_attack_weapon_links (
                    equipment_id, attack_id
                );
                """
            )
            conn.commit()
    _schema_ready = True
