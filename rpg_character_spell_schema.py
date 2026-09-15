"""Migration automatique de la préparation des sorts JDR — Phase 15A."""
from __future__ import annotations

_schema_ready = False


def ensure_spell_schema(*, get_connection):
    global _schema_ready
    if _schema_ready:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rpg_character_spellcasting_profiles (
                    character_id BIGINT PRIMARY KEY
                        REFERENCES rpg_characters(id)
                        ON DELETE CASCADE,
                    class_key TEXT NOT NULL DEFAULT 'cleric',
                    class_level INTEGER NOT NULL DEFAULT 1
                        CHECK (class_level BETWEEN 1 AND 20),
                    caster_level INTEGER NOT NULL DEFAULT 1
                        CHECK (caster_level BETWEEN 1 AND 100),
                    ability_key TEXT NOT NULL DEFAULT 'wis'
                        CHECK (ability_key IN ('str','dex','con','int','wis','cha')),
                    spontaneous_mode TEXT NOT NULL DEFAULT 'cure'
                        CHECK (spontaneous_mode IN ('cure','inflict','none')),
                    preparation_notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS rpg_character_prepared_spells (
                    id BIGSERIAL PRIMARY KEY,
                    character_id BIGINT NOT NULL
                        REFERENCES rpg_characters(id)
                        ON DELETE CASCADE,
                    catalog_key TEXT,
                    spell_name TEXT NOT NULL,
                    spell_level INTEGER NOT NULL
                        CHECK (spell_level BETWEEN 0 AND 9),
                    slot_kind TEXT NOT NULL DEFAULT 'normal'
                        CHECK (slot_kind IN ('normal','domain')),
                    domain_source TEXT,
                    prepared_count INTEGER NOT NULL DEFAULT 1
                        CHECK (prepared_count BETWEEN 1 AND 100),
                    used_count INTEGER NOT NULL DEFAULT 0
                        CHECK (used_count BETWEEN 0 AND 100),
                    school TEXT,
                    range_text TEXT,
                    summary TEXT,
                    source_text TEXT,
                    notes TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (used_count <= prepared_count),
                    CHECK (spell_level > 0 OR slot_kind = 'normal'),
                    CHECK (spell_level > 0 OR used_count = 0)
                );

                CREATE INDEX IF NOT EXISTS rpg_prepared_spells_character_idx
                ON rpg_character_prepared_spells (
                    character_id,
                    spell_level,
                    slot_kind,
                    sort_order,
                    spell_name,
                    id
                );
                """
            )
            conn.commit()

    _schema_ready = True
