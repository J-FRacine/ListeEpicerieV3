"""Migration de compatibilité pour la table d'équipement JDR.

La table ``rpg_character_equipment`` existait avant certains champs détaillés.
Cette migration ajoute uniquement les colonnes manquantes et ne supprime aucune
donnée. La connexion PostgreSQL est injectée afin de garder ce module testable.
"""
from __future__ import annotations


_schema_ready = False


def ensure_equipment_schema(*, get_connection):
    """Ajoute de façon idempotente les colonnes d'équipement manquantes."""
    global _schema_ready
    if _schema_ready:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS item_type TEXT NOT NULL DEFAULT 'gear';
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS quantity INTEGER NOT NULL DEFAULT 1;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS weight_each NUMERIC(10, 3) NOT NULL DEFAULT 0;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS value_text TEXT;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS notes TEXT;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS carried BOOLEAN NOT NULL DEFAULT TRUE;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS equipped BOOLEAN NOT NULL DEFAULT FALSE;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS armor_category TEXT NOT NULL DEFAULT 'none';
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS armor_bonus INTEGER NOT NULL DEFAULT 0;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS shield_bonus INTEGER NOT NULL DEFAULT 0;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS enhancement_bonus INTEGER NOT NULL DEFAULT 0;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS max_dex_bonus INTEGER;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS armor_check_penalty INTEGER NOT NULL DEFAULT 0;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS arcane_spell_failure INTEGER NOT NULL DEFAULT 0;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS speed_reduction_applies BOOLEAN NOT NULL DEFAULT FALSE;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS reduced_speed_override INTEGER;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS proficiency_required TEXT;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
                ALTER TABLE rpg_character_equipment
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

                CREATE INDEX IF NOT EXISTS
                    rpg_character_equipment_character_idx
                ON rpg_character_equipment (
                    character_id,
                    item_type,
                    sort_order,
                    id
                );
                """
            )
            conn.commit()

    _schema_ready = True
