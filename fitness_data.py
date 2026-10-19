from __future__ import annotations
from datetime import date
from db import get_connection

EXERCISES = (
    ('outdoor_walk', 'Marche extérieure', 'minutes', 5, 'Marchez à un rythme confortable qui permet de parler. Reportez ou remplacez par une marche sur place si la météo est dangereuse.'),
    ('walk', 'Marche sur place (alternative)', 'minutes', 5, 'Alternative à la marche extérieure par forte pluie, verglas ou autre météo défavorable.'),
    ('chair', 'Se lever d’une chaise', 'répétitions', 5, 'Utilisez une chaise stable; levez-vous, puis rasseyez-vous lentement.'),
    ('wall', 'Pompes contre un mur', 'répétitions', 5, 'Mains contre le mur, pliez les coudes puis repoussez.'),
    ('calf', 'Montées sur les pointes', 'répétitions', 8, 'Tenez-vous à une chaise stable; soulevez les talons puis redescendez.'),
)

def init_fitness_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS fitness_settings (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                started_on DATE NOT NULL DEFAULT CURRENT_DATE,
                level_offset INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS fitness_entries (
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
            )''')
            cur.execute('''ALTER TABLE fitness_entries ADD COLUMN IF NOT EXISTS skip_reason TEXT''')
            cur.execute('ALTER TABLE fitness_settings ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN NOT NULL DEFAULT TRUE')
            cur.execute('ALTER TABLE fitness_settings ADD COLUMN IF NOT EXISTS reminder_snoozed_on DATE')
        conn.commit()

def settings(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO fitness_settings(user_id) VALUES (%s) ON CONFLICT(user_id) DO NOTHING',(user_id,))
            cur.execute('SELECT started_on, level_offset, reminder_enabled, reminder_snoozed_on FROM fitness_settings WHERE user_id=%s',(user_id,))
            out=cur.fetchone()
        conn.commit()
    return out

def week_number(started_on, day, offset=0):
    return max(1,min(8,1+(day-started_on).days//7+offset))

def daily_plan(week, day):
    stage=(max(1,min(8,week))-1)//2
    walking=(5,10,15,20)[stage]
    reps=[(5,5,8),(7,7,10),(9,9,12),(10,10,15)][stage]
    plan=[dict(key='outdoor_walk',name='Marche extérieure',unit='minutes',target=walking,info=EXERCISES[0][4]),
          dict(key='walk',name='Marche sur place (si météo défavorable)',unit='minutes',target=walking,info=EXERCISES[1][4],optional=True)]
    if day.weekday() in (0,3):
        for ex,n in zip(EXERCISES[2:],reps):
            plan.append(dict(key=ex[0],name=ex[1],unit=ex[2],target=n,info=ex[4]))
    return plan

def day_progress(plan, records, day):
    """Une marche intérieure peut remplacer la marche extérieure; ne compter qu'une marche."""
    required=[ex for ex in plan if not ex.get('optional')]
    done=0
    for ex in required:
        if ex['key']=='outdoor_walk':
            if (records.get((day,'outdoor_walk'),{}).get('completed') or records.get((day,'walk'),{}).get('completed')):
                done+=1
        elif records.get((day,ex['key']),{}).get('completed'):
            done+=1
    return done,len(required)

def entries_between(user_id, start_day, end_day):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT session_date,exercise_key,completed,actual_value,difficulty,notes,skip_reason FROM fitness_entries
                WHERE user_id=%s AND session_date BETWEEN %s AND %s ORDER BY session_date,exercise_key''',(user_id,start_day,end_day))
            return cur.fetchall()

def save_entry(user_id, day, key, completed, actual_value=None, difficulty=None, notes='', skip_reason=None):
    if key not in {x[0] for x in EXERCISES}: raise ValueError('Exercice inconnu')
    if difficulty not in (None,'facile','correct','difficile'): raise ValueError('Difficulté invalide')
    if skip_reason not in (None,'meteo'): raise ValueError('Motif invalide')
    if skip_reason and (key!='outdoor_walk' or completed): raise ValueError('Motif de report incompatible')
    if actual_value is not None and not (0<=int(actual_value)<=999): raise ValueError('Valeur invalide')
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO fitness_entries(user_id,session_date,exercise_key,completed,actual_value,difficulty,notes,skip_reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id,session_date,exercise_key) DO UPDATE SET completed=EXCLUDED.completed,
                actual_value=EXCLUDED.actual_value,difficulty=EXCLUDED.difficulty,notes=EXCLUDED.notes,
                skip_reason=EXCLUDED.skip_reason,updated_at=NOW()''',
                (user_id,day,key,bool(completed),actual_value,difficulty,(notes or '')[:1000],skip_reason))
        conn.commit()

def change_level(user_id, delta):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE fitness_settings SET level_offset=GREATEST(-7,LEAST(7,level_offset+%s)),updated_at=NOW() WHERE user_id=%s',(delta,user_id))
        conn.commit()


def update_reminder_preferences(user_id, enabled=None, snooze_date=None):
    """Modifie uniquement les préférences de rappel de cet utilisateur."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if enabled is not None:
                cur.execute('UPDATE fitness_settings SET reminder_enabled=%s, updated_at=NOW() WHERE user_id=%s', (bool(enabled), user_id))
            if snooze_date is not None:
                cur.execute('UPDATE fitness_settings SET reminder_snoozed_on=%s, updated_at=NOW() WHERE user_id=%s', (snooze_date, user_id))
        conn.commit()
