from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from db import get_connection
from rpg_character_rules import (
    ABILITY_LABELS,
    PATHFINDER_SKILL_KEYS,
    SAVE_DEFINITIONS,
    SIZE_LABELS,
    STANDARD_SKILLS,
)


MAX_TEXT = 1000


def _normalize_text(
    value,
    *,
    label,
    maximum=MAX_TEXT,
    required=False,
):
    text = str(value or "").strip()

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


def _normalize_int(
    value,
    *,
    label,
    minimum=None,
    maximum=None,
    default=0,
):
    if value in (None, ""):
        integer_value = default
    else:
        try:
            integer_value = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{label} doit être un nombre entier."
            ) from error

    if (
        minimum is not None
        and integer_value < minimum
    ):
        raise ValueError(
            f"{label} doit être au moins {minimum}."
        )

    if (
        maximum is not None
        and integer_value > maximum
    ):
        raise ValueError(
            f"{label} ne peut pas dépasser {maximum}."
        )

    return integer_value


def _normalize_optional_int(
    value,
    *,
    label,
    minimum=None,
    maximum=None,
):
    if value in (None, ""):
        return None

    return _normalize_int(
        value,
        label=label,
        minimum=minimum,
        maximum=maximum,
    )


def _normalize_decimal(
    value,
    *,
    label,
    minimum=Decimal("0"),
    maximum=Decimal("999"),
):
    try:
        number = Decimal(
            str(
                value
                if value not in (None, "")
                else 0
            )
        )
    except Exception as error:
        raise ValueError(
            f"{label} doit être un nombre."
        ) from error

    if number < minimum or number > maximum:
        raise ValueError(
            f"{label} doit être compris entre "
            f"{minimum} et {maximum}."
        )

    return number


def _normalize_skill_ranks(
    value,
):
    number = _normalize_decimal(
        value,
        label="Les rangs",
        minimum=Decimal("0"),
        maximum=Decimal("999"),
    )

    if number != number.to_integral():
        raise ValueError(
            "Pathfinder utilise des rangs entiers. "
            "Utilisez 0, 1, 2, 3, etc."
        )

    return number


def _require_character(
    cur,
    user_id,
    character_id,
):
    cur.execute(
        """
        SELECT id
        FROM rpg_characters
        WHERE id = %s
          AND user_id = %s;
        """,
        (
            character_id,
            user_id,
        ),
    )

    if cur.fetchone() is None:
        raise ValueError(
            "Ce personnage n’existe plus "
            "ou ne vous appartient pas."
        )


def init_rpg_character_schema():
    """Crée les tables privées de l'application Personnages JDR."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                rpg_characters (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    character_name TEXT NOT NULL,
                    player_name TEXT,
                    campaign TEXT,
                    class_name TEXT,
                    character_level SMALLINT NOT NULL
                        DEFAULT 1
                        CHECK (
                            character_level
                            BETWEEN 1 AND 100
                        ),
                    race TEXT,
                    alignment TEXT,
                    deity TEXT,
                    size_key TEXT NOT NULL
                        DEFAULT 'medium'
                        CHECK (
                            size_key IN (
                                'fine',
                                'diminutive',
                                'tiny',
                                'small',
                                'medium',
                                'large',
                                'huge',
                                'gargantuan',
                                'colossal'
                            )
                        ),
                    age_text TEXT,
                    gender TEXT,
                    height_text TEXT,
                    weight_text TEXT,
                    eyes TEXT,
                    hair TEXT,
                    skin TEXT,
                    experience_points INTEGER NOT NULL
                        DEFAULT 0
                        CHECK (
                            experience_points >= 0
                        ),

                    str_score SMALLINT NOT NULL
                        DEFAULT 10
                        CHECK (str_score BETWEEN 1 AND 100),
                    dex_score SMALLINT NOT NULL
                        DEFAULT 10
                        CHECK (dex_score BETWEEN 1 AND 100),
                    con_score SMALLINT NOT NULL
                        DEFAULT 10
                        CHECK (con_score BETWEEN 1 AND 100),
                    int_score SMALLINT NOT NULL
                        DEFAULT 10
                        CHECK (int_score BETWEEN 1 AND 100),
                    wis_score SMALLINT NOT NULL
                        DEFAULT 10
                        CHECK (wis_score BETWEEN 1 AND 100),
                    cha_score SMALLINT NOT NULL
                        DEFAULT 10
                        CHECK (cha_score BETWEEN 1 AND 100),

                    str_temp_score SMALLINT,
                    dex_temp_score SMALLINT,
                    con_temp_score SMALLINT,
                    int_temp_score SMALLINT,
                    wis_temp_score SMALLINT,
                    cha_temp_score SMALLINT,

                    max_hp INTEGER NOT NULL DEFAULT 0,
                    current_hp INTEGER NOT NULL DEFAULT 0,
                    nonlethal_damage INTEGER NOT NULL DEFAULT 0,
                    speed TEXT,
                    damage_reduction TEXT,
                    spell_resistance INTEGER,

                    base_attack_bonus INTEGER NOT NULL DEFAULT 0,
                    armor_bonus INTEGER NOT NULL DEFAULT 0,
                    shield_bonus INTEGER NOT NULL DEFAULT 0,
                    natural_armor_bonus INTEGER NOT NULL DEFAULT 0,
                    deflection_bonus INTEGER NOT NULL DEFAULT 0,
                    misc_ac_modifier INTEGER NOT NULL DEFAULT 0,
                    armor_check_penalty INTEGER NOT NULL DEFAULT 0,
                    initiative_misc_modifier INTEGER NOT NULL DEFAULT 0,
                    grapple_misc_modifier INTEGER NOT NULL DEFAULT 0,
                    cmb_misc_modifier INTEGER NOT NULL DEFAULT 0,
                    cmd_misc_modifier INTEGER NOT NULL DEFAULT 0,

                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),

                    CHECK (
                        str_temp_score IS NULL
                        OR str_temp_score BETWEEN 1 AND 100
                    ),
                    CHECK (
                        dex_temp_score IS NULL
                        OR dex_temp_score BETWEEN 1 AND 100
                    ),
                    CHECK (
                        con_temp_score IS NULL
                        OR con_temp_score BETWEEN 1 AND 100
                    ),
                    CHECK (
                        int_temp_score IS NULL
                        OR int_temp_score BETWEEN 1 AND 100
                    ),
                    CHECK (
                        wis_temp_score IS NULL
                        OR wis_temp_score BETWEEN 1 AND 100
                    ),
                    CHECK (
                        cha_temp_score IS NULL
                        OR cha_temp_score BETWEEN 1 AND 100
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                rpg_characters_user_idx
                ON rpg_characters (
                    user_id,
                    character_name,
                    id
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                rpg_character_saves (
                    character_id BIGINT NOT NULL
                        REFERENCES rpg_characters(id)
                        ON DELETE CASCADE,
                    save_key TEXT NOT NULL
                        CHECK (
                            save_key IN (
                                'fortitude',
                                'reflex',
                                'will',
                                'fear',
                                'horror',
                                'madness'
                            )
                        ),
                    base_save INTEGER NOT NULL DEFAULT 0,
                    magic_modifier INTEGER NOT NULL DEFAULT 0,
                    misc_modifier INTEGER NOT NULL DEFAULT 0,
                    temporary_modifier INTEGER NOT NULL DEFAULT 0,
                    conditional_notes TEXT,
                    PRIMARY KEY (
                        character_id,
                        save_key
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                rpg_character_skills (
                    id BIGSERIAL PRIMARY KEY,
                    character_id BIGINT NOT NULL
                        REFERENCES rpg_characters(id)
                        ON DELETE CASCADE,
                    skill_key TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    ability_key TEXT NOT NULL
                        CHECK (
                            ability_key IN (
                                'str',
                                'dex',
                                'con',
                                'int',
                                'wis',
                                'cha'
                            )
                        ),
                    class_skill BOOLEAN NOT NULL
                        DEFAULT FALSE,
                    trained_only BOOLEAN NOT NULL
                        DEFAULT FALSE,
                    armor_check_applies BOOLEAN NOT NULL
                        DEFAULT FALSE,
                    double_armor_penalty BOOLEAN NOT NULL
                        DEFAULT FALSE,
                    ranks NUMERIC(6, 1) NOT NULL
                        DEFAULT 0,
                    misc_modifier INTEGER NOT NULL
                        DEFAULT 0,
                    sort_order INTEGER NOT NULL
                        DEFAULT 0,
                    is_custom BOOLEAN NOT NULL
                        DEFAULT FALSE,
                    UNIQUE (
                        character_id,
                        skill_key
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                rpg_character_skills_character_idx
                ON rpg_character_skills (
                    character_id,
                    sort_order,
                    skill_name
                );
                """
            )

            cur.execute(
                """
                ALTER TABLE rpg_characters
                ADD COLUMN IF NOT EXISTS
                cmb_misc_modifier INTEGER
                NOT NULL DEFAULT 0;
                """
            )

            cur.execute(
                """
                ALTER TABLE rpg_characters
                ADD COLUMN IF NOT EXISTS
                cmd_misc_modifier INTEGER
                NOT NULL DEFAULT 0;
                """
            )

            cur.execute(
                """
                UPDATE rpg_characters
                SET cmb_misc_modifier =
                    grapple_misc_modifier
                WHERE cmb_misc_modifier = 0
                  AND grapple_misc_modifier <> 0;
                """
            )

            pathfinder_keys = sorted(
                PATHFINDER_SKILL_KEYS
            )
            placeholders = ", ".join(
                ["%s"] * len(
                    pathfinder_keys
                )
            )

            # Les anciennes compétences D&D 3.5 ayant des données
            # sont conservées comme compétences personnalisées.
            cur.execute(
                f"""
                UPDATE rpg_character_skills
                SET
                    skill_key =
                        'legacy_35_' || id::TEXT,
                    skill_name =
                        skill_name
                        || ' (ancienne 3.5)',
                    is_custom = TRUE,
                    sort_order =
                        sort_order + 1000
                WHERE is_custom = FALSE
                  AND skill_key NOT IN (
                      {placeholders}
                  )
                  AND (
                      ranks <> 0
                      OR misc_modifier <> 0
                      OR class_skill = TRUE
                  );
                """,
                pathfinder_keys,
            )

            # Les anciennes lignes vides sont remplacées par
            # la liste standard Pathfinder.
            cur.execute(
                f"""
                DELETE FROM rpg_character_skills
                WHERE is_custom = FALSE
                  AND skill_key NOT IN (
                      {placeholders}
                  )
                  AND ranks = 0
                  AND misc_modifier = 0
                  AND class_skill = FALSE;
                """,
                pathfinder_keys,
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                rpg_character_attacks (
                    id BIGSERIAL PRIMARY KEY,
                    character_id BIGINT NOT NULL
                        REFERENCES rpg_characters(id)
                        ON DELETE CASCADE,
                    attack_name TEXT NOT NULL,
                    ability_key TEXT NOT NULL
                        DEFAULT 'str'
                        CHECK (
                            ability_key IN (
                                'str',
                                'dex',
                                'con',
                                'int',
                                'wis',
                                'cha'
                            )
                        ),
                    magic_bonus INTEGER NOT NULL DEFAULT 0,
                    misc_bonus INTEGER NOT NULL DEFAULT 0,
                    damage TEXT,
                    critical TEXT,
                    attack_range TEXT,
                    attack_type TEXT,
                    notes TEXT,
                    ammunition_current INTEGER,
                    ammunition_max INTEGER,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                rpg_character_attacks_character_idx
                ON rpg_character_attacks (
                    character_id,
                    sort_order,
                    id
                );
                """
            )

            conn.commit()


def _initialize_character_rows(
    cur,
    character_id,
):
    cur.executemany(
        """
        INSERT INTO rpg_character_saves (
            character_id,
            save_key
        )
        VALUES (%s, %s)
        ON CONFLICT (
            character_id,
            save_key
        ) DO NOTHING;
        """,
        [
            (
                character_id,
                save_key,
            )
            for save_key
            in SAVE_DEFINITIONS
        ],
    )

    cur.executemany(
        """
        UPDATE rpg_character_skills
        SET
            skill_name = %s,
            ability_key = %s,
            trained_only = %s,
            armor_check_applies = %s,
            double_armor_penalty = %s,
            sort_order = %s
        WHERE character_id = %s
          AND skill_key = %s
          AND is_custom = FALSE;
        """,
        [
            (
                skill_name,
                ability_key,
                trained_only,
                armor_check,
                double_penalty,
                index,
                character_id,
                skill_key,
            )
            for index, (
                skill_key,
                skill_name,
                ability_key,
                armor_check,
                trained_only,
                double_penalty,
            )
            in enumerate(
                STANDARD_SKILLS,
                start=1,
            )
        ],
    )

    cur.executemany(
        """
        INSERT INTO rpg_character_skills (
            character_id,
            skill_key,
            skill_name,
            ability_key,
            trained_only,
            armor_check_applies,
            double_armor_penalty,
            sort_order,
            is_custom
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            FALSE
        )
        ON CONFLICT (
            character_id,
            skill_key
        ) DO NOTHING;
        """,
        [
            (
                character_id,
                skill_key,
                skill_name,
                ability_key,
                trained_only,
                armor_check,
                double_penalty,
                index,
            )
            for index, (
                skill_key,
                skill_name,
                ability_key,
                armor_check,
                trained_only,
                double_penalty,
            )
            in enumerate(
                STANDARD_SKILLS,
                start=1,
            )
        ],
    )


def create_rpg_character(
    user_id,
    character_name,
    player_name=None,
):
    name = _normalize_text(
        character_name,
        label="Le nom du personnage",
        maximum=120,
        required=True,
    )
    player = _normalize_text(
        player_name,
        label="Le nom du joueur",
        maximum=120,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rpg_characters (
                    user_id,
                    character_name,
                    player_name
                )
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (
                    user_id,
                    name,
                    player,
                ),
            )

            character_id = cur.fetchone()[
                "id"
            ]

            _initialize_character_rows(
                cur,
                character_id,
            )

            conn.commit()
            return character_id


def list_rpg_characters(
    user_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    character_name,
                    player_name,
                    campaign,
                    class_name,
                    character_level,
                    race,
                    current_hp,
                    max_hp,
                    updated_at
                FROM rpg_characters
                WHERE user_id = %s
                ORDER BY
                    character_name,
                    id;
                """,
                (user_id,),
            )

            return cur.fetchall()


def get_rpg_character(
    user_id,
    character_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM rpg_characters
                WHERE id = %s
                  AND user_id = %s;
                """,
                (
                    character_id,
                    user_id,
                ),
            )

            character = cur.fetchone()

            if character is None:
                raise ValueError(
                    "Ce personnage n’existe plus "
                    "ou ne vous appartient pas."
                )

            _initialize_character_rows(
                cur,
                character_id,
            )
            conn.commit()

            return character


def delete_rpg_character(
    user_id,
    character_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM rpg_characters
                WHERE id = %s
                  AND user_id = %s
                RETURNING id;
                """,
                (
                    character_id,
                    user_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Ce personnage n’existe plus "
                    "ou ne vous appartient pas."
                )

            conn.commit()


def update_rpg_character_identity(
    user_id,
    character_id,
    values,
):
    name = _normalize_text(
        values.get("character_name"),
        label="Le nom du personnage",
        maximum=120,
        required=True,
    )

    normalized = {
        "player_name": _normalize_text(
            values.get("player_name"),
            label="Le nom du joueur",
            maximum=120,
        ),
        "campaign": _normalize_text(
            values.get("campaign"),
            label="La campagne",
            maximum=160,
        ),
        "class_name": _normalize_text(
            values.get("class_name"),
            label="La classe",
            maximum=120,
        ),
        "character_level": _normalize_int(
            values.get("character_level"),
            label="Le niveau",
            minimum=1,
            maximum=100,
            default=1,
        ),
        "race": _normalize_text(
            values.get("race"),
            label="La race",
            maximum=120,
        ),
        "alignment": _normalize_text(
            values.get("alignment"),
            label="L’alignement",
            maximum=80,
        ),
        "deity": _normalize_text(
            values.get("deity"),
            label="La divinité",
            maximum=120,
        ),
        "size_key": str(
            values.get("size_key")
            or "medium"
        ).strip(),
        "age_text": _normalize_text(
            values.get("age_text"),
            label="L’âge",
            maximum=60,
        ),
        "gender": _normalize_text(
            values.get("gender"),
            label="Le genre",
            maximum=80,
        ),
        "height_text": _normalize_text(
            values.get("height_text"),
            label="La taille",
            maximum=60,
        ),
        "weight_text": _normalize_text(
            values.get("weight_text"),
            label="Le poids",
            maximum=60,
        ),
        "eyes": _normalize_text(
            values.get("eyes"),
            label="Les yeux",
            maximum=80,
        ),
        "hair": _normalize_text(
            values.get("hair"),
            label="Les cheveux",
            maximum=80,
        ),
        "skin": _normalize_text(
            values.get("skin"),
            label="La peau",
            maximum=80,
        ),
        "experience_points": _normalize_int(
            values.get("experience_points"),
            label="Les points d’expérience",
            minimum=0,
            maximum=2_000_000_000,
            default=0,
        ),
    }

    if normalized["size_key"] not in SIZE_LABELS:
        raise ValueError(
            "La catégorie de taille est invalide."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                """
                UPDATE rpg_characters
                SET
                    character_name = %s,
                    player_name = %s,
                    campaign = %s,
                    class_name = %s,
                    character_level = %s,
                    race = %s,
                    alignment = %s,
                    deity = %s,
                    size_key = %s,
                    age_text = %s,
                    gender = %s,
                    height_text = %s,
                    weight_text = %s,
                    eyes = %s,
                    hair = %s,
                    skin = %s,
                    experience_points = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                (
                    name,
                    normalized["player_name"],
                    normalized["campaign"],
                    normalized["class_name"],
                    normalized["character_level"],
                    normalized["race"],
                    normalized["alignment"],
                    normalized["deity"],
                    normalized["size_key"],
                    normalized["age_text"],
                    normalized["gender"],
                    normalized["height_text"],
                    normalized["weight_text"],
                    normalized["eyes"],
                    normalized["hair"],
                    normalized["skin"],
                    normalized["experience_points"],
                    character_id,
                    user_id,
                ),
            )

            conn.commit()


def update_rpg_character_combat(
    user_id,
    character_id,
    values,
):
    normalized = {}

    for ability_key in ABILITY_LABELS:
        normalized[f"{ability_key}_score"] = (
            _normalize_int(
                values.get(
                    f"{ability_key}_score"
                ),
                label=(
                    f"Le score {ABILITY_LABELS[ability_key]}"
                ),
                minimum=1,
                maximum=100,
                default=10,
            )
        )
        normalized[f"{ability_key}_temp_score"] = (
            _normalize_optional_int(
                values.get(
                    f"{ability_key}_temp_score"
                ),
                label=(
                    f"Le score temporaire "
                    f"{ABILITY_LABELS[ability_key]}"
                ),
                minimum=1,
                maximum=100,
            )
        )

    integer_fields = {
        "max_hp": ("Les points de vie maximums", -10000, 100000),
        "current_hp": ("Les points de vie actuels", -10000, 100000),
        "nonlethal_damage": ("Les dégâts non létaux", 0, 100000),
        "base_attack_bonus": ("Le bonus de base à l’attaque", -100, 100),
        "armor_bonus": ("Le bonus d’armure", -100, 100),
        "shield_bonus": ("Le bonus de bouclier", -100, 100),
        "natural_armor_bonus": ("Le bonus d’armure naturelle", -100, 100),
        "deflection_bonus": ("Le bonus de déviation", -100, 100),
        "misc_ac_modifier": ("Le modificateur divers de CA", -100, 100),
        "armor_check_penalty": ("La pénalité d’armure", -100, 0),
        "initiative_misc_modifier": (
            "Le modificateur divers d’initiative",
            -100,
            100,
        ),
        "grapple_misc_modifier": (
            "L’ancien modificateur de lutte",
            -100,
            100,
        ),
        "cmb_misc_modifier": (
            "Le modificateur divers de BMO/CMB",
            -100,
            100,
        ),
        "cmd_misc_modifier": (
            "Le modificateur divers de DMD/CMD",
            -100,
            100,
        ),
    }

    for field, (
        label,
        minimum,
        maximum,
    ) in integer_fields.items():
        normalized[field] = _normalize_int(
            values.get(field),
            label=label,
            minimum=minimum,
            maximum=maximum,
            default=0,
        )

    normalized["spell_resistance"] = (
        _normalize_optional_int(
            values.get("spell_resistance"),
            label="La résistance à la magie",
            minimum=0,
            maximum=1000,
        )
    )
    normalized["speed"] = _normalize_text(
        values.get("speed"),
        label="La vitesse",
        maximum=80,
    )
    normalized["damage_reduction"] = _normalize_text(
        values.get("damage_reduction"),
        label="La réduction des dégâts",
        maximum=80,
    )

    columns = [
        "str_score",
        "dex_score",
        "con_score",
        "int_score",
        "wis_score",
        "cha_score",
        "str_temp_score",
        "dex_temp_score",
        "con_temp_score",
        "int_temp_score",
        "wis_temp_score",
        "cha_temp_score",
        "max_hp",
        "current_hp",
        "nonlethal_damage",
        "speed",
        "damage_reduction",
        "spell_resistance",
        "base_attack_bonus",
        "armor_bonus",
        "shield_bonus",
        "natural_armor_bonus",
        "deflection_bonus",
        "misc_ac_modifier",
        "armor_check_penalty",
        "initiative_misc_modifier",
        "grapple_misc_modifier",
        "cmb_misc_modifier",
        "cmd_misc_modifier",
    ]

    assignments = ",\n                    ".join(
        f"{column} = %s"
        for column in columns
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                f"""
                UPDATE rpg_characters
                SET
                    {assignments},
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                [
                    normalized[column]
                    for column in columns
                ]
                + [
                    character_id,
                    user_id,
                ],
            )

            conn.commit()


def list_rpg_saves(
    user_id,
    character_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )
            _initialize_character_rows(
                cur,
                character_id,
            )

            cur.execute(
                """
                SELECT
                    character_id,
                    save_key,
                    base_save,
                    magic_modifier,
                    misc_modifier,
                    temporary_modifier,
                    conditional_notes
                FROM rpg_character_saves
                WHERE character_id = %s;
                """,
                (character_id,),
            )

            by_key = {
                row["save_key"]: row
                for row in cur.fetchall()
            }

            conn.commit()

            return [
                by_key[save_key]
                for save_key
                in SAVE_DEFINITIONS
            ]


def update_rpg_saves(
    user_id,
    character_id,
    saves,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            normalized_rows = []

            for row in saves:
                save_key = str(
                    row.get("save_key")
                    or ""
                ).strip()

                if save_key not in SAVE_DEFINITIONS:
                    raise ValueError(
                        "Un jet de sauvegarde est invalide."
                    )

                normalized_rows.append(
                    (
                        _normalize_int(
                            row.get("base_save"),
                            label="Le bonus de base",
                            minimum=-100,
                            maximum=100,
                        ),
                        _normalize_int(
                            row.get("magic_modifier"),
                            label="Le bonus magique",
                            minimum=-100,
                            maximum=100,
                        ),
                        _normalize_int(
                            row.get("misc_modifier"),
                            label="Le bonus divers",
                            minimum=-100,
                            maximum=100,
                        ),
                        _normalize_int(
                            row.get("temporary_modifier"),
                            label="Le bonus temporaire",
                            minimum=-100,
                            maximum=100,
                        ),
                        _normalize_text(
                            row.get("conditional_notes"),
                            label="Les modificateurs conditionnels",
                            maximum=500,
                        ),
                        character_id,
                        save_key,
                    )
                )

            cur.executemany(
                """
                UPDATE rpg_character_saves
                SET
                    base_save = %s,
                    magic_modifier = %s,
                    misc_modifier = %s,
                    temporary_modifier = %s,
                    conditional_notes = %s
                WHERE character_id = %s
                  AND save_key = %s;
                """,
                normalized_rows,
            )

            conn.commit()


def list_rpg_skills(
    user_id,
    character_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )
            _initialize_character_rows(
                cur,
                character_id,
            )

            cur.execute(
                """
                SELECT
                    id,
                    skill_key,
                    skill_name,
                    ability_key,
                    class_skill,
                    trained_only,
                    armor_check_applies,
                    double_armor_penalty,
                    ranks,
                    misc_modifier,
                    sort_order,
                    is_custom
                FROM rpg_character_skills
                WHERE character_id = %s
                ORDER BY
                    sort_order,
                    skill_name,
                    id;
                """,
                (character_id,),
            )

            rows = cur.fetchall()
            conn.commit()
            return rows


def update_rpg_skills(
    user_id,
    character_id,
    skills,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            normalized_rows = []

            for row in skills:
                skill_id = _normalize_int(
                    row.get("id"),
                    label="L’identifiant de compétence",
                    minimum=1,
                )
                ability_key = str(
                    row.get("ability_key")
                    or ""
                ).strip()

                if ability_key not in ABILITY_LABELS:
                    raise ValueError(
                        "La caractéristique d’une compétence "
                        "est invalide."
                    )

                normalized_rows.append(
                    (
                        _normalize_text(
                            row.get("skill_name"),
                            label="Le nom de la compétence",
                            maximum=120,
                            required=True,
                        ),
                        ability_key,
                        bool(row.get("class_skill")),
                        bool(row.get("trained_only")),
                        bool(row.get("armor_check_applies")),
                        bool(row.get("double_armor_penalty")),
                        _normalize_skill_ranks(
                            row.get("ranks"),
                        ),
                        _normalize_int(
                            row.get("misc_modifier"),
                            label="Le modificateur divers",
                            minimum=-1000,
                            maximum=1000,
                        ),
                        skill_id,
                        character_id,
                    )
                )

            cur.executemany(
                """
                UPDATE rpg_character_skills
                SET
                    skill_name = %s,
                    ability_key = %s,
                    class_skill = %s,
                    trained_only = %s,
                    armor_check_applies = %s,
                    double_armor_penalty = %s,
                    ranks = %s,
                    misc_modifier = %s
                WHERE id = %s
                  AND character_id = %s;
                """,
                normalized_rows,
            )

            conn.commit()


def create_custom_rpg_skill(
    user_id,
    character_id,
    *,
    skill_name,
    ability_key,
    trained_only=False,
    armor_check_applies=False,
    double_armor_penalty=False,
):
    name = _normalize_text(
        skill_name,
        label="Le nom de la compétence",
        maximum=120,
        required=True,
    )
    ability = str(
        ability_key
        or ""
    ).strip()

    if ability not in ABILITY_LABELS:
        raise ValueError(
            "La caractéristique est invalide."
        )

    skill_key = (
        "custom_"
        + uuid4().hex
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                """
                SELECT COALESCE(
                    MAX(sort_order),
                    0
                ) + 1 AS next_order
                FROM rpg_character_skills
                WHERE character_id = %s;
                """,
                (character_id,),
            )
            next_order = cur.fetchone()[
                "next_order"
            ]

            cur.execute(
                """
                INSERT INTO rpg_character_skills (
                    character_id,
                    skill_key,
                    skill_name,
                    ability_key,
                    trained_only,
                    armor_check_applies,
                    double_armor_penalty,
                    sort_order,
                    is_custom
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE
                )
                RETURNING id;
                """,
                (
                    character_id,
                    skill_key,
                    name,
                    ability,
                    bool(trained_only),
                    bool(armor_check_applies),
                    bool(double_armor_penalty),
                    next_order,
                ),
            )

            skill_id = cur.fetchone()[
                "id"
            ]
            conn.commit()
            return skill_id


def delete_custom_rpg_skill(
    user_id,
    character_id,
    skill_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                """
                DELETE FROM rpg_character_skills
                WHERE id = %s
                  AND character_id = %s
                  AND is_custom = TRUE
                RETURNING id;
                """,
                (
                    skill_id,
                    character_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Cette compétence personnalisée "
                    "n’existe plus."
                )

            conn.commit()


def list_rpg_attacks(
    user_id,
    character_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                """
                SELECT
                    id,
                    attack_name,
                    ability_key,
                    magic_bonus,
                    misc_bonus,
                    damage,
                    critical,
                    attack_range,
                    attack_type,
                    notes,
                    ammunition_current,
                    ammunition_max,
                    sort_order
                FROM rpg_character_attacks
                WHERE character_id = %s
                ORDER BY
                    sort_order,
                    id;
                """,
                (character_id,),
            )

            return cur.fetchall()


def _normalize_attack_values(
    values,
):
    ability_key = str(
        values.get("ability_key")
        or "str"
    ).strip()

    if ability_key not in ABILITY_LABELS:
        raise ValueError(
            "La caractéristique de l’attaque "
            "est invalide."
        )

    ammunition_current = (
        _normalize_optional_int(
            values.get("ammunition_current"),
            label="Les munitions actuelles",
            minimum=0,
            maximum=100000,
        )
    )
    ammunition_max = (
        _normalize_optional_int(
            values.get("ammunition_max"),
            label="Les munitions maximums",
            minimum=0,
            maximum=100000,
        )
    )

    return {
        "attack_name": _normalize_text(
            values.get("attack_name"),
            label="Le nom de l’attaque",
            maximum=120,
            required=True,
        ),
        "ability_key": ability_key,
        "magic_bonus": _normalize_int(
            values.get("magic_bonus"),
            label="Le bonus magique",
            minimum=-100,
            maximum=100,
        ),
        "misc_bonus": _normalize_int(
            values.get("misc_bonus"),
            label="Le bonus divers",
            minimum=-100,
            maximum=100,
        ),
        "damage": _normalize_text(
            values.get("damage"),
            label="Les dégâts",
            maximum=120,
        ),
        "critical": _normalize_text(
            values.get("critical"),
            label="Le critique",
            maximum=80,
        ),
        "attack_range": _normalize_text(
            values.get("attack_range"),
            label="La portée",
            maximum=80,
        ),
        "attack_type": _normalize_text(
            values.get("attack_type"),
            label="Le type",
            maximum=80,
        ),
        "notes": _normalize_text(
            values.get("notes"),
            label="Les notes",
            maximum=1000,
        ),
        "ammunition_current": ammunition_current,
        "ammunition_max": ammunition_max,
    }


def create_rpg_attack(
    user_id,
    character_id,
    values,
):
    normalized = _normalize_attack_values(
        values
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                """
                SELECT COALESCE(
                    MAX(sort_order),
                    0
                ) + 1 AS next_order
                FROM rpg_character_attacks
                WHERE character_id = %s;
                """,
                (character_id,),
            )
            next_order = cur.fetchone()[
                "next_order"
            ]

            cur.execute(
                """
                INSERT INTO rpg_character_attacks (
                    character_id,
                    attack_name,
                    ability_key,
                    magic_bonus,
                    misc_bonus,
                    damage,
                    critical,
                    attack_range,
                    attack_type,
                    notes,
                    ammunition_current,
                    ammunition_max,
                    sort_order
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    character_id,
                    normalized["attack_name"],
                    normalized["ability_key"],
                    normalized["magic_bonus"],
                    normalized["misc_bonus"],
                    normalized["damage"],
                    normalized["critical"],
                    normalized["attack_range"],
                    normalized["attack_type"],
                    normalized["notes"],
                    normalized["ammunition_current"],
                    normalized["ammunition_max"],
                    next_order,
                ),
            )

            attack_id = cur.fetchone()[
                "id"
            ]
            conn.commit()
            return attack_id


def update_rpg_attack(
    user_id,
    character_id,
    attack_id,
    values,
):
    normalized = _normalize_attack_values(
        values
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                """
                UPDATE rpg_character_attacks
                SET
                    attack_name = %s,
                    ability_key = %s,
                    magic_bonus = %s,
                    misc_bonus = %s,
                    damage = %s,
                    critical = %s,
                    attack_range = %s,
                    attack_type = %s,
                    notes = %s,
                    ammunition_current = %s,
                    ammunition_max = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND character_id = %s
                RETURNING id;
                """,
                (
                    normalized["attack_name"],
                    normalized["ability_key"],
                    normalized["magic_bonus"],
                    normalized["misc_bonus"],
                    normalized["damage"],
                    normalized["critical"],
                    normalized["attack_range"],
                    normalized["attack_type"],
                    normalized["notes"],
                    normalized["ammunition_current"],
                    normalized["ammunition_max"],
                    attack_id,
                    character_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Cette attaque n’existe plus."
                )

            conn.commit()


def delete_rpg_attack(
    user_id,
    character_id,
    attack_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(
                cur,
                user_id,
                character_id,
            )

            cur.execute(
                """
                DELETE FROM rpg_character_attacks
                WHERE id = %s
                  AND character_id = %s
                RETURNING id;
                """,
                (
                    attack_id,
                    character_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Cette attaque n’existe plus."
                )

            conn.commit()
