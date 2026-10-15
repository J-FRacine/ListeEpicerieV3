from __future__ import annotations
from datetime import date, timedelta
from db import get_connection

EXERCISES = (
    ("walk", "Marche sur place", "minutes", 2, "Marchez doucement, sans saut; vous devez pouvoir parler."),
    ("chair", "Se lever d’une chaise", "répétitions", 5, "Utilisez une chaise stable; levez-vous, puis rasseyez-vous lentement."),
    ("wall", "Pompes contre un mur", "répétitions", 5, "Mains contre le mur, pliez les coudes puis repoussez."),
    ("calf", "Montées sur les pointes", "répétitions", 8, "Tenez-vous à une chaise stable; soulevez les talons puis redescendez."),
)

def init_fitness_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS fitness_settings (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                started_on DATE NOT NULL DEFAULT CURRENT_DATE,
                level_offset INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS fitness_entries (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_date DATE NOT NULL,
                exercise_key TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT FALSE,
                actual_value INTEGER,
                difficulty TEXT,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY(user_id,session_date,exercise_key),
                CONSTRAINT fitness_difficulty_check CHECK (difficulty IS NULL OR difficulty IN ('facile','correct','difficile')),
                CONSTRAINT fitness_value_check CHECK (actual_value IS NULL OR actual_value BETWEEN 0 AND 999)
            )""")
        conn.commit()

def settings(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO fitness_settings(user_id) VALUES (%s) ON CONFLICT(user_id) DO NOTHING",(user_id,))
            cur.execute("SELECT started_on, level_offset FROM fitness_settings WHERE user_id=%s",(user_id,))
            out=cur.fetchone()
        conn.commit()
    return out

def week_number(started_on, day, offset=0):
    return max(1,min(8,1+(day-started_on).days//7+offset))

def daily_plan(week, day):
    stage=(max(1,min(8,week))-1)//2
    walking=(5,10,15,20)[stage]
    reps=[(5,5,8),(7,7,10),(9,9,12),(10,10,15)][stage]
    # Repos facultatif le dimanche. Renforcement lundi et jeudi.
    plan=[dict(key='walk', name='Marche sur place', unit='minutes', target=walking, info=EXERCISES[0][4])]
    if day.weekday() in (0,3):
        for ex, n in zip(EXERCISES[1:],reps):
            plan.append(dict(key=ex[0],name=ex[1],unit=ex[2],target=n,info=ex[4]))
    return plan

def entries_between(user_id, start_day, end_day):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT session_date,exercise_key,completed,actual_value,difficulty,notes FROM fitness_entries
                WHERE user_id=%s AND session_date BETWEEN %s AND %s ORDER BY session_date,exercise_key""",(user_id,start_day,end_day))
            return cur.fetchall()

def save_entry(user_id, day, key, completed, actual_value=None, difficulty=None, notes=''):
    if key not in {x[0] for x in EXERCISES}: raise ValueError('Exercice inconnu')
    if difficulty not in (None,'facile','correct','difficile'): raise ValueError('Difficulté invalide')
    if actual_value is not None and not (0<=int(actual_value)<=999): raise ValueError('Valeur invalide')
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO fitness_entries(user_id,session_date,exercise_key,completed,actual_value,difficulty,notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id,session_date,exercise_key) DO UPDATE SET completed=EXCLUDED.completed,
                actual_value=EXCLUDED.actual_value,difficulty=EXCLUDED.difficulty,notes=EXCLUDED.notes,updated_at=NOW()""",
                (user_id,day,key,bool(completed),actual_value,difficulty,(notes or '')[:1000]))
        conn.commit()

def change_level(user_id, delta):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE fitness_settings SET level_offset=GREATEST(-7,LEAST(7,level_offset+%s)),updated_at=NOW() WHERE user_id=%s",(delta,user_id))
        conn.commit()
